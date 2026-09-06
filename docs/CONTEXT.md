# MAA-Meow 本地定制 Core · 会话状态快照

> 父会话 ID：6860a895-3ed6-4ab4-8d9a-97cac0edace2 → 当前：unknown  
> 最后更新：2026-09-06 22:07  
> 实质性事件计数：18  
> 接续方式：新 Chat 首条粘贴 `/session-continuity` + 文末 handoff 块

---

## 当前状态（一句话）

**可安装的 debug APK 为 versionCode 446**；Core `v6.17.2-8-gde8c9ebd90`；代理倍率 UI 已补 7~10。

---

## 进行中的话题

- 用户侧待验证：安装 **446** → 作战设置里代理倍率可选 7~10。

---

## 本会话已完成的工作

| 日期 | 事件 |
|------|------|
| 06~07 | 本地封装、station_preset UI、versionCode bump、NCNN 铁律、`.DS_Store` 防护 |
| 07-28 | export `6066-recruit` → APK **440/441** |
| 09-06 | `sync/dev-v2-custom-0906` @ `de8c9ebd90` → APK **442/444** 仍 LoadResource 失败 |
| 09-06 22:07 | asst.log：模板重名；`rsync --delete` 同步 `resource/` → `install/resource/` → APK **445** |

---

## 对下一个会话的特别提示

### 0. 当前推荐产物

| 项 | 值 |
|----|-----|
| APK | `app/build/outputs/apk/debug/app-debug.apk` |
| versionCode | **446** |
| versionName | `0.14.4-alpha.27` |
| `.maaversion` | `v6.17.2-8-gde8c9ebd90` |
| deploy | **full-custom** |

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
