# 固定 Core 的 Android arm64 构建

本文件记录个人仓库 `xjbsteven/MAA-Meow` 的 `feat/recycle-station-preset-20261015` 分支构建流程；本轮起点为 `a4541a8b56ae424a4372c3b467e68111fd326543`，最终 Android SHA 见 APK 同目录交付清单。旧版 `scripts/setup_maa_core.py` 会下载最新 Core，**此构建不要运行它**。

## 环境与来源

本机沿用环境：`JAVA_HOME=$PWD/.build-tools/jdk-25/Contents/Home`、`ANDROID_HOME=$PWD/.build-tools/android-sdk`、`GRADLE_USER_HOME=$PWD/.build-tools/gradle-home`。

- macOS、JDK 25、Android SDK 37、NDK 29.0.13113456；设置 `JAVA_HOME`、`ANDROID_HOME`，在 `local.properties` 写 `sdk.dir`。
- 两个个人仓库均使用 `feat/recycle-station-preset-20261015`；不要切回 `main` / `dev-v2`。
- 自定义 Core 仓库 `xjbsteven/MaaAssistantArknights` 中固定 commit：`02f6a195c2df1bee3db2867a7421e28ff79bdf42`，tree `751ed2e85dcf14ecec6856830d6510914158dc8c`。
- Core 版本：`v6.17.3-alpha.1-custom.02f6a195c2`。

默认 Core 仓库位于 Android 仓库的 `../MaaAssistantArknights`；可用 `MAA_CORE_REPO` 指定其他路径。部署脚本只读该仓库的 Git 对象和已构建的 `build-android/bin`，不会切换或改动其工作树。

## 构建 Core

本轮使用 `.maa-cache/core-source-02f6a195` 独立 worktree，NDK 29.0.13113456 与 CMake 4.3.3（Core 的 CMake 最低要求高于 Android JNI 的 3.22.1）。MaaUtils 子模块固定为 `6e9ba33f6ad835418097d9324c01c44a82825a2b`，复用同 SHA 的干净本地子模块与 MaaDeps。

在固定 Core commit 的独立 checkout 中运行：

```bash
cmake --preset android-arm64 -B build-android \
  -DCMAKE_TOOLCHAIN_FILE="$ANDROID_HOME/ndk/29.0.13113456/build/cmake/android.toolchain.cmake" \
  -DBUILD_DEBUG_DEMO=OFF -DBUILD_RESOURCE_UPDATER=OFF -DBUILD_MAA_UTILS=ON \
  -DMAA_HASH_VERSION=v6.17.3-alpha.1-custom.02f6a195c2
cmake --build build-android --target clean
CCACHE_DISABLE=1 cmake --build build-android --target MaaCore MaaUtils -j 6
```

确认 `build-android/bin/libMaaCore.so` SHA-256 为 `6d9b6f044f96b6baae36b0ae93410842bdd97d809829975853d6f7fb603b82de`。同目录的 `libMaaUtils.so` 一同部署。若 checkout 不是固定 commit，请使用独立 worktree 构建；切勿把别的 commit 构建出的 so 冒充固定产物。

## 部署与校验

```bash
MAA_CORE_REPO="$PWD/.maa-cache/core-source-02f6a195" python3 scripts/deploy_fixed_custom_core.py
python3 scripts/verify_fixed_custom_core.py
```

部署脚本用 `git archive` 从固定 commit 导出完整 `resource/`，清除旧 `MaaResource`，复制 Core 与 Utils so，并写 `.maaversion`。OCR ONNX 与 templates/tasks 均来自相同 Git tree。Android OCR runtime 从同一个 Core sibling 仓库的 `install/` 复制，部署与构建前按脚本内四个固定 SHA-256 核对（Android control unit、onnxruntime、OpenCV、fastdeploy）；NCNN 由项目 `scripts/convert_ocr_ncnn.py` 从此 commit 的 OCR ONNX 生成，缓存键包含 ONNX 哈希和转换配方。至少检查 PaddleOCR/PaddleCharOCR 的 `det`、`rec` `.ncnn.param/.bin`；不能跳过转换。

`verifyFixedCore` 在 Gradle `preBuild` 前执行，要求 `.maaversion`、so SHA-256、嵌入版本、`tasks/tasks.json`、OCR runtime 完整，Utils 哈希匹配，NCNN 哈希与资源文件集合均无漂移，并要求 `InfrastCollect` 与四类一键收获文字齐全。资源清单生成时过滤 `.DS_Store`、`._*`、`__MACOSX`，运行时提取再过滤一次。

## 测试、构建、验收

```bash
ANDROID_USER_HOME="$PWD/.build-tools/android-home/.android" \
  bash gradlew :app:testDebugUnitTest :app:lintDebug :app:assembleDebug \
  -Pmaa.abi=arm64-v8a -Pmaa.customVersionCode=908 \
  -Pmaa.customVersionName=0.22.0-custom.02f6a195c2.908
python3 scripts/verify_fixed_custom_core.py
unzip -l app/build/outputs/apk/debug/app-debug.apk | rg 'lib/arm64-v8a/libMaaCore.so|MaaResource/tasks/tasks.json|\.ncnn\.(param|bin)'
unzip -l app/build/outputs/apk/debug/app-debug.apk | rg 'DS_Store|__MACOSX|/\._' # 必须无输出
shasum -a 256 app/build/outputs/apk/debug/app-debug.apk
```

使用 SDK build-tools 36.0.0 的 `aapt dump badging` 或 `apkanalyzer manifest application-id/version-code/version-name` 核对包信息，再用 `unzip -p` 抽出 `libMaaCore.so` 验证 SHA-256 与嵌入版本。构建产物是 debug 签名 APK，构建参数显式固定 versionCode 908（高于上一包 907）与 versionName `0.22.0-custom.02f6a195c2.908`；不传两个参数时仍使用官方 Git 计数与描述策略。不要使用最新官方 Core 自动覆盖 staged 文件。

> `.maaversion`、staged `MaaResource` 与 native so 是本地生成输入，不应由 Git 提交；交付 commit 加本文件与指定 Core commit 可重建它们。

最终 APK 放在 `dist/MAA-Meow-v908-core-02f6a195c2-arm64-debug.apk`；大小、SHA-256、Android 提交、APK 内逐文件核验结果见同目录交付清单。

## 覆盖安装签名

旧 447 debug APK 的签名证书 SHA-256 是 `0cd27521db91bace8e72f8c862e0242b841c03cf0b49b40f15b06c2acaf79b22`。本轮首次 APK 误用了 `~/.android/debug.keystore`（证书 `0db81adda822e33d9de3b59e7077599765b91aef3dd9216dcea8a2f87d05794e`），因此 Android 拒绝覆盖安装。可覆盖安装包改用本机已有的 `.build-tools/android-home/.android/debug.keystore`；该密钥是用户本地文件，不在 Git 中。运行 Gradle 时必须设置上面的 `ANDROID_USER_HOME`。

构建后用 `apksigner verify --print-certs` 对照旧 APK 与新 APK 的签名证书 SHA-256，必须完全相同；再检查 `versionCode` 高于旧包。没有相同的私钥时无法从 Git commit 单独重现可覆盖安装签名，只能新装或由密钥持有人签名。

## 本轮 Core CI 与测试边界

`02f6a195…` 的 Smoke Test 已通过，Release Pipeline 的 Android arm64 作业已通过。不过该 PR 工作流实际检出 `refs/pull/3/merge`（`20adc32…`），因此没有把该产物冒充 HEAD；本轮 APK 使用精确 HEAD 的本地重编译结果。

Debug 原生单测中，`maa-dorm-scan-test` 9 用例 / 60 断言、`maa-recruit-minimum-test` 3 用例 / 21 断言通过。额外全量构建的 `maa-algorithm-test` 因 `Utils/Algorithm.hpp` 使用未声明的 `battle::OperNameTag` 编译失败，未修改无关算法逻辑；不能声称 Core 全量单测通过。

真机仍须检查：仅收取开关开启时四类奖励收取、关闭后公共导航不收取且重入不重复收取、无人机贸易交付、回收站预设执行、旧配置迁移、宿舍信赖 / 菲亚梅塔 / 公招自定义 / 主题切换，以及 OCR 与提权运行。

## 本轮 Android 自动验证

执行 `bash gradlew :app:testDebugUnitTest :app:lintDebug :app:assembleDebug -Pmaa.abi=arm64-v8a -Pmaa.customVersionCode=908 -Pmaa.customVersionName=0.22.0-custom.02f6a195c2.908`，环境使用前述 JDK / Android / Gradle 目录。Gradle 9.6.0、AGP 9.4.1，Kotlin / Java / arm64 NDK 编译通过；202 个测试类共 1,374 项测试，0 失败、0 错误、0 跳过，包含 `BaseRewardCollectionParamsTest` 与 `StationPresetRecycleTest` 各 3 项。Lint 通过，0 Error、172 Warning、2 Hint。

APK 内 `libMaaCore.so` 与本次构建原文件逐字节一致；Utils 与四个 runtime 分别与 NDK `llvm-strip --strip-unneeded` 的结果逐字节一致。全部 10,036 个资源文件（含 16 个 NCNN 文件）按身份清单逐个核对 SHA-256，所有打包 ELF 均为 AArch64，动态依赖均由 APK 或 Android 系统提供。`tasks/tasks.json` 的 `InfrastCollect` 和四类收获文字已核对；无人机贸易 `DroneConfirm -> DeliverableOrder` 链路仍保留。

若 macOS 的 `/usr/bin/git` 被 Xcode license 检查挡住，可使用 CommandLineTools 的 Git；本轮使用本地 `.build-tools/bin/git` 指向 `/Library/Developer/CommandLineTools/usr/bin/git`，并设置 `GIT_EXEC_PATH=/Library/Developer/CommandLineTools/usr/libexec/git-core`。Python 使用 `.venv/bin/python`（3.12）。这些环境修复不修改系统设置。
