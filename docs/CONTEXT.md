# MAA-Meow 自定义 Android 当前基线

## 历史旧基线

旧推荐可用包为 versionCode **441**、versionName `0.14.4-alpha.26`、Core `v6.13.0-beta.2-54-gb413a132d5`。440 因 APK 内 `.DS_Store` 导致资源初始化失败而废弃。后续 447 是 2026-09-07 旧分支临时构建，均不作为本轮开发底座。

## 当前升级基线（2026-09-26 Core-only 重打包）

- ANDROID_UPSTREAM_SHA=`ad0c95b2230f9d3aa10d546dc0d226e83d4988a8`
- CORE_UPSTREAM_SHA=`9e56e82c0d1577e73603d8be676686bbfeb5f13d`
- CUSTOM_CORE_SHA=`5115df57b4d8b30dd201041b1c394b214148611b`
- CUSTOM_CORE_VERSION=`v6.17.3-alpha.1-custom.5115df57b4`
- Core binary SHA-256=`feedcfcbfad3b4621c18563833037be0af566eed54d9a8f86a2631834cd67728`
- Android 起点=`486d62eb7023b5bc1fd6be338c73f408bd4f5cf2`
- versionCode=`903`
- versionName=`0.22.0-custom.5115df57b4.3`
- APK filename=`MAA-Meow-v903-arm64-cover-install.apk`
- APK SHA-256=`a92057f4d9e524c8e730c1e05fcb31fcc16df96f126dec40cb0a573ef01271f7`

本轮以官方 Android 固定 main 为底，新增 `minimum_recruit_times` UI/序列化，旧 `forceConfirmToMeetTimes` 加载与备份导入迁移，保留官方独立的 `level3_recruitment_permit_reserve`。Rotation 增加 game/station_preset 子模式、布局/设施选择、rest、drones 以及会客室接收线索；station_preset 复用官方菲亚梅塔配置，跨设施组合仅 Normal 模式生效。固定 Core 的 dorm OCR fail-open 属 Core 实现，Android 不加规避分支。

Core 与完整 resource 从同一固定 commit 部署；NCNN 由该 resource 的 OCR ONNX 转换。构建前固定 Core 身份校验，资源清单和运行时提取过滤 macOS 垃圾文件。自动与真机验收结果记录在最终交付报告；未连接设备时不得视为真机通过。

完整重建步骤见 [BUILDING.md](BUILDING.md)。

## 历史：2026-09-25 验收

`:app:compileDebugKotlin`、`:app:testDebugUnitTest`、`:app:lintDebug`、`:app:assembleDebug` 均通过。APK 静态核对：仅 arm64-v8a；Core SHA-256 为 `a4a168270523bcfb5c21503bf85c1f7fa010d16485950baad24ea308ef057ddb`；存在 `tasks/tasks.json`、设施点预设模板、PaddleOCR 和 PaddleCharOCR NCNN；asset manifest 有 9470 条；无 `.DS_Store`、`._*`、`__MACOSX`。

ADB `devices -l` 为空，真机新装/覆盖安装、首次/手动资源初始化、普通任务、公招最低数量触发、station_preset 全流程与菲亚梅塔宿舍流程均待用户现场验证；没有宣称真机通过。

注意：Android OCR runtime libraries 从 Core sibling 仓库 `install/` 中按固定 SHA-256 复制；本轮精确固定的 Core/Utils 与 Git resource、由同份 ONNX 转换出的 NCNN 已在构建前及 APK 内核对。

## 历史：2026-09-25 覆盖安装修复

用户现场截图显示安装失败 -7，系统报告与已安装应用签名不同。旧 447 APK 证书 SHA-256 为 `0cd27521db91bace8e72f8c862e0242b841c03cf0b49b40f15b06c2acaf79b22`，首次交付 APK 的证书为 `0db81adda822e33d9de3b59e7077599765b91aef3dd9216dcea8a2f87d05794e`。使用本机保留的旧 debug keystore 重新构建后，新 APK 证书与旧包完全一致。新 APK SHA-256 为 `1bc0cb7cd99afb819ca0fa55d4a6bbe4e1d764e5c96fe7fdb3398a94df19038c`。尚未通过真机重试安装。

## 历史：2026-09-25 StationPreset UI 修正

Rotation + StationPreset 只显示编号设施选择 `presetSelectedRooms`，隐藏普通 `FacilitiesSection`；显示现有 0–100% 宿舍心情阈值，并注明菲亚梅塔候选规则。Normal、Custom 与 Rotation + Game 的原可见性保持不变。`dormThreshold=30/50` 分别下发 `threshold=0.3/0.5`，固定 Core 与资源未改变。`:app:testDebugUnitTest`、`:app:lintDebug`、`:app:assembleDebug` 通过；APK versionCode 901，SHA-256 为 `fe8bc64adcebdf9cb676c2ce79796d983bda681614456f7b68a678a8d6b0a664`。

## 历史：2026-09-26 增量

新 Core `d8789fc8372bfc0ed4a1b195a57892ab40c3a11c` 修复 StationPreset 菲亚梅塔跨页与后置宿舍整理。Android 仍只在 Rotation + StationPreset 增加自家路径；Custom 保留固定官方语义，没有恢复 `autoAdvancePlanIndex` 或废弃的 facility preset 示例。完整 resource 从新 Core commit 导出并清空旧 staged 目录；旧 `facility_preset_3_shifts_daily.json` 不再存在。StationPreset 下显示并允许独立修改蹭信赖与未进驻筛选；两者可与菲亚梅塔同时开启。

2026-09-26 自动验收：`:app:testDebugUnitTest`、`:app:lintDebug`、`:app:assembleDebug` 通过；APK 中 `libMaaCore.so` SHA-256 为 `e71366154a9a85c42c60c0b49c4172994fb2c0243da2420e9def2fde2f3b1a8e`，嵌入版本匹配。APK 仅 arm64，含 tasks、StationPreset 模板、PaddleOCR/PaddleCharOCR NCNN；asset manifest 9469 项；无废弃 3 换 preset 或 macOS 垃圾文件。签名证书仍为 `0cd27521db91bace8e72f8c862e0242b841c03cf0b49b40f15b06c2acaf79b22`。ADB 无连接设备，真机流程待验证。

## 2026-09-26 Core-only 重打包

只将已集成的 Core 从 `d8789fc8372bfc0ed4a1b195a57892ab40c3a11c` 更新到 `5115df57b4d8b30dd201041b1c394b214148611b`，后者仅优化菲亚梅塔恢复目标首次扫描的提前终止。Android UI、Infrast 配置与参数序列化均未改。按 exact-commit 机制清空并导出新 Core 的完整 resource，重新生成 NCNN 和 resource identity。旧版本验收记录保留在上方历史章节。

自动验收：`:app:testDebugUnitTest`、`:app:lintDebug`、`:app:assembleDebug` 与 `verify_fixed_custom_core.py` 均通过。APK 内 Core SHA-256 为 `feedcfcbfad3b4621c18563833037be0af566eed54d9a8f86a2631834cd67728`，嵌入版本正确；仅 arm64，含 tasks、PaddleOCR/PaddleCharOCR NCNN；asset manifest 9469 项；无废弃三换预设或 macOS 垃圾文件。签名证书仍为 `0cd27521db91bace8e72f8c862e0242b841c03cf0b49b40f15b06c2acaf79b22`。
