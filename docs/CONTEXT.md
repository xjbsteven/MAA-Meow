# MAA-Meow 本地定制 Core · 会话状态快照

> 父会话 ID：6860a895-3ed6-4ab4-8d9a-97cac0edace2 → 当前：unknown  
> 最后更新：2026-09-07 21:54  
> 实质性事件计数：19  
> 接续方式：新 Chat 首条粘贴 `/session-continuity` + 文末 handoff 块

---

## 当前状态（一句话）

已在 `sync/upstream-v0.21-keep-local` 完成 Aliothmoon/MAA-Meow 上游整体合并并保留本地定制；**可安装 debug APK 为 versionCode 447**，Core `v6.17.2-8-gde8c9ebd90`。

---

## 进行中的话题

- 用户侧待验证：覆盖安装 **447**，确认资源加载、设施点预设、公招强制确认和上游新 UI 均正常。

---

## 本会话已完成的工作

| 日期 | 事件 |
|------|------|
| 06~07 | 本地封装、station_preset UI、versionCode bump、NCNN 铁律、`.DS_Store` 防护 |
| 07-28 | export `6066-recruit` → APK **440/441** |
| 09-06 | `sync/dev-v2-custom-0906` @ `de8c9ebd90` → APK **442/444** 仍 LoadResource 失败 |
| 09-06 22:07 | asst.log：模板重名；`rsync --delete` 同步 `resource/` → `install/resource/` → APK **445** |
| 09-07 | 合并 `upstream/main`（上游 v0.21.x 大版本结构），以上游新架构为骨架，保留本地 station_preset、公招 `force_confirm_to_meet_times`、会客室接收线索、完整 Core/NCNN 打包、版本号自动递增和垃圾文件过滤 |
| 09-07 21:50 | Core `de8c9ebd90` full-custom 部署：9342 个资源、6 个 so、8 组 NCNN 缓存；生成 APK **447**；源码编译、i18n 校验、全部 debug 单元测试通过 |

---

## 对下一个会话的特别提示

### 0. 当前推荐产物

| 项 | 值 |
|----|-----|
| APK | `app/build/outputs/apk/debug/app-debug.apk` |
| SHA-256 | `026cac723362acfd959027cccb48dd4815b260c5da8c43c8e2abb700ec814f16` |
| versionCode | **447** |
| versionName | `0.14.4-alpha.28` |
| `.maaversion` | `v6.17.2-8-gde8c9ebd90` |
| deploy | **full-custom** |

### 合并状态

- 分支：`sync/upstream-v0.21-keep-local`
- 上游：`upstream/main`，整体合并保留上游新增功能与测试
- 本地定制：station_preset、`force_confirm_to_meet_times`、`reception_receive_clue`、代理倍率 7~10、完整 Core/NCNN 构建链
- 构建工具升级后的依赖已进入 `~/.gradle` 缓存；根工程及 `build-logic` 均加入阿里云镜像与官方回退
- 验证：`:app:compileDebugKotlin`、`:app:testDebugUnitTest`、`assembleDebug` 均成功；APK 内含 6 个 arm64 so 和 PaddleOCR NCNN 文件，未发现 `.DS_Store`

### 1. 封装铁律

- cmake `install(DIRECTORY resource)` **不会删除**已搬走的文件。跨版本封装前必须：
  `rsync -a --delete "$MAA/resource/" "$MAA/install/resource/"`
- deploy 会检查同一 template 树内（排除 UiTheme）同名 png；撞名会直接失败
- install/ 齐全时默认 full-custom；`--hybrid-official-so` 仅回退
- 勿拷 `libc++_shared.so`；deploy 后禁止缺 NCNN 时 `--skip-ncnn`

### 2. 442/444 真因（asst.log，不是 hybrid SO）

```
Templ file exists in multiple paths:
  .../template/InfrastPic/Drone/DroneConfirm.png
  .../template/InfrastPic/Dorm/DroneConfirm.png
TaskData load failed
```

官方已把无人机模板从 `Dorm/` 迁到 `Drone/`（#17952），但 `install/` 里 6 月残留目录还在。OCR/NCNN 正常（`OcrPack::load | leave, 0 ms` 只是延迟加载，不是失败）。

---

## 核心路径

| 用途 | 路径 |
|------|------|
| 本文 | `docs/CONTEXT.md` |
| 封装 | `scripts/local_build_apk.sh` |
| 部署 | `scripts/deploy_local_maa_core.py` |
| Core 仓库 | `../MaaAssistantArknights` |
