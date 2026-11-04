# MAA-Meow personal integration, upstream v0.25.1

**Status:** Integration work branch, not certified APK/release.

- Official Android baseline: `Aliothmoon/MAA-Meow@8785acb293f64516dfa5b78d39cbe1b9dc2731db` (tag `v0.25.1`).
- Original custom source: `xjbsteven/MAA-Meow:codex/recycle-integration-20261015`.
- Core source pinned for *reproducible* Android CI: `xjbsteven/MaaAssistantArknights@d498de1587b7c3ac646f29f9164c157cefef5889` based on upstream Core v6.21.1.
- Do not build the old `v6.17.3-alpha.1-custom.ee8a1ad24f` SHA-locked scripts or silently accept the stock official binary.

## Feature decisions

| Feature | Previous custom paths | Upstream v0.25.1 | Decision |
| --- | --- | --- | --- |
| Facility-point station preset layout, room selection, rotation, dorm/shift auxiliaries and drone timing | `data/model/{StationPresetModels,InfrastConfig}.kt`, `domain/enums/InfrastRotationStyle.kt`, `presentation/view/panel/InfrastConfigPanel.kt` | Not available | Port into latest model and Compose UI |
| Recruit minimum-count guarantee and old `forceConfirmToMeetTimes` profile migration | `RecruitConfig.kt`, `RecruitProfileMigration.kt`, `RecruitConfigPanel.kt` | Not available | Port and preserve backwards deserialization |
| Conditional UI theme switching | `SwitchThemeConfig.kt`, `switchtheme/SwitchThemeConfigPanel.kt` | No conditional param | Port flag; paired Core must understand it |
| Recycle facility toggle | `InfrastRoomType.kt` | **Already supported** with `minCoreVersion=v6.20.0-beta.1` | Keep official enum, do not replace version guards |
| Recycle pickup popup | Old custom fallback proposal | Core v6.21.1 already recognizes and dismisses popup | Reuse official task resource and plugin |
| Standalone product collection | No pre-existing independent toggle | No explicit standalone configuration | Add `collectOnly` default false, serialize `collect_only`, show checkbox; paired Core runs only notification collection |
| New-home UI/roguelike compatibility | Older assets | v6.21.1 fixes home; PR #19003 was pending | Use upstream v6.21.1 resources and personal Core backport |
| Asset extraction and profile/settings migration | `AssetExtractor.kt`, `ConfigBackupManager.kt`, `TaskChainState.kt` | Significant upstream changes | Apply nonoverlapping personal changes and keep upstream additions |
| Fixed old-Core verification/deploy scripts | `scripts/verify_fixed_custom_core.py`, `scripts/deploy_fixed_custom_core.py`, `app/build.gradle.kts` | Official automatic Core provisioning | **Do not port old binary pins**, replace with CI compilation and embedded SHA checks |

## Build and test contract

In `.github/workflows/build-dev.yml` the integration branch CI downloads v6.21.1 runtime/OCR dependencies, builds the **pinned** custom Core Android arm64 from source, stages custom `libMaaCore.so` and `libMaaUtils.so` plus the matching resources, removes incompatible x86_64 libraries, writes a `.maaversion` containing the Core SHA, and checks that the embedded Core binary version matches. It runs a standalone C++ scheduling/recruit smoke test, Android lint, Kotlin `testDebugUnitTest`, then `assembleDebug`; output should be an ARM64 debug APK artifact.

**Only mark a stage as passed after inspecting the corresponding GitHub Actions run.** Branch creation and a committed workflow are not equivalent to a successful build. Old test sources retained in Core's removed `unit_test` build layout are not presented as executed.

## Device regression (not automatable by GitHub CI)

Back up current Android task profiles before installing any debug build; a debug/release signing mismatch may prevent in-place upgrade. Run with matching CN game data:

1. New home: enter base, public recruitment and credit store; return home between tasks.
2. New home to roguelike; check fallback light/dark mode.
3. Standard and station-preset shifts in manufacture/trading/center/reception/training/recycle/dorm.
4. Recycle reward popup: no stray click into settings; other product rewards still collected.
5. `collectOnly=true`: products collected while operator placements/drones unchanged.
6. Dorm low-trust autofill and Fiammetta recovery; confirm no accidental clear/replacements.
7. Restart app, export/import task profile; check old settings persist and Core version in logs.
8. Capture MAA logs and screenshots for any failed case. Do not interpret a successful APK compilation as a gameplay pass.

The legacy branches remain intact. No default-branch merge or Release is authorized.


## V909 feature-parity audit (2026-11-04)

The previous port used `codex/recycle-integration-20261015`, but the user's installed
v909 APK was built from the newer `feat/recycle-station-preset-20261015` branches:
Android `22c7c8ffaee117d2aa6e7747012e6a35b248237f` and
Core `af669690a02a4d58304f03cd294eb60e6bdde0cb`.
A comparison of the 12 Android and 13 Core files changed between these two historical
branches found the following previously omitted end-user capabilities:

- Station-preset `Recycle` room: appears in selection UI, remains off by default,
  is included by Select All, and stays selected across layout changes. Core recognizes
  `Recycle` by ID and by the Chinese OCR label `回收站`.
- Independent normal infrastructure automatic reward collection toggle:
  `collectBaseRewards` (legacy default `true`) is serialized as `collect`.
  Core v6.21.1's `InfrastBegin` automatically collects rewards, so `collect=false`
  selects `InfrastBeginNoCollect` with only the navigation chain.
  `collect_only=true` is a separate action and always collects without shifting.

The v909 custom popup click-recording ProcessTask actions and fallback
`InfrastRecycleReward*` task chain are *intentionally not restored*: official
Core v6.21.1 already has `InfrastRewardRecycleProduct` and its plugin.
The old v909 verification/build scripts are likewise replaced by the new CI
that builds a pinned custom Core, runs Kotlin/C++ tests and lint, and packages an APK.
The v909 custom version-name suffix is no longer used; Git-based versioning is kept.

The Android tests `StationPresetRecycleTest` and
`BaseRewardCollectionParamsTest` were also restored from the v909 branch.
This is a source-level and CI audit, not proof of gameplay on a real device;
the in-game preset and recycle popup must still be verified on the user's device.
