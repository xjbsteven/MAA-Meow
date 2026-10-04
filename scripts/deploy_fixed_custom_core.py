#!/usr/bin/env python3
"""Stage the fixed custom Core and its exact-commit resource for a local arm64 build."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE_REPO = Path(os.environ.get('MAA_CORE_REPO', str(ROOT.parent / 'MaaAssistantArknights')))
CORE_SHA = '6652f584336c13519b7ceb8fca2b40c91dc0c0ef'
CORE_VERSION = 'v6.17.3-alpha.1-custom.6652f58433'
CORE_SHA256 = '8265222663530aa81546dafd7b84751049bd1b3c4833de167481fe0a6cf6de11'
RUNTIME_SHA256 = {
    'libMaaAndroidNativeControlUnit.so': '40eee689dd7fea90d9da7350b78bb5de0bcdc344c75fa6875f73be3a6254e8ce',
    'libonnxruntime.so': '71c92e5779b04cfcc234aff8452d08010c8a8b13982f5e32954e380037c5e057',
    'libopencv_world4.so': '909caa9ab62d20d206e8fa3734d6b0877fcd36db0c01570a546fdcdf0cd7e58e',
    'libfastdeploy_ppocr.so': '6ccc3608b21a5e49e7acc41f12ce73c2671ab388ed356a73b3fea1628f482c5b',
}
RESOURCE = ROOT / 'app/src/main/assets/MaaSync/MaaResource'
NATIVE = ROOT / 'app/src/main/jniLibs/arm64-v8a'

def run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()

def main() -> None:
    actual = run('git', '-C', str(CORE_REPO), 'rev-parse', CORE_SHA + '^{commit}')
    if actual != CORE_SHA:
        raise SystemExit('CUSTOM_CORE_SHA not reachable')
    core = CORE_REPO / 'build-android/bin/libMaaCore.so'
    utils = CORE_REPO / 'build-android/bin/libMaaUtils.so'
    if hashlib.sha256(core.read_bytes()).hexdigest() != CORE_SHA256:
        raise SystemExit('Core binary SHA-256 mismatch; rebuild at fixed commit')
    if CORE_VERSION.encode() not in core.read_bytes():
        raise SystemExit('Core binary version mismatch')
    if not utils.is_file():
        raise SystemExit('Matching libMaaUtils.so missing')
    with tempfile.TemporaryDirectory(prefix='maa-core-resource-') as tmp:
        archive = Path(tmp) / 'resource.tar'
        with archive.open('wb') as output:
            subprocess.run(['git', '-C', str(CORE_REPO), 'archive', '--format=tar', CORE_SHA, 'resource'], stdout=output, check=True)
        with tarfile.open(archive) as tar:
            tar.extractall(tmp, filter='data')
        source = Path(tmp) / 'resource'
        if not (source / 'tasks/tasks.json').is_file():
            raise SystemExit('Core task resource missing')
        shutil.rmtree(RESOURCE, ignore_errors=True)
        shutil.copytree(source, RESOURCE, ignore=shutil.ignore_patterns('.DS_Store', '._*', '__MACOSX'))
    shutil.copy2(core, NATIVE / 'libMaaCore.so')
    shutil.copy2(utils, NATIVE / 'libMaaUtils.so')
    for name, expected in RUNTIME_SHA256.items():
        runtime = CORE_REPO / 'install' / name
        if not runtime.is_file() or hashlib.sha256(runtime.read_bytes()).hexdigest() != expected:
            raise SystemExit(f'Pinned Android runtime missing or mismatched: {name}')
        shutil.copy2(runtime, NATIVE / name)

    (ROOT / '.maaversion').write_text(CORE_VERSION + '\n')
    # Android OCR uses NCNN models generated from the exact-commit OCR ONNX files.
    subprocess.run(['python3', str(ROOT / 'scripts/convert_ocr_ncnn.py'), '--resource', str(RESOURCE), '--cache', str(ROOT / '.maa-cache/ncnn')], check=True)
    for package in ('PaddleOCR', 'PaddleCharOCR'):
        for kind in ('det', 'rec'):
            for ext in ('param', 'bin'):
                if not (RESOURCE / package / kind / f'{kind}.ncnn.{ext}').is_file():
                    raise SystemExit(f'NCNN incomplete: {package}/{kind}/{ext}')
    identity = {
        'core_sha': CORE_SHA,
        'core_tree': run('git', '-C', str(CORE_REPO), 'rev-parse', CORE_SHA + '^{tree}'),
        'resource_files': {
            str(path.relative_to(RESOURCE)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in RESOURCE.rglob('*') if path.is_file() and '.ncnn.' not in path.name
        },
    }
    (ROOT / '.maa-resource-identity.json').write_text(json.dumps(identity, sort_keys=True))
    print(f'CUSTOM_CORE_SHA={CORE_SHA}\nCUSTOM_CORE_VERSION={CORE_VERSION}')

if __name__ == '__main__':
    main()
