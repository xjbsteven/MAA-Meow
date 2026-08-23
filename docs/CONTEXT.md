# MAA-Meow 本地定制 Core · 会话状态快照

> 父会话 ID：6860a895-3ed6-4ab4-8d9a-97cac0edace2 → 当前：unknown  
> 最后更新：2026-07-28 21:42  
> 实质性事件计数：14  
> 接续方式：新 Chat 首条粘贴 `/session-continuity` + 文末 handoff 块

---

## 当前状态（一句话）

**可安装的 debug APK 为 versionCode 441**，Core `v6.13.0-beta.2-54-gb413a132d5`（基于 `6066b6a6b4` + 公招 `force_confirm_to_meet_times`）；含设施点预设、宿舍 OCR fail-open、公招新选项；**已含 NCNN**；**已剔除 `.DS_Store`**（440 初始化失败根因）。

---

## 进行中的话题

- 无阻塞项；用户侧待验证：安装 **441** → 「重新初始化资源」→ 测设施点预设 + 公招新开关。

---

## 本会话已完成的工作

| 日期 | 事件 |
|------|------|
| 06-21~06-25 | 打通 Mac 本地 hybrid 封装：`bootstrap_build_env.sh` + `deploy_local_maa_core.py` + `local_build_apk.sh` |
| 06-25~06-29 | Android UI 同步 `station_preset`：布局步进器、设施勾选、无人机、去除 JSON 排班 |
| 06-29 | `versionCode` 自动 bump；修正设施点预设文案（去掉菲亚梅塔误导） |
| 07-01 | Core `6066b6a6b4`（设施预设 + 宿舍信赖 OCR）；误用 `--skip-ncnn` 打出 438 失败，补 NCNN 后 **439** |
| 07-01 | 建立 `docs/CONTEXT.md`（session-continuity）；`local_build_apk.sh` 缺 NCNN 时禁止 `--skip-ncnn` |
| 07-28 | 采用 export `android-core-export-6066-recruit`（base=6066 + recruit）；Android 加 `forceConfirmToMeetTimes`；打出 **440**（含 NCNN） |
| 07-29 | 440 初始化失败：`MaaSync/MaaResource/.DS_Store`；清理并在 deploy/manifest/`AssetExtractor` 三层排除；打出 **441** |

---

## 尚未解决的问题

- `docs/BUILDING.md` 未收录本地定制 Core 封装步骤。
- 换 Core/资源后建议「重新初始化资源」（`isResourceReady` 可能不重解压）。
- **打包前必须以目标产物校验**，勿假设当前 git checkout 就是要打的包（`feat/recruit-force-confirm-meet-times` 曾缺 preset）。

---

## 对下一个会话的特别提示

### 0. 当前推荐产物（2026-07-28）

| 项 | 值 |
|----|-----|
| APK | `app/build/outputs/apk/debug/app-debug.apk` |
| versionCode | **441**（440 因 `.DS_Store` 初始化失败，勿再用） |
| versionName | `0.14.4-alpha.26` |
| `.maaversion` | `v6.13.0-beta.2-54-gb413a132d5` |
| Core export | `MaaAssistantArknights/build/android-core-export-6066-recruit/` |
| Core commit | `b413a132d5`（`feat/android-core-6066-recruit-force-confirm`） |
| base | `v6.13.0-beta.2-52-g6066b6a6b4` |
| sha256 | `4dc7448843b628bc79ad3d1de1e528bb938cefdb04b0d3b617cca8c893a4b2a5` |
| 含 | station_preset + dorm OCR fail-open + `force_confirm_to_meet_times` |
| NCNN | 已转换 |

**核实标记**：`InfrastPresetTask`、`facility OCR failed, assume not stationed`、`force_confirm_to_meet_times`。

### 1. WordOcr / 资源加载失败 —— 禁止再犯

Hybrid deploy 会覆盖成 onnx-only；Android 必须有 `det.ncnn.param` / `rec.ncnn.param`。  
**禁止**在 deploy 后 `--skip-ncnn`。缺 NCNN 时脚本会 exit 1。装后必要时「重新初始化资源」。

### 1b. `.DS_Store` 导致资源初始化失败

Mac 上 Finder 会在 `install/resource` 写入 `.DS_Store`；deploy 原样拷进 assets → 进 APK → `AssetExtractor` 复制时报：`文件 MaaSync/MaaResource/.DS_Store 在 3 次尝试后仍失败`。  
防护：`deploy_local_maa_core.py` 跳过；`asset-manifest.gradle.kts` 不列入清单；`AssetExtractor` 运行时再过滤。打包后可用 `unzip -l app-debug.apk | rg DS_Store` 自检。

### 2. 公招新参数（Android 已同步）

- `RecruitConfig.forceConfirmToMeetTimes` → `force_confirm_to_meet_times`
- UI：常规设置，招募次数下方「优先保证最大招募数量」
- 默认 `false`

### 3. versionCode

当前 **440**；由 `.build-tools/last-version-code` 自动递增，保证可覆盖安装。

---

## 核心文档与脚本索引

| 用途 | 路径 |
|------|------|
| 本文 | `docs/CONTEXT.md` |
| 封装脚本 | `scripts/local_build_apk.sh` |
| Core 部署 | `scripts/deploy_local_maa_core.py` |
| NCNN | `scripts/convert_ocr_ncnn.py` |
| 公招 | `RecruitConfig.kt`, `RecruitConfigPanel.kt` |
| 基建预设 | `InfrastConfig.kt`, `InfrastConfigPanel.kt` |
| 本批 Core | `../MaaAssistantArknights/build/android-core-export-6066-recruit/` |
