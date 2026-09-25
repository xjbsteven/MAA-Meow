#!/usr/bin/env python3
"""Fail Android builds if staged Core identity or runtime inputs drift."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
VERSION = 'v6.17.3-alpha.1-custom.11feb567ab'
SHA256 = 'a4a168270523bcfb5c21503bf85c1f7fa010d16485950baad24ea308ef057ddb'
RESOURCE = ROOT / 'app/src/main/assets/MaaSync/MaaResource'
NATIVE = ROOT / 'app/src/main/jniLibs/arm64-v8a'

def require(ok: bool, message: str) -> None:
    if not ok:
        raise SystemExit(message)

def main() -> None:
    core = NATIVE / 'libMaaCore.so'
    require((ROOT / '.maaversion').read_text().strip() == VERSION, '.maaversion mismatch')
    require(hashlib.sha256(core.read_bytes()).hexdigest() == SHA256, 'libMaaCore.so SHA-256 mismatch')
    require(VERSION.encode() in core.read_bytes(), 'embedded Core version mismatch')
    require((NATIVE / 'libMaaUtils.so').is_file(), 'libMaaUtils.so missing')
    require((NATIVE / 'libMaaAndroidNativeControlUnit.so').is_file(), 'control unit missing')
    require((RESOURCE / 'tasks/tasks.json').is_file(), 'Core tasks resource missing')
    for package in ('PaddleOCR', 'PaddleCharOCR'):
        for kind in ('det', 'rec'):
            for ext in ('param', 'bin'):
                require((RESOURCE / package / kind / f'{kind}.ncnn.{ext}').is_file(), f'NCNN missing: {package}/{kind}/{ext}')
    identity = json.loads((ROOT / '.maa-resource-identity.json').read_text())
    require(identity['core_sha'] == '11feb567ab6ac5d240101cf623aa2361c4ff4ace', 'resource Core SHA mismatch')
    require(identity['core_tree'] == '6f796dcc52ba604242e308e2260432977a53e9c5', 'resource tree mismatch')
    for name, expected in identity['resource_files'].items():
        path = RESOURCE / name
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected, f'resource drift: {name}')
    junk = [p for p in RESOURCE.rglob('*') if p.name == '.DS_Store' or p.name.startswith('._') or p.name == '__MACOSX']
    require(not junk, f'macOS junk found: {junk[:3]}')
    print(f'Core identity verified: {VERSION} ({SHA256})')

if __name__ == '__main__':
    main()
