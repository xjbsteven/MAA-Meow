#!/usr/bin/env python3
"""Fail Android builds if staged Core identity or runtime inputs drift."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
VERSION = 'v0.0.1-ac8b4a626'
SHA256 = 'f91d781087c94ab20d8383ee4148f404725f100f2c950c125d0231d16a79520f'
UTILS_SHA256 = 'b82a0711998a4eb003fef86c99affaf20dd9841af8887191f3401242562db1e8'
RUNTIME_SHA256 = {
    'libMaaAndroidNativeControlUnit.so': 'd81b3ce2cee4bbaf6b74762d703f4e0644461af41e3429fa7be44fa52f34961d',
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
    require(all(action in core.read_bytes() for action in (b'ClickSelfRecord', b'ClickRecorded')), 'Core recorded-click actions missing')
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
    require(identity['core_sha'] == 'af669690a02a4d58304f03cd294eb60e6bdde0cb', 'resource Core SHA mismatch')
    require(identity['core_tree'] == '3f4ffe19b37e393fe5988db0385f9b7fa4c1e7a3', 'resource tree mismatch')
    require(identity['build_sha'] == 'ac8b4a626324730eb82fb783d052607315afe4c8', 'CI build SHA mismatch')
    require(identity['artifact_id'] == 12424308843 and identity['run_id'] == 39775167175, 'CI artifact provenance mismatch')
    for name, expected in identity['resource_files'].items():
        path = RESOURCE / name
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected, f'resource drift: {name}')
    actual_files = {str(p.relative_to(RESOURCE)) for p in RESOURCE.rglob('*') if p.is_file()}
    require(actual_files == set(identity['resource_files']), 'resource file set mismatch')
    tasks = json.loads((RESOURCE / 'tasks/tasks.json').read_text())
    require('InfrastCollect' in tasks, 'InfrastCollect missing')
    require(
        all(text in tasks['InfrastReward']['text'] for text in ('可收获', '订单交付', '员信赖')),
        'normal base collection OCR labels missing',
    )
    # 回收站已拆为独立分支：材料产出不再属于普通奖励 OCR 列表。
    recycle = tasks.get('InfrastRecycleReward', {})
    popup = tasks.get('InfrastRecycleRewardPopup', {})
    fallback = tasks.get('InfrastRecycleRewardFallback', {})
    require(recycle.get('text') == ['材料产出'], 'recycle materials collection OCR label missing')
    require(recycle.get('action') == 'ClickSelfRecord', 'recycle OCR click must record the button position')
    require(popup.get('text') == ['获得物资'], 'recycle reward popup recognition missing')
    require(popup.get('action') == 'ClickRect' and popup.get('specificRect') == [645, 665, 1, 1], 'recycle popup close position mismatch')
    require(fallback.get('action') == 'ClickRecorded', 'recycle fallback must replay the recorded button position')
    require('specificRect' not in fallback, 'recycle fallback must not use guessed fixed coordinates')
    require('InfrastRecycleRewardFallback' in recycle.get('next', []), 'recycle fallback not reachable')
    require('InfrastRecycleReward' in tasks['InfrastNotification']['next'], 'recycle collection not linked from the overview')
    junk = [p for p in RESOURCE.rglob('*') if p.name == '.DS_Store' or p.name.startswith('._') or p.name == '__MACOSX']
    require(not junk, f'macOS junk found: {junk[:3]}')
    print(f'Core identity verified: {VERSION} ({SHA256})')

if __name__ == '__main__':
    main()
