#!/usr/bin/env python3
"""Deploy a locally built MAA install/ tree into MAA-Meow assets and jniLibs."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ASSETS_RESOURCE_DIR = Path("app/src/main/assets/MaaSync/MaaResource")
JNILIBS_DIR = Path("app/src/main/jniLibs")
VERSION_FILE = Path(".maaversion")
EXCLUDE_SO = {"libc++_shared.so"}


def deploy(install_dir: Path, project_root: Path, abi: str, version: str) -> None:
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
    for so in install_dir.glob("*.so"):
        if so.name in EXCLUDE_SO:
            continue
        shutil.copy2(so, jnilib_dir / so.name)
        copied_so += 1

    (project_root / VERSION_FILE).write_text(version + "\n", encoding="utf-8")
    print(f"[VERSION] {VERSION_FILE}: {version}")
    print(f"[DONE] resource={copied_resource} files, so={copied_so} files -> {abi}/")


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
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    deploy(Path(args.install_dir).resolve(), project_root, args.abi, args.version)


if __name__ == "__main__":
    main()
