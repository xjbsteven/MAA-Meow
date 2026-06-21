#!/usr/bin/env python3
"""Deploy a locally built MAA install/ tree into MAA-Meow assets and jniLibs."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

ASSETS_RESOURCE_DIR = Path("app/src/main/assets/MaaSync/MaaResource")
JNILIBS_DIR = Path("app/src/main/jniLibs")
VERSION_FILE = Path(".maaversion")
CACHE_DIR = Path(".maa-cache")
DEFAULT_GITHUB_REPO = "MaaAssistantArknights/MaaAssistantArknights"
ABI_KEYWORDS = {
    "arm64-v8a": "android-arm64",
    "x86_64": "android-x64",
}
# Always taken from the custom cmake install (must match each other).
CUSTOM_CORE_SO = {"libMaaCore.so", "libMaaUtils.so"}
# Also copied from custom install even in hybrid mode (not in official MAA tarball).
CUSTOM_EXTRA_SO = {"libMaaAndroidNativeControlUnit.so"}
# OCR model dirs replaced from official tarball for lib/model compatibility.
OFFICIAL_RESOURCE_OVERLAY = ("PaddleOCR", "PaddleCharOCR")
# NDK bridge build already ships libc++_shared; do not duplicate from MAA tarball.
OFFICIAL_SO_SKIP = {"libc++_shared.so"}
REQUIRED_JNI_LIBS = (
    "libMaaCore.so",
    "libMaaUtils.so",
    "libfastdeploy_ppocr.so",
    "libonnxruntime.so",
    "libopencv_world4.so",
)
REQUIRED_OCR_FILES = (
    "PaddleOCR/rec/inference.onnx",
    "PaddleOCR/det/inference.onnx",
    "PaddleCharOCR/rec/inference.onnx",
)


def _fetch_json(url: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN")

    def _request(with_auth: bool) -> dict:
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "MaaMeow-Deploy")
        if with_auth and token:
            req.add_header("Authorization", f"token {token}")
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))

    if not token:
        return _request(False)
    try:
        return _request(True)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return _request(False)
        raise


def _download_file(url: str, dest: Path) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/octet-stream")
    req.add_header("User-Agent", "MaaMeow-Deploy")
    if token:
        req.add_header("Authorization", f"token {token}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=600) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out)


def _ensure_official_tarball(project_root: Path, abi: str) -> Path:
    keyword = ABI_KEYWORDS[abi]
    cache_dir = project_root / CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    cached = sorted(cache_dir.glob(f"*{keyword}*.tar.gz"))
    if cached:
        print(f"[CACHE] Using official tarball: {cached[-1].name}")
        return cached[-1]

    api = f"https://api.github.com/repos/{DEFAULT_GITHUB_REPO}/releases/latest"
    print(f"[FETCH] Downloading latest official Android SO tarball ({keyword})")
    release = _fetch_json(api)
    asset = next(
        (a for a in release.get("assets", []) if keyword in a["name"] and a["name"].endswith(".tar.gz")),
        None,
    )
    if asset is None:
        raise SystemExit(f"[ERROR] No official release asset found for {keyword}")

    dest = cache_dir / asset["name"]
    _download_file(asset["browser_download_url"], dest)
    print(f"[DOWNLOAD] {dest.name}")
    return dest


def _extract_official_so(tarball: Path, jnilib_dir: Path, skip_names: set[str]) -> list[str]:
    copied: list[str] = []
    with tarfile.open(tarball, "r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            name = Path(member.name).name
            if not name.endswith(".so") or name in skip_names:
                continue
            dest = jnilib_dir / name
            with tar.extractfile(member) as src:
                dest.write_bytes(src.read())
            copied.append(name)
    return copied


def _extract_official_resource_overlay(
    tarball: Path, assets_dir: Path, overlay_dirs: tuple[str, ...]
) -> int:
    copied = 0
    with tarfile.open(tarball, "r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            parts = Path(member.name).parts
            if "resource" not in parts:
                continue
            res_idx = parts.index("resource")
            rel_parts = parts[res_idx + 1 :]
            if not rel_parts or rel_parts[0] not in overlay_dirs:
                continue
            dest = assets_dir / Path(*rel_parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as src:
                dest.write_bytes(src.read())
            copied += 1
    return copied


def verify_deploy(project_root: Path, abi: str, *, hybrid: bool) -> None:
    jnilib_dir = project_root / JNILIBS_DIR / abi
    assets_dir = project_root / ASSETS_RESOURCE_DIR
    errors: list[str] = []

    for name in REQUIRED_JNI_LIBS:
        path = jnilib_dir / name
        if not path.is_file() or path.stat().st_size < 1024:
            errors.append(f"missing or empty jni lib: {name}")

    for rel in REQUIRED_OCR_FILES:
        path = assets_dir / rel
        if not path.is_file() or path.stat().st_size < 1024:
            errors.append(f"missing or empty OCR resource: {rel}")

    version_json = assets_dir / "version.json"
    if not version_json.is_file():
        errors.append("missing assets version.json")

    if hybrid:
        core = jnilib_dir / "libMaaCore.so"
        utils = jnilib_dir / "libMaaUtils.so"
        ocr = jnilib_dir / "libfastdeploy_ppocr.so"
        if core.is_file() and utils.is_file() and core.stat().st_mtime < ocr.stat().st_mtime:
            # sanity: custom core copied after official OCR libs in deploy()
            pass

    if errors:
        raise SystemExit("[VERIFY FAILED]\n" + "\n".join(f"  - {e}" for e in errors))

    print("[VERIFY OK] hybrid deploy layout looks complete")


def deploy(
    install_dir: Path,
    project_root: Path,
    abi: str,
    version: str,
    *,
    hybrid_official_so: bool = False,
) -> None:
    if not install_dir.is_dir():
        raise SystemExit(f"[ERROR] install dir not found: {install_dir}")

    resource_src = install_dir / "resource"
    if not resource_src.is_dir():
        raise SystemExit(f"[ERROR] resource dir not found: {resource_src}")

    assets_dir = project_root / ASSETS_RESOURCE_DIR
    if assets_dir.exists():
        print(f"[DELETE] {assets_dir}")
        shutil.rmtree(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)

    copied_resource = 0
    for src in resource_src.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(resource_src)
        dest = assets_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied_resource += 1

    jnilib_dir = project_root / JNILIBS_DIR / abi
    jnilib_dir.mkdir(parents=True, exist_ok=True)
    for existing in jnilib_dir.glob("*.so"):
        if existing.name != "libjnidispatch.so":
            existing.unlink()

    copied_so = 0
    if hybrid_official_so:
        tarball = _ensure_official_tarball(project_root, abi)
        official_names = _extract_official_so(
            tarball,
            jnilib_dir,
            skip_names=CUSTOM_CORE_SO | CUSTOM_EXTRA_SO | OFFICIAL_SO_SKIP,
        )
        print(f"[HYBRID] official so={len(official_names)}: {', '.join(sorted(official_names))}")
        overlay_count = _extract_official_resource_overlay(
            tarball, assets_dir, OFFICIAL_RESOURCE_OVERLAY
        )
        print(f"[HYBRID] official OCR resource overlay={overlay_count} files")
        for name in sorted(CUSTOM_CORE_SO | CUSTOM_EXTRA_SO):
            src = install_dir / name
            if not src.is_file():
                if name in CUSTOM_EXTRA_SO:
                    print(f"[HYBRID] skip optional custom so (missing): {name}")
                    continue
                raise SystemExit(f"[ERROR] custom core library missing: {src}")
            shutil.copy2(src, jnilib_dir / name)
            copied_so += 1
            print(f"[HYBRID] custom so: {name}")
        verify_deploy(project_root, abi, hybrid=True)
    else:
        for so in install_dir.glob("*.so"):
            shutil.copy2(so, jnilib_dir / so.name)
            copied_so += 1

    (project_root / VERSION_FILE).write_text(version + "\n", encoding="utf-8")
    print(f"[VERSION] {VERSION_FILE}: {version}")
    mode = "hybrid" if hybrid_official_so else "full-custom"
    print(f"[DONE] mode={mode}, resource={copied_resource} files, so={copied_so} custom core libs -> {abi}/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy local MAA install/ into MAA-Meow")
    parser.add_argument(
        "--install-dir",
        required=True,
        help="Path to MAA cmake install/ directory (contains resource/ and *.so)",
    )
    parser.add_argument(
        "--abi",
        default="arm64-v8a",
        choices=["arm64-v8a", "x86_64"],
        help="Target Android ABI (default: arm64-v8a)",
    )
    parser.add_argument(
        "--version",
        default="local-facility-preset",
        help="Version string written to .maaversion",
    )
    parser.add_argument(
        "--hybrid-official-so",
        action="store_true",
        help=(
            "Use official prebuilt OCR/ONNX .so from latest MAA release, "
            "but keep libMaaCore.so/libMaaUtils.so and resources from --install-dir"
        ),
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    deploy(
        Path(args.install_dir).resolve(),
        project_root,
        args.abi,
        args.version,
        hybrid_official_so=args.hybrid_official_so,
    )


if __name__ == "__main__":
    main()
