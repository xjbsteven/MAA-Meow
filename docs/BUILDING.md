# 固定 Core 的 Android arm64 构建

本文件记录 `Aliothmoon/MAA-Meow@ad0c95b2230f9d3aa10d546dc0d226e83d4988a8` 上重建自定义 APK 的流程。Android 改动以本仓库交付 commit 为准。旧版 `scripts/setup_maa_core.py` 会下载最新 Core，**此构建不要运行它**。

## 环境与来源

- macOS、JDK 25、Android SDK 37、NDK 29.0.13113456；设置 `JAVA_HOME`、`ANDROID_HOME`，在 `local.properties` 写 `sdk.dir`。
- Android upstream 固定 SHA：`ad0c95b2230f9d3aa10d546dc0d226e83d4988a8`，不要在本次重建时重新追踪 `main`。
- Core upstream SHA：`9e56e82c0d1577e73603d8be676686bbfeb5f13d`。
- 自定义 Core 仓库 `xjbsteven/MaaAssistantArknights` 中固定 commit：`5115df57b4d8b30dd201041b1c394b214148611b`，tree `7a0e50239b265fd5811ae07515c35c5d90ce2ee4`。
- Core 版本：`v6.17.3-alpha.1-custom.5115df57b4`。

默认 Core 仓库位于 Android 仓库的 `../MaaAssistantArknights`；可用 `MAA_CORE_REPO` 指定其他路径。部署脚本只读该仓库的 Git 对象和已构建的 `build-android/bin`，不会切换或改动其工作树。

## 构建 Core

在固定 Core commit 的独立 checkout 中运行：

```bash
cmake --preset android-arm64 -DMAA_HASH_VERSION=v6.17.3-alpha.1-custom.5115df57b4
CCACHE_DISABLE=1 cmake --build build --target MaaCore -j 6
```

确认 `build-android/bin/libMaaCore.so` SHA-256 为 `feedcfcbfad3b4621c18563833037be0af566eed54d9a8f86a2631834cd67728`。同目录的 `libMaaUtils.so` 一同部署。若 checkout 不是固定 commit，请使用独立 worktree 构建；切勿把别的 commit 构建出的 so 冒充固定产物。

## 部署与校验

```bash
python3 scripts/deploy_fixed_custom_core.py
python3 scripts/verify_fixed_custom_core.py
```

部署脚本用 `git archive` 从固定 commit 导出完整 `resource/`，清除旧 `MaaResource`，复制 Core 与 Utils so，并写 `.maaversion`。OCR ONNX 与 templates/tasks 均来自相同 Git tree。Android OCR runtime 从同一个 Core sibling 仓库的 `install/` 复制，部署与构建前按脚本内四个固定 SHA-256 核对（Android control unit、onnxruntime、OpenCV、fastdeploy）；NCNN 由项目 `scripts/convert_ocr_ncnn.py` 从此 commit 的 OCR ONNX 生成，缓存键包含 ONNX 哈希和转换配方。至少检查 PaddleOCR/PaddleCharOCR 的 `det`、`rec` `.ncnn.param/.bin`；不能跳过转换。

`verifyFixedCore` 在 Gradle `preBuild` 前执行，要求 `.maaversion`、so SHA-256、嵌入版本、`tasks/tasks.json`、OCR runtime 与 NCNN 都存在。资源清单生成时过滤 `.DS_Store`、`._*`、`__MACOSX`，运行时提取再过滤一次。

## 测试、构建、验收

```bash
ANDROID_USER_HOME="$PWD/.build-tools/android-home/.android" \
  bash gradlew :app:testDebugUnitTest :app:lintDebug :app:assembleDebug \
  -Pmaa.abi=arm64-v8a -Pmaa.customVersionCode=903 \
  -Pmaa.customVersionName=0.22.0-custom.5115df57b4.3
python3 scripts/verify_fixed_custom_core.py
unzip -l app/build/outputs/apk/debug/app-debug.apk | rg 'lib/arm64-v8a/libMaaCore.so|MaaResource/tasks/tasks.json|\.ncnn\.(param|bin)'
unzip -l app/build/outputs/apk/debug/app-debug.apk | rg 'DS_Store|__MACOSX|/\._' # 必须无输出
shasum -a 256 app/build/outputs/apk/debug/app-debug.apk
```

使用 SDK build-tools 36.0.0 的 `aapt dump badging` 或 `apkanalyzer manifest application-id/version-code/version-name` 核对包信息，再用 `unzip -p` 抽出 `libMaaCore.so` 验证 SHA-256 与嵌入版本。构建产物是 debug 签名 APK，构建参数显式固定 versionCode 903（大于旧 441）与 versionName `0.22.0-custom.5115df57b4.3`；不传两个参数时仍使用官方 Git 计数与描述策略。不要使用最新官方 Core 自动覆盖 staged 文件。

> `.maaversion`、staged `MaaResource` 与 native so 是本地生成输入，不应由 Git 提交；交付 commit 加本文件与指定 Core commit 可重建它们。

本次交付 APK SHA-256：`a92057f4d9e524c8e730c1e05fcb31fcc16df96f126dec40cb0a573ef01271f7`（`app/build/outputs/apk/debug/app-debug.apk`，复制为 `dist/MAA-Meow-v903-arm64-cover-install.apk`）。

## 覆盖安装签名

旧 447 debug APK 的签名证书 SHA-256 是 `0cd27521db91bace8e72f8c862e0242b841c03cf0b49b40f15b06c2acaf79b22`。本轮首次 APK 误用了 `~/.android/debug.keystore`（证书 `0db81adda822e33d9de3b59e7077599765b91aef3dd9216dcea8a2f87d05794e`），因此 Android 拒绝覆盖安装。可覆盖安装包改用本机已有的 `.build-tools/android-home/.android/debug.keystore`；该密钥是用户本地文件，不在 Git 中。运行 Gradle 时必须设置上面的 `ANDROID_USER_HOME`。

构建后用 `apksigner verify --print-certs` 对照旧 APK 与新 APK 的签名证书 SHA-256，必须完全相同；再检查 `versionCode` 高于旧包。没有相同的私钥时无法从 Git commit 单独重现可覆盖安装签名，只能新装或由密钥持有人签名。
