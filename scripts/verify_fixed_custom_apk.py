#!/usr/bin/env python3
"""Verify the actual APK against pinned, already-verified custom Core inputs."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import zipfile

import verify_fixed_custom_core as staged

ROOT = Path(__file__).resolve().parent.parent
require = staged.require


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path)
    parser.add_argument('--sdk', type=Path, default=Path(os.environ.get('ANDROID_HOME', str(ROOT / '.build-tools/android-sdk'))))
    args = parser.parse_args()
    staged.main()
    apk = args.apk.resolve()
    ndk = args.sdk / 'ndk/29.0.13113456/toolchains/llvm/prebuilt/darwin-x86_64'
    identity = json.loads((ROOT / '.maa-resource-identity.json').read_text())
    report = {
        'apk': str(apk), 'size_bytes': apk.stat().st_size, 'sha256': digest(apk.read_bytes()),
        'core_sha': identity['core_sha'], 'core_tree': identity['core_tree'],
        'core_build_sha': identity['build_sha'], 'core_version': staged.VERSION,
        'artifact_id': identity['artifact_id'], 'run_id': identity['run_id'],
        'android_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'native': {},
    }
    # Android's APK writer stores UTF-8 paths without setting the ZIP UTF-8 bit.
    with zipfile.ZipFile(apk, metadata_encoding='utf-8') as z, tempfile.TemporaryDirectory() as tmp:
        names = z.namelist()
        require(len(names) == len(set(names)), 'Duplicate APK ZIP entries')
        require(not any(Path(n).name == '.DS_Store' or Path(n).name.startswith('._') or '__MACOSX' in n for n in names), 'macOS junk in APK')
        require({n.split('/')[1] for n in names if n.startswith('lib/')} == {'arm64-v8a'}, 'APK ABI mismatch')
        prefix = 'assets/MaaSync/MaaResource/'
        actual = {n[len(prefix):] for n in names if n.startswith(prefix) and not n.endswith('/')}
        require(actual == set(identity['resource_files']), 'APK resource file set mismatch')
        for name, expected in identity['resource_files'].items():
            require(digest(z.read(prefix + name)) == expected, 'APK resource mismatch: ' + name)
        report['resource_files_verified'] = len(actual)
        report['ncnn_files_verified'] = sum('.ncnn.' in n for n in actual)
        tasks = json.loads(z.read(prefix + 'tasks/tasks.json'))
        # Every resource was checked above, including the tasks validated by verifyFixedCore.
        report['recycle_tasks'] = {n: tasks[n] for n in ('InfrastRecycleReward', 'InfrastRecycleRewardPopup', 'InfrastRecycleRewardFallback')}
        report['collection_labels'] = tasks['InfrastReward']['text']
        native_names = {Path(n).name for n in names if n.startswith('lib/arm64-v8a/') and n.endswith('.so')}
        sources = {p.name: p for p in staged.NATIVE.glob('*.so')}
        # The app's JNI bridge uses the NDK's shared C++ runtime, never the artifact's copy.
        sources['libc++_shared.so'] = ndk / 'sysroot/usr/lib/aarch64-linux-android/libc++_shared.so'
        for name, source in sources.items():
            data = z.read('lib/arm64-v8a/' + name)
            expected = source.read_bytes()
            method = 'exact source bytes'
            if data != expected:
                stripped = Path(tmp) / name
                subprocess.run([str(ndk / 'bin/llvm-strip'), '--strip-unneeded', '-o', str(stripped), str(source)], check=True)
                require(data == stripped.read_bytes(), 'APK native mismatch: ' + name)
                method = 'exact NDK stripped source bytes'
            report['native'][name] = {'source_sha256': digest(expected), 'apk_sha256': digest(data), 'verification': method}
        core = z.read('lib/arm64-v8a/libMaaCore.so')
        require(staged.VERSION.encode() in core, 'APK embedded Core version mismatch')
        require(all(action in core for action in (b'ClickSelfRecord', b'ClickRecorded')), 'APK Core recorded-click actions missing')
        report['recorded_click_actions'] = 'PASS (binary identity + both action strings)'
        system_libs = {'libc.so', 'libm.so', 'libdl.so', 'liblog.so', 'libandroid.so', 'libjnigraphics.so', 'libmediandk.so', 'libz.so', 'libvulkan.so', 'libEGL.so', 'libGLESv2.so', 'libGLESv3.so', 'libOpenSLES.so', 'libaaudio.so', 'libnativewindow.so'}
        dependencies = {}
        for name in sorted(native_names):
            native = Path(tmp) / ('apk-' + name)
            native.write_bytes(z.read('lib/arm64-v8a/' + name))
            out = subprocess.check_output([str(ndk / 'bin/llvm-readelf'), '-h', '-d', str(native)], text=True)
            require('AArch64' in out, 'Non-arm64 ELF: ' + name)
            needed = [line.split('[')[1].split(']')[0] for line in out.splitlines() if '(NEEDED)' in line]
            require(set(needed) <= native_names | system_libs, f'Unresolved dependencies: {name}: {needed}')
            dependencies[name] = needed
        report['dependencies'] = dependencies
        report['elf_architecture_and_dependency_closure'] = 'PASS'
    output = apk.with_suffix('.verification.json')
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f'APK verified: {report["sha256"]}; resources={report["resource_files_verified"]}; NCNN={report["ncnn_files_verified"]}')
    print(f'Report: {output}')


if __name__ == '__main__':
    main()
