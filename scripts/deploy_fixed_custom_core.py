#!/usr/bin/env python3
"""Stage the fixed custom Core and its exact-commit resource for a local arm64 build."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE_SHA = 'af669690a02a4d58304f03cd294eb60e6bdde0cb'
# CI built the PR merge commit; its complete source tree equals CORE_SHA's tree.
CORE_TREE = '3f4ffe19b37e393fe5988db0385f9b7fa4c1e7a3'
BUILD_SHA = 'ac8b4a626324730eb82fb783d052607315afe4c8'
ARTIFACT = Path(os.environ.get('MAA_CORE_ARTIFACT', str(ROOT / '.maa-cache/core-af669690-artifact')))
TREE_JSON = Path(os.environ.get('MAA_CORE_TREE_JSON', str(ROOT / '.maa-cache/core-af669690-tree.json')))
CORE_VERSION = 'v0.0.1-ac8b4a626'
CORE_SHA256 = 'f91d781087c94ab20d8383ee4148f404725f100f2c950c125d0231d16a79520f'
UTILS_SHA256 = 'b82a0711998a4eb003fef86c99affaf20dd9841af8887191f3401242562db1e8'
RUNTIME_SHA256 = {
    'libMaaAndroidNativeControlUnit.so': 'd81b3ce2cee4bbaf6b74762d703f4e0644461af41e3429fa7be44fa52f34961d',
    'libonnxruntime.so': '71c92e5779b04cfcc234aff8452d08010c8a8b13982f5e32954e380037c5e057',
    'libopencv_world4.so': '909caa9ab62d20d206e8fa3734d6b0877fcd36db0c01570a546fdcdf0cd7e58e',
    'libfastdeploy_ppocr.so': '6ccc3608b21a5e49e7acc41f12ce73c2671ab388ed356a73b3fea1628f482c5b',
}
RESOURCE = ROOT / 'app/src/main/assets/MaaSync/MaaResource'
NATIVE = ROOT / 'app/src/main/jniLibs/arm64-v8a'

def main() -> None:
    core = ARTIFACT / 'libMaaCore.so'
    utils = ARTIFACT / 'libMaaUtils.so'
    if hashlib.sha256(core.read_bytes()).hexdigest() != CORE_SHA256:
        raise SystemExit('Core binary SHA-256 mismatch; rebuild at fixed commit')
    if CORE_VERSION.encode() not in core.read_bytes():
        raise SystemExit('Core binary version mismatch')
    if not utils.is_file() or hashlib.sha256(utils.read_bytes()).hexdigest() != UTILS_SHA256:
        raise SystemExit('Matching libMaaUtils.so missing')
    # Reconstruct every Git tree from the API listing, rather than trusting the
    # listing's top-level SHA (GitHub can echo the requested commit SHA there).
    metadata = json.loads(TREE_JSON.read_text())
    if metadata.get('truncated', True):
        raise SystemExit('Incomplete Git tree metadata')
    directories: dict[str, list] = {'': []}
    for entry in metadata['tree']:
        parent, _, name = entry['path'].rpartition('/')
        directories.setdefault(parent, []).append((name, entry))
    for directory, entries in directories.items():
        data = b''.join(
            f"{entry['mode'].lstrip('0')} {name}".encode() + b'\0' + bytes.fromhex(entry['sha'])
            for name, entry in sorted(entries, key=lambda item: item[0] + ('/' if item[1]['type'] == 'tree' else ''))
        )
        actual = hashlib.sha1(b'tree ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        expected = CORE_TREE if not directory else next(e['sha'] for e in metadata['tree'] if e['path'] == directory)
        if actual != expected:
            raise SystemExit(f'Git tree metadata mismatch: {directory}')
    source = ARTIFACT / 'resource'
    resource_blobs = {e['path'][9:]: e['sha'] for e in metadata['tree'] if e['path'].startswith('resource/') and e['type'] == 'blob'}
    if {str(p.relative_to(source)) for p in source.rglob('*') if p.is_file()} != set(resource_blobs):
        raise SystemExit('Artifact resource file set differs from pinned Git tree')
    for name, expected in resource_blobs.items():
        data = (source / name).read_bytes()
        if hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != expected:
            raise SystemExit(f'Artifact resource differs from pinned Git tree: {name}')
    for name, expected in RUNTIME_SHA256.items():
        runtime = ARTIFACT / name
        if not runtime.is_file() or hashlib.sha256(runtime.read_bytes()).hexdigest() != expected:
            raise SystemExit(f'Pinned Android runtime missing or mismatched: {name}')
    shutil.rmtree(RESOURCE, ignore_errors=True)
    shutil.copytree(source, RESOURCE)
    NATIVE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(core, NATIVE / core.name)
    shutil.copy2(utils, NATIVE / utils.name)
    for name in RUNTIME_SHA256:
        shutil.copy2(ARTIFACT / name, NATIVE / name)

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
        'core_tree': CORE_TREE,
        'build_sha': BUILD_SHA,
        'artifact_id': 12424308843,
        'run_id': 39775167175,
        'resource_files': {
            str(path.relative_to(RESOURCE)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in RESOURCE.rglob('*') if path.is_file()
        },
    }
    (ROOT / '.maa-resource-identity.json').write_text(json.dumps(identity, sort_keys=True))
    print(f'CUSTOM_CORE_SHA={CORE_SHA}\nCUSTOM_CORE_VERSION={CORE_VERSION}')

if __name__ == '__main__':
    main()
