# 固定 Core 的 Android arm64 构建

本文件对应个人仓库 `xjbsteven/MAA-Meow` 的 `feat/recycle-station-preset-20261015` 分支、回收站领奖弹窗修复交付 v909。Android 起点为 `ea0b44067c760f6020364c45f9f12e2ddb93d824`；最终提交见 APK 交付清单。不要运行会覆盖自定义 Core 的 `scripts/setup_maa_core.py`，不要合并两个草稿 PR。

## 精确来源

- Core HEAD：`af669690a02a4d58304f03cd294eb60e6bdde0cb`。
- Core Git tree：`3f4ffe19b37e393fe5988db0385f9b7fa4c1e7a3`。
- Release Pipeline：<https://github.com/xjbsteven/MaaAssistantArknights/actions/runs/39775167175>，artifact `MAAComponent-android-arm64` / ID `12424308843`。
- Smoke Test：<https://github.com/xjbsteven/MaaAssistantArknights/actions/runs/39775167066>。
- 该 PR 工作流实际编译临时合并提交 `ac8b4a626324730eb82fb783d052607315afe4c8`，Core 内嵌版本与压缩包版本均为 `v0.0.1-ac8b4a626`。通过 GitHub Git commit API 确认它与指定 HEAD 的 **完整 Git tree 完全相同**，因此可以复用，未重新编译 Core，也未修改或伪造二进制版本字符串。
- artifact 内原始 `resource/` 的全部 10,028 个文件逐一匹配指定提交的 Git blob SHA-1；部署脚本还从递归 tree 列表重新计算全部目录及根 tree SHA-1，拒绝不完整或不一致的元数据。

## 环境与部署

本机沿用 JDK 25、SDK 37、NDK `29.0.13113456`、Android JNI CMake `3.22.1`、Gradle `9.6.0`。Python 使用本地 `.venv`。设置：

```bash
export JAVA_HOME="$PWD/.build-tools/jdk-25/Contents/Home"
export ANDROID_HOME="$PWD/.build-tools/android-sdk"
export ANDROID_USER_HOME="$PWD/.build-tools/android-home/.android"
export GRADLE_USER_HOME="$PWD/.build-tools/gradle-home"
export DEVELOPER_DIR=/Library/Developer/CommandLineTools
export GIT_EXEC_PATH=/Library/Developer/CommandLineTools/usr/libexec/git-core
export PATH="$JAVA_HOME/bin:$PWD/.build-tools/bin:$PWD/.venv/bin:$PATH"
```

`.build-tools/bin/git` 为本机 CommandLineTools 的 Git，避免未接受 Xcode license 的默认 Git。`local.properties` 中 `sdk.dir` 指向本地 SDK。以上不修改系统配置。

下载并解压指定 artifact，再获取固定 tree 元数据；需要具备 artifact 下载权限的 GitHub 身份。本机 CLI 下载返回 401，本次实际通过 GitHub 连接器下载相同 artifact，ZIP 内容校验与解压成功。

```bash
gh run download 39775167175 -R xjbsteven/MaaAssistantArknights \
  -n MAAComponent-android-arm64 -D .maa-cache/core-af669690-artifact
tar -xzf .maa-cache/core-af669690-artifact/MAAComponent-v0.0.1-ac8b4a626-android-arm64.tar.gz \
  -C .maa-cache/core-af669690-artifact
gh api 'repos/xjbsteven/MaaAssistantArknights/git/trees/3f4ffe19b37e393fe5988db0385f9b7fa4c1e7a3?recursive=1' \
  > .maa-cache/core-af669690-tree.json
python scripts/deploy_fixed_custom_core.py
python scripts/verify_fixed_custom_core.py
```

可用 `MAA_CORE_ARTIFACT` 指向解压后包含 `libMaaCore.so`、`libMaaUtils.so`、运行库与 `resource/` 的目录；`MAA_CORE_TREE_JSON` 指向递归 Git tree JSON。脚本先核对所有库哈希及资源来源，再替换 staged 文件。不会读取或切换相邻 Core 仓库工作树。

固定库 SHA-256：

- `libMaaCore.so`: `f91d781087c94ab20d8383ee4148f404725f100f2c950c125d0231d16a79520f`
- `libMaaUtils.so`: `b82a0711998a4eb003fef86c99affaf20dd9841af8887191f3401242562db1e8`
- `libMaaAndroidNativeControlUnit.so`: `d81b3ce2cee4bbaf6b74762d703f4e0644461af41e3429fa7be44fa52f34961d`
- `libonnxruntime.so`: `71c92e5779b04cfcc234aff8452d08010c8a8b13982f5e32954e380037c5e057`
- `libopencv_world4.so`: `909caa9ab62d20d206e8fa3734d6b0877fcd36db0c01570a546fdcdf0cd7e58e`
- `libfastdeploy_ppocr.so`: `6ccc3608b21a5e49e7acc41f12ce73c2671ab388ed356a73b3fea1628f482c5b`

`libc++_shared.so` 由 Android JNI 使用的 NDK 提供，不复制 artifact 中的同名库；NDK 原文件 SHA-256 为 `259e897588d798546fb5721eec1983c98a6a46358a5fa864b170d95c7d77fec3`。APK 校验脚本将它与真实 NDK 文件比较。

NCNN 转换沿用配方 2，缓存按源 ONNX 内容哈希选择。此次 8 组模型全部命中缓存；移除 8 个源 ONNX 后，最终 10,036 个资源文件包含 16 个 `.ncnn.param/.bin`。PaddleOCR、PaddleCharOCR 的 det/rec 均齐全。`.maa-resource-identity.json` 记录源 HEAD、Git tree、实际编译 SHA、run/artifact ID 及转换后每个文件的 SHA-256；这些生成输入与库不提交到 Git。

## 测试与 APK 核验

```bash
bash gradlew :app:testDebugUnitTest :app:lintDebug :app:assembleDebug \
  -Pmaa.abi=arm64-v8a -Pmaa.customVersionCode=909 \
  -Pmaa.customVersionName=0.22.0-custom.af669690a0.909
python scripts/verify_fixed_custom_apk.py app/build/outputs/apk/debug/app-debug.apk
"$ANDROID_HOME/build-tools/36.0.0/apksigner" verify --verbose --print-certs \
  app/build/outputs/apk/debug/app-debug.apk
"$ANDROID_HOME/build-tools/36.0.0/aapt" dump badging app/build/outputs/apk/debug/app-debug.apk
```

2026-10-23 实际结果：BUILD SUCCESSFUL。202 个测试类共 1,374 项，0 失败、0 错误、0 跳过；`BaseRewardCollectionParamsTest`、`StationPresetRecycleTest` 各 3 项通过。Lint 0 Error、173 Warning、2 Hint。Gradle 日志确认 `verifyFixedCore` 实际执行并通过，没有跳过校验。

实际 APK 检查：

- `libMaaCore.so` 与指定 artifact 原文件逐字节相同；其他 staged 库和 NDK C++ runtime 与 NDK `llvm-strip --strip-unneeded` 输出逐字节一致，交付 JSON 保留源哈希与包内哈希。
- 全部 10,036 个资源文件逐个核对 SHA-256，文件集合完全相同；没有 macOS 垃圾文件。APK 文件名按 Android 的 UTF-8 路径编码读取。
- Core 中存在 `ClickSelfRecord`、`ClickRecorded`，任务资源确认：材料产出 OCR 后记录实际点击中心；获得物资弹窗关闭坐标为 `[645,665,1,1]`；fallback 使用 `ClickRecorded` 且没有固定坐标。普通奖励仍包括可收获、订单交付、员信赖。
- 所有打包原生库为 AArch64，DT_NEEDED 依赖由 APK 或 Android 系统提供。
- applicationId `com.aliothmoon.maameow`；versionCode `909`；versionName `0.22.0-custom.af669690a0.909`；minSdk 28。

## 签名与交付

使用用户已有 `.build-tools/android-home/.android/debug.keystore`，与旧覆盖安装 APK 的证书 SHA-256 相同：`0cd27521db91bace8e72f8c862e0242b841c03cf0b49b40f15b06c2acaf79b22`。RSA 2048，APK Signature Scheme v2 验证通过。密钥不提交。

APK：`dist/MAA-Meow-v909-core-af669690a0-arm64-debug.apk`；302,784,046 字节（288.76 MiB）。SHA-256：`1196a33cdb6dcaeab10b97ef1219e31d7d23ad6549f43a6fd26476cf0f08386f`。同目录 `.sha256`、`.verification.json` 与 `delivery-v909/` 保留交付信息、身份清单和构建/签名/Lint 日志；均为本机文件。

## 真机边界

ADB 检查无设备连接，未安装、启动或验证真实弹窗，也没有真实任务执行顺序的 Debug 日志。静态校验、依赖闭包和单测不代表 Android 原生库加载或真实界面验收通过。以下全部待用户验证：

1. 仅开启基建奖励自动收取，其他辅助选项关闭，普通奖励仍可收取。
2. 回收站材料产出领取后，出现奖励弹窗时正常关闭。
3. 获得物资 OCR 失败时复点原领取位置，不进入其他设置。
4. 继续处理制造站、贸易站、干员信赖等其他奖励。
5. 奖励已领取完毕时不多点、不误入其他界面。
6. 回收站预设、宿舍/回收站换班、无人机、自动补货及此前自定义功能无回归。

验收时保留 Debug 日志，重点记录 `InfrastRecycleReward`、`InfrastRecycleRewardPopup`、`InfrastRecycleRewardFallback` 的执行顺序。此次未修改这些业务实现，也未额外运行 Core 全量测试；复用指定成功的 CI 产物。
