#!/usr/bin/env bash
# Build MAA-Meow debug APK locally.
# Default: full-custom deploy (matching libMaaCore + libMaaUtils + OCR stack from install/).
# Hybrid (official OCR/utils + custom Core) is opt-in and breaks when Core >> cached tarball.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$ROOT/.build-tools"
SDK="$TOOLS/android-sdk"
MAA_INSTALL=""
FETCH_RUN=""
CORE_VERSION="local-facility-preset"
ABI="arm64-v8a"
SKIP_DEPLOY=""
SKIP_NCNN=""
NO_DAEMON=""
VERSION_CODE=""
HYBRID_OFFICIAL_SO=""

usage() {
  cat <<'EOF'
Usage: ./scripts/local_build_apk.sh [options]

Build a debug APK on this machine. After one-time bootstrap_build_env.sh,
you can rebuild in ~10 minutes without downloading GitHub Artifacts.

Options:
  --maa-install PATH   Path to MAA cmake install/ (resource/ + libMaaCore.so ...)
  --fetch-core-run ID  Download maa-android-arm64-install from a GitHub Actions run once
  --core-version VER   Label written to .maaversion (default: local-facility-preset)
  --abi ABI            arm64-v8a (default) or x86_64 — builds only this native ABI
  --version-code N     Force Android versionCode (for adb install -r when git history shrinks)
  --hybrid-official-so Use official release OCR/utils .so + custom libMaaCore only
                       (risky if Core is much newer than cached MAAComponent tarball)
  --skip-deploy        Skip deploy when jniLibs/assets already present
  --skip-ncnn          Skip onnx->ncnn OCR conversion (only if assets already have *.ncnn.param)
  --no-daemon          Disable Gradle daemon (default: keep daemon for faster rebuilds)
  -h, --help           Show this help

Examples:
  ./scripts/bootstrap_build_env.sh
  ./scripts/local_build_apk.sh --fetch-core-run 27903241649
  ./scripts/local_build_apk.sh --maa-install ../MaaAssistantArknights/install
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --maa-install) MAA_INSTALL="$2"; shift 2 ;;
    --fetch-core-run) FETCH_RUN="$2"; shift 2 ;;
    --core-version) CORE_VERSION="$2"; shift 2 ;;
    --abi) ABI="$2"; shift 2 ;;
    --skip-deploy) SKIP_DEPLOY=1; shift ;;
    --skip-ncnn) SKIP_NCNN=1; shift ;;
    --hybrid-official-so) HYBRID_OFFICIAL_SO=1; shift ;;
    --no-daemon) NO_DAEMON=1; shift ;;
    --version-code) VERSION_CODE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
done

if [[ -z "$MAA_INSTALL" && -z "$FETCH_RUN" ]]; then
  echo "[ERROR] Provide --maa-install or --fetch-core-run"
  usage
  exit 1
fi

if [[ ! -f "$ROOT/local.properties" ]]; then
  echo "[ERROR] Run ./scripts/bootstrap_build_env.sh first"
  exit 1
fi

if [[ -n "${JAVA_HOME:-}" && -x "$JAVA_HOME/bin/java" ]]; then
  :
elif [[ -x "$TOOLS/jdk-25/Contents/Home/bin/java" ]]; then
  export JAVA_HOME="$TOOLS/jdk-25/Contents/Home"
elif command -v /usr/libexec/java_home >/dev/null 2>&1; then
  export JAVA_HOME="$(/usr/libexec/java_home -v 25 2>/dev/null || /usr/libexec/java_home)"
else
  echo "[ERROR] JAVA_HOME not set; run bootstrap_build_env.sh"
  exit 1
fi

export ANDROID_HOME="$SDK"
export ANDROID_SDK_ROOT="$SDK"
export ANDROID_SDK_HOME="${ANDROID_SDK_HOME:-$TOOLS/android-home}"
export GRADLE_USER_HOME="${GRADLE_USER_HOME:-$TOOLS/gradle-home}"
mkdir -p "$ANDROID_SDK_HOME/.android" "$GRADLE_USER_HOME"
export PATH="$JAVA_HOME/bin:$SDK/cmdline-tools/latest/bin:$SDK/platform-tools:$PATH"

if [[ -n "$FETCH_RUN" ]]; then
  MAA_INSTALL="$TOOLS/maa-install"
  if [[ ! -f "$MAA_INSTALL/libMaaCore.so" ]]; then
    "$ROOT/scripts/fetch_ci_maa_core.sh" "$FETCH_RUN"
  else
    echo "[CACHE] Reusing $MAA_INSTALL"
  fi
fi

if [[ ! -f "$MAA_INSTALL/libMaaCore.so" ]]; then
  echo "[ERROR] libMaaCore.so not found under $MAA_INSTALL"
  exit 1
fi

REQUIRED_INSTALL_SO=(
  libMaaCore.so
  libMaaUtils.so
  libfastdeploy_ppocr.so
  libonnxruntime.so
  libopencv_world4.so
)
install_complete=1
for so in "${REQUIRED_INSTALL_SO[@]}"; do
  if [[ ! -f "$MAA_INSTALL/$so" ]]; then
    install_complete=0
    break
  fi
done

DEPLOY_ARGS=(
  --install-dir "$MAA_INSTALL"
  --abi "$ABI"
  --version "$CORE_VERSION"
)
if [[ -n "$HYBRID_OFFICIAL_SO" ]]; then
  echo "[DEPLOY] Hybrid deploy (official OCR/utils + custom libMaaCore)..."
  echo "[WARN] Hybrid can break LoadResource when Core version >> cached MAAComponent tarball."
  DEPLOY_ARGS+=(--hybrid-official-so)
elif [[ "$install_complete" -eq 1 ]]; then
  echo "[DEPLOY] Full-custom deploy (matching Core/Utils/OCR stack from install/)..."
else
  echo "[DEPLOY] install/ missing OCR/utils .so; falling back to hybrid official stack..."
  echo "[WARN] Prefer a complete cmake install/ for Core >= official tarball version."
  DEPLOY_ARGS+=(--hybrid-official-so)
fi

if [[ -n "$SKIP_DEPLOY" && -f "$ROOT/app/src/main/jniLibs/$ABI/libMaaCore.so" ]]; then
  echo "[SKIP] --skip-deploy: reusing deployed jniLibs/assets"
else
  python3 "$ROOT/scripts/deploy_local_maa_core.py" "${DEPLOY_ARGS[@]}"
fi

RESOURCE="$ROOT/app/src/main/assets/MaaSync/MaaResource"
NCNN_DET="$RESOURCE/PaddleOCR/det/det.ncnn.param"
needs_ncnn=0
if [[ -f "$RESOURCE/PaddleOCR/det/inference.onnx" ]] || [[ ! -f "$NCNN_DET" ]]; then
  needs_ncnn=1
fi

if [[ -n "$SKIP_NCNN" && "$needs_ncnn" -eq 1 ]]; then
  echo "[ERROR] --skip-ncnn requested but PaddleOCR lacks *.ncnn.param (deploy overwrote onnx-only)."
  echo "        Remove --skip-ncnn so convert_ocr_ncnn.py runs, or WordOcr will fail on device."
  exit 1
fi

if [[ -z "$SKIP_NCNN" && "$needs_ncnn" -eq 1 ]]; then
  echo "[NCNN] Converting OCR onnx -> ncnn (Android WordOcr requires det.ncnn.param / rec.ncnn.param)..."
  VENV="$ROOT/.venv"
  if [[ ! -x "$VENV/bin/python" ]]; then
    PY="$(command -v python3.12 || command -v python3)"
    "$PY" -m venv "$VENV"
  fi
  "$VENV/bin/python" -m pip install -q -r "$ROOT/scripts/requirements.txt"
  "$VENV/bin/python" "$ROOT/scripts/convert_ocr_ncnn.py" \
    --resource "$RESOURCE" \
    --cache "$ROOT/.maa-cache/ncnn"
elif [[ -z "$SKIP_NCNN" ]]; then
  echo "[SKIP] NCNN OCR models already present under assets"
fi

echo "[BUILD] assembleDebug (abi=$ABI) ..."
cd "$ROOT"
chmod +x ./gradlew

GIT_CODE="$(git rev-list --count HEAD)"
LAST_CODE_FILE="$TOOLS/last-version-code"
if [[ -z "$VERSION_CODE" ]]; then
  VERSION_CODE="$GIT_CODE"
  if [[ -f "$LAST_CODE_FILE" ]]; then
    LAST_CODE="$(<"$LAST_CODE_FILE")"
    if (( VERSION_CODE <= LAST_CODE )); then
      VERSION_CODE=$((LAST_CODE + 1))
      echo "[VERSION] git commit count dropped ($GIT_CODE <= $LAST_CODE); bump versionCode -> $VERSION_CODE"
    fi
  fi
else
  echo "[VERSION] Using explicit versionCode=$VERSION_CODE (git=$GIT_CODE)"
fi
echo "$VERSION_CODE" > "$LAST_CODE_FILE"

GRADLE_ARGS=(assembleDebug -PdevAbi="$ABI" -PversionCodeOverride="$VERSION_CODE")
if [[ -n "$NO_DAEMON" ]]; then
  GRADLE_ARGS+=(--no-daemon)
fi
./gradlew "${GRADLE_ARGS[@]}"

APK="$(find "$ROOT/app/build/outputs/apk/debug" -name '*.apk' | head -1)"
if [[ -z "$APK" ]]; then
  echo "[ERROR] APK not found"
  exit 1
fi

echo ""
echo "=========================================="
echo "[DONE] APK: $APK"
echo "Install: adb install -r \"$APK\""
echo "=========================================="
