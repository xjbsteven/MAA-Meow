#!/usr/bin/env python3
"""Fail Android builds if staged Core identity or runtime inputs drift."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
VERSION = 'v6.17.3-alpha.1-custom.02f6a195c2'
SHA256 = '6d9b6f044f96b6baae36b0ae93410842bdd97d809829975853d6f7fb603b82de'
UTILS_SHA256 = '0ec9f763c8ba66bf53f6e8d14307e1f66241a9ff63ef07a953d00d649434fd73'
RUNTIME_SHA256 = {
    'libMaaAndroidNativeControlUnit.so': '40eee689dd7fea90d9da7350b78bb5de0bcdc344c75fa6875f73be3a6254e8ce',
    'libonnxruntime.so': '71c92e5779b04cfcc234aff8452d08010c8a8b13982f5e32954e380037c5e057',
    'libopencv_world4.so': '909caa9ab62d20d206e8fa3734d6b0877fcd36db0c01570a546fdcdf0cd7e58e',
    'libfastdeploy_ppocr.so': '6ccc3608b21a5e49e7acc41f12ce73c2671ab388ed356a73b3fea1628f482c5b',
}
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
    utils = NATIVE / 'libMaaUtils.so'
    require(utils.is_file() and hashlib.sha256(utils.read_bytes()).hexdigest() == UTILS_SHA256, 'libMaaUtils.so SHA-256 mismatch')
    for name, expected in RUNTIME_SHA256.items():
        path = NATIVE / name
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected, f'Android runtime drift: {name}')

    require((RESOURCE / 'tasks/tasks.json').is_file(), 'Core tasks resource missing')
    for package in ('PaddleOCR', 'PaddleCharOCR'):
        for kind in ('det', 'rec'):
            for ext in ('param', 'bin'):
                require((RESOURCE / package / kind / f'{kind}.ncnn.{ext}').is_file(), f'NCNN missing: {package}/{kind}/{ext}')
    identity = json.loads((ROOT / '.maa-resource-identity.json').read_text())
    require(identity['core_sha'] == '02f6a195c2df1bee3db2867a7421e28ff79bdf42', 'resource Core SHA mismatch')
    require(identity['core_tree'] == '751ed2e85dcf14ecec6856830d6510914158dc8c', 'resource tree mismatch')
    for name, expected in identity['resource_files'].items():
        path = RESOURCE / name
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected, f'resource drift: {name}')
    actual_files = {str(p.relative_to(RESOURCE)) for p in RESOURCE.rglob('*') if p.is_file()}
    require(actual_files == set(identity['resource_files']), 'resource file set mismatch')
    tasks = json.loads((RESOURCE / 'tasks/tasks.json').read_text())
    require('InfrastCollect' in tasks, 'InfrastCollect missing')
    require(all(text in tasks['InfrastReward']['text'] for text in ('可收获', '订单交付', '员信赖', '材料产出')), 'full collection OCR labels missing')
    junk = [p for p in RESOURCE.rglob('*') if p.name == '.DS_Store' or p.name.startswith('._') or p.name == '__MACOSX']
    require(not junk, f'macOS junk found: {junk[:3]}')
    print(f'Core identity verified: {VERSION} ({SHA256})')

if __name__ == '__main__':
    main()
