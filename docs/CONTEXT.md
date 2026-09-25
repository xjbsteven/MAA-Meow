# MAA-Meow 自定义 Android 当前基线

## 历史旧基线

旧推荐可用包为 versionCode **441**、versionName `0.14.4-alpha.26`、Core `v6.13.0-beta.2-54-gb413a132d5`。440 因 APK 内 `.DS_Store` 导致资源初始化失败而废弃。后续 447 是 2026-09-07 旧分支临时构建，均不作为本轮开发底座。

## 当前升级基线

- ANDROID_UPSTREAM_SHA=`ad0c95b2230f9d3aa10d546dc0d226e83d4988a8`
- CORE_UPSTREAM_SHA=`9e56e82c0d1577e73603d8be676686bbfeb5f13d`
- CUSTOM_CORE_SHA=`11feb567ab6ac5d240101cf623aa2361c4ff4ace`
- CUSTOM_CORE_VERSION=`v6.17.3-alpha.1-custom.11feb567ab`
- CUSTOM_MAAMEOW_SHA=`2a7adc080ef0fd714ca6591cb148f2be7fed5d5e`（功能实现 commit）
- versionCode=`900`
- versionName=`0.22.0-custom.11feb567ab`
- APK filename=`app-debug.apk`
- APK SHA-256=`c9b3288df14464cf1fef178180032e643aa8cc25e12dc9f7ae9f57ba22804ffe`

本轮以官方 Android 固定 main 为底，新增 `minimum_recruit_times` UI/序列化，旧 `forceConfirmToMeetTimes` 加载与备份导入迁移，保留官方独立的 `level3_recruitment_permit_reserve`。Rotation 增加 game/station_preset 子模式、布局/设施选择、rest、drones 以及会客室接收线索；station_preset 复用官方菲亚梅塔配置，跨设施组合仅 Normal 模式生效。固定 Core 的 dorm OCR fail-open 属 Core 实现，Android 不加规避分支。

Core 与完整 resource 从同一固定 commit 部署；NCNN 由该 resource 的 OCR ONNX 转换。构建前固定 Core 身份校验，资源清单和运行时提取过滤 macOS 垃圾文件。自动与真机验收结果记录在最终交付报告；未连接设备时不得视为真机通过。

完整重建步骤见 [BUILDING.md](BUILDING.md)。

## 2026-09-25 验收

`:app:compileDebugKotlin`、`:app:testDebugUnitTest`、`:app:lintDebug`、`:app:assembleDebug` 均通过。APK 静态核对：仅 arm64-v8a；Core SHA-256 为 `a4a168270523bcfb5c21503bf85c1f7fa010d16485950baad24ea308ef057ddb`；存在 `tasks/tasks.json`、设施点预设模板、PaddleOCR 和 PaddleCharOCR NCNN；asset manifest 有 9470 条；无 `.DS_Store`、`._*`、`__MACOSX`。

ADB `devices -l` 为空，真机新装/覆盖安装、首次/手动资源初始化、普通任务、公招最低数量触发、station_preset 全流程与菲亚梅塔宿舍流程均待用户现场验证；没有宣称真机通过。

注意：Android OCR runtime libraries 从 Core sibling 仓库 `install/` 中按固定 SHA-256 复制；本轮精确固定的 Core/Utils 与 Git resource、由同份 ONNX 转换出的 NCNN 已在构建前及 APK 内核对。
