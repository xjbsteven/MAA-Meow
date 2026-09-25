# 固定 Core 的 Android arm64 构建

本文件记录 `Aliothmoon/MAA-Meow@ad0c95b2230f9d3aa10d546dc0d226e83d4988a8` 上重建自定义 APK 的流程。Android 改动以本仓库交付 commit 为准。旧版 `scripts/setup_maa_core.py` 会下载最新 Core，**此构建不要运行它**。

## 环境与来源

- macOS、JDK 25、Android SDK 37、NDK 29.0.13113456；设置 `JAVA_HOME`、`ANDROID_HOME`，在 `local.properties` 写 `sdk.dir`。
- Android upstream 固定 SHA：`ad0c95b2230f9d3aa10d546dc0d226e83d4988a8`，不要在本次重建时重新追踪 `main`。
- Core upstream SHA：`9e56e82c0d1577e73603d8be676686bbfeb5f13d`。
- 自定义 Core 仓库 `xjbsteven/MaaAssistantArknights` 中固定 commit：`11feb567ab6ac5d240101cf623aa2361c4ff4ace`，tree `6f796dcc52ba604242e308e2260432977a53e9c5`。
- Core 版本：`v6.17.3-alpha.1-custom.11feb567ab`。

默认 Core 仓库位于 Android 仓库的 `../MaaAssistantArknights`；可用 `MAA_CORE_REPO` 指定其他路径。部署脚本只读该仓库的 Git 对象和已构建的 `build-android/bin`，不会切换或改动其工作树。

## 构建 Core

在固定 Core commit 的独立 checkout 中运行：

```bash
cmake --preset android-arm64 -DMAA_HASH_VERSION=v6.17.3-alpha.1-custom.11feb567ab
CCACHE_DISABLE=1 cmake --build build --target MaaCore -j 6
```

确认 `build-android/bin/libMaaCore.so` SHA-256 为 `a4a168270523bcfb5c21503bf85c1f7fa010d16485950baad24ea308ef057ddb`。同目录的 `libMaaUtils.so` 一同部署。若 checkout 不是固定 commit，请使用独立 worktree 构建；切勿把别的 commit 构建出的 so 冒充固定产物。

## 部署与校验

```bash
python3 scripts/deploy_fixed_custom_core.py
python3 scripts/verify_fixed_custom_core.py
```

部署脚本用 `git archive` 从固定 commit 导出完整 `resource/`，清除旧 `MaaResource`，复制 Core 与 Utils so，并写 `.maaversion`。OCR ONNX 与 templates/tasks 均来自相同 Git tree。Android OCR runtime 使用 `jniLibs/arm64-v8a` 中的官方 Android runtime 库；NCNN 由项目 `scripts/convert_ocr_ncnn.py` 从此 commit 的 OCR ONNX 生成，缓存键包含 ONNX 哈希和转换配方。至少检查 PaddleOCR/PaddleCharOCR 的 `det`、`rec` `.ncnn.param/.bin`；不能跳过转换。

`verifyFixedCore` 在 Gradle `preBuild` 前执行，要求 `.maaversion`、so SHA-256、嵌入版本、`tasks/tasks.json`、OCR runtime 与 NCNN 都存在。资源清单生成时过滤 `.DS_Store`、`._*`、`__MACOSX`，运行时提取再过滤一次。

## 测试、构建、验收

```bash
./gradlew :app:testDebugUnitTest :app:lintDebug :app:assembleDebug \
  -Pmaa.abi=arm64-v8a -Pmaa.customVersionCode=900 \
  -Pmaa.customVersionName=0.22.0-custom.11feb567ab
python3 scripts/verify_fixed_custom_core.py
unzip -l app/build/outputs/apk/debug/app-debug.apk | rg 'lib/arm64-v8a/libMaaCore.so|MaaResource/tasks/tasks.json|\.ncnn\.(param|bin)'
unzip -l app/build/outputs/apk/debug/app-debug.apk | rg 'DS_Store|__MACOSX|/\._' # 必须无输出
shasum -a 256 app/build/outputs/apk/debug/app-debug.apk
```

使用 SDK build-tools 36.0.0 的 `aapt dump badging` 或 `apkanalyzer manifest application-id/version-code/version-name` 核对包信息，再用 `unzip -p` 抽出 `libMaaCore.so` 验证 SHA-256 与嵌入版本。构建产物是 debug 签名 APK，构建参数显式固定 versionCode 900（大于旧 441）与 versionName `0.22.0-custom.11feb567ab`；不传两个参数时仍使用官方 Git 计数与描述策略。不要使用最新官方 Core 自动覆盖 staged 文件。

> `.maaversion`、staged `MaaResource` 与 native so 是本地生成输入，不应由 Git 提交；交付 commit 加本文件与指定 Core commit 可重建它们。

本次交付 APK SHA-256：`c9b3288df14464cf1fef178180032e643aa8cc25e12dc9f7ae9f57ba22804ffe`（`app/build/outputs/apk/debug/app-debug.apk`）。
