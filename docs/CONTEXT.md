# MAA-Meow 本地定制 Core · 会话状态快照

> 父会话 ID：6860a895-3ed6-4ab4-8d9a-97cac0edace2 → 当前：unknown  
> 最后更新：2026-07-01 13:55  
> 实质性事件计数：12  
> 接续方式：新 Chat 首条粘贴 `/session-continuity` + 文末 handoff 块

---

## 当前状态（一句话）

**可安装的 debug APK 为 versionCode 439**，内嵌 Core `v6.13.0-beta.2-52-g6066b6a6b4`（分支 `fix/dorm-trust-facility-ocr-fail-open` @ `6066b6a6b4`），Android UI 已对齐 Mac「进驻总览设施点预设」；**2026-07-01 13:52 已补回 PaddleOCR NCNN 模型**（修复 WordOcr 资源加载失败）。

---

## 进行中的话题

- 无阻塞项；用户侧待验证：安装 439 后「重新初始化资源」→ 资源加载是否正常。
- Core 侧 `fix/dorm-trust-facility-ocr-fail-open` 与 `dev-v2` 分支关系需持续关注（曾误打不含 facility_preset 的分支）。

---

## 本会话已完成的工作

| 日期 | 事件 |
|------|------|
| 06-21~06-25 | 打通 Mac 本地 hybrid 封装：`bootstrap_build_env.sh` + `deploy_local_maa_core.py` + `local_build_apk.sh` |
| 06-25~06-29 | Android UI 同步 `station_preset`：布局步进器、设施勾选、无人机、去除 JSON 排班；`InfrastConfig.toTaskParams` 发 `preset`/`drones` 对象 |
| 06-29 | 修正设施点预设提示文案（去掉菲亚梅塔误导说明） |
| 06-29 | `versionCode` 机制：`git rev-list --count` + `.build-tools/last-version-code` 自动 bump + `--version-code` 覆盖 |
| 07-01 | Core 分支 `fix/dorm-trust-facility-ocr-fail-open` 重建，含 `e951e1b3a2`（设施预设）+ `f7122ebc8f`（宿舍信赖 OCR fail-open） |
| 07-01 | 误用 `--skip-ncnn` 打出 438 → 真机 WordOcr 失败；补 NCNN 后打出 **439**，脚本增加 `--skip-ncnn` 缺 NCNN 时 **直接报错退出** |

---

## 尚未解决的问题

- `docs/BUILDING.md` 仍只写官方 `setup_maa_core.py` 流程，**未收录**本地定制 Core 封装步骤（可后续合并进 BUILDING 或链到本文）。
- 覆盖安装后若 app 版本未变，`isResourceReady` 可能不重解压 assets；**NCNN 缺失时「重新初始化资源」仍必要**，但初始化源必须是 **APK 内已含 NCNN** 的包。
- `dev-v2` 本地仍可能有 `e951e1b3a2` facility_preset 提交；**打包前必须以目标分支 `git log` + `InfrastPresetTask.cpp` 存在性校验**，勿假设分支名。

---

## 对下一个会话的特别提示

### 1. 【高频复发】WordOcr / 资源加载失败 —— 禁止再犯

**症状（日志）**

```
asst::OcrPack::load | leave, 0 ms
WordOcr load failed, path: .../Maa/resource/PaddleOCR
MaaResourceLoader LoadResource failed: .../files/Maa
```

**根因**

- Hybrid `deploy_local_maa_core.py` 会用**官方 release tarball 覆盖** `PaddleOCR` / `PaddleCharOCR` 为 **onnx-only**。
- Android Core **必须**有 `det.ncnn.param`、`rec.ncnn.param`（及对应 `.bin`），**不能**只有 `inference.onnx`。
- 使用 `--skip-ncnn` 或在 deploy 后未跑 `convert_ocr_ncnn.py` → APK assets 无 NCNN → 装机必挂。
- 「重新初始化资源」只是把 APK assets 再解压一遍；**若 APK 里就没有 NCNN，重初始化无效**（2026-07-01 13:49 日志已验证）。

**标准封装铁律**

```bash
cd /Users/xujiabin/project/MaaAssistantArknights
# 确认分支与 HEAD（见下文「Core 分支」）
cmake --build build-android --parallel $(sysctl -n hw.logicalcpu)
cmake --install build-android --prefix install
cp /Users/xujiabin/project/MAA-Meow/.build-tools/maa-install/libMaaAndroidNativeControlUnit.so install/

cd /Users/xujiabin/project/MAA-Meow
# 不要加 --skip-ncnn（除非 assets 里已有 *.ncnn.param 且未重新 deploy）
./scripts/local_build_apk.sh --maa-install ../MaaAssistantArknights/install
```

**打包后自检（本地）**

```bash
ls app/src/main/assets/MaaSync/MaaResource/PaddleOCR/det/det.ncnn.param
ls app/src/main/assets/MaaSync/MaaResource/PaddleOCR/rec/rec.ncnn.param
```

**装后若仍失败**：设置 → **重新初始化资源**（不清任务/排班/设置）。

**脚本保护（2026-07-01 起）**：`local_build_apk.sh` 在缺 NCNN 时传 `--skip-ncnn` 会 **exit 1**。

---

### 2. versionCode vs versionName（安装「无法降级」）

| 字段 | 来源 | 用户可见 |
|------|------|----------|
| `versionCode` | `git rev-list --count` 或 `--version-code` / `.build-tools/last-version-code` 递增 | 一般不可见；**决定能否 `adb install -r` 覆盖** |
| `versionName` | `git describe` → 如 `0.14.4-alpha.24` | 设置里常见；**alpha 数字变小不等于降级** |

覆盖安装失败 → 用 `local_build_apk.sh` 自动 bump，或 `--version-code N` 显式抬高。

---

### 3. Core 分支与打包前校验

| 仓库 | 路径 |
|------|------|
| MAA Core | `/Users/xujiabin/project/MaaAssistantArknights` |
| MAA-Meow | `/Users/xujiabin/project/MAA-Meow` |

**当前应使用的 Core 分支（2026-07-01）**

- 分支：`fix/dorm-trust-facility-ocr-fail-open`
- HEAD：`6066b6a6b4`
- 必含提交：
  - `e951e1b3a2` — 设施预设换班 / 进驻总览 `station_preset`
  - `f7122ebc8f` — 宿舍信赖补位 OCR fail-open

**打包前必跑**

```bash
cd /Users/xujiabin/project/MaaAssistantArknights
git branch --show-current
git rev-parse --short HEAD
git log -3 --oneline
test -f src/MaaCore/Task/Infrast/InfrastPresetTask.cpp && echo "preset OK"
```

若从 `game` 轮换切到 `station_preset` 后 Core 无 `InfrastPresetTask` → **换班 UI 有、Core 无**，任务会失败。曾发生：分支重建前误打 `3410d7c815` 仅含 dorm fix、不含 preset 的包。

**切换分支后**：若增删了 `InfrastPresetTask` 等源文件，需 **重新 cmake 配置** `build-android`（不能只增量 ninja）。

```bash
NDK=/Users/xujiabin/project/MAA-Meow/.build-tools/android-sdk/ndk/29.0.13113456
VER=$(git describe --tags --match 'v*' HEAD)
cmake -B build-android --preset android-publish-arm64 \
  -DCMAKE_TOOLCHAIN_FILE="$NDK/build/cmake/android.toolchain.cmake" \
  -DMAA_HASH_VERSION="$VER"
```

---

### 4. Android UI ↔ Core API（`station_preset`）

Mac / Android 已对齐：**不再**用 JSON `filename`/`plan_index` 驱动设施点预设，改为内联参数：

```json
{
  "mode": 20000,
  "rotation_style": "station_preset",
  "facility": ["Mfg"],
  "preset": { "rooms": ["Control", "Mfg1", ...], "rest": true },
  "drones": { "enable": true, "room": "trading", "index": 1, "order": "pre" }
}
```

关键 Kotlin：`InfrastConfig.kt`、`StationPresetModels.kt`、`InfrastConfigPanel.kt`。  
多班次：**多个基建任务**，每任务一个班次（非 JSON 多 plan 自增）。

自定义 JSON 排班（153/243 等）仅在 **Custom 模式**；`autoAdvancePlanIndex` 仅 Custom。

---

### 5. 标准本地封装流程（增量 ~2–3 分钟）

```bash
MAA=/Users/xujiabin/project/MaaAssistantArknights
MEOW=/Users/xujiabin/project/MAA-Meow
export JAVA_HOME="$MEOW/.build-tools/jdk-25/Contents/Home"

cd "$MAA"
VER=$(git describe --tags --match 'v*' HEAD)
cmake --build build-android --parallel $(sysctl -n hw.logicalcpu)
cmake --install build-android --prefix install
cp "$MEOW/.build-tools/maa-install/libMaaAndroidNativeControlUnit.so" install/

cd "$MEOW"
./scripts/local_build_apk.sh --maa-install "$MAA/install" --core-version "$VER"
# 仅改 Gradle/UI、Core 未变：可加 --skip-deploy
# 绝不在 deploy 后 --skip-ncnn
```

**产出**

- APK：`app/build/outputs/apk/debug/app-debug.apk`
- Core 版本标记：`.maaversion`
- 最近 versionCode 记录：`.build-tools/last-version-code`（当前 **439**）

---

### 6. 其他踩坑备忘

- **首次**全量编 Android Core + maadeps 下载：约几十分钟；之后增量秒级~分钟级。
- `app/build.gradle.kts` 有 `keepDebugSymbols`，防 AGP strip 破坏预编译 `.so`。
- 模拟器可测 UI/OCR；Shizuku/虚拟屏/完整自动化以真机为准。
- 息屏锁屏时内置定时一般不跑；外部自动化用 Tasker 等 `am start`。

---

## 核心文档与脚本索引

| 用途 | 路径 |
|------|------|
| **本文（会话继承）** | `docs/CONTEXT.md` |
| 通用构建说明 | `docs/BUILDING.md` |
| 本地封装脚本 | `scripts/local_build_apk.sh` |
| 环境引导 | `scripts/bootstrap_build_env.sh` |
| Core 部署 | `scripts/deploy_local_maa_core.py` |
| OCR NCNN 转换 | `scripts/convert_ocr_ncnn.py` |
| Android 基建配置 | `app/.../InfrastConfig.kt`, `InfrastConfigPanel.kt` |
| Core 设施预设 | `MaaAssistantArknights/src/MaaCore/Task/Infrast/InfrastPresetTask.cpp` |
| Core 接口 | `MaaAssistantArknights/src/MaaCore/Task/Interface/InfrastTask.cpp` |
| Mac UI 参考 | `MaaAssistantArknights/src/MaaMacGui/.../InfrastSettingsView.swift`, `StationPresetSupport.swift` |

---

## session-continuity 使用约定（本项目）

- 长期线程（本地封装 + 定制 Core + Android UI 同步）默认维护 **本文**。
- 发生实质性事件后：**先更新 `docs/CONTEXT.md`，再回复用户**。
- 上下文 ≥65% 或自然断点时：当前 Chat 发 `/session-continuity` 生成交接包 → **新 Chat** 粘贴包接续。
- 打包类任务交接时务必更新：**Core 分支/HEAD、.maaversion、last-version-code、是否含 NCNN**。
