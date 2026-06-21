#!/usr/bin/env bash
# Build MAA-Meow debug APK locally (hybrid deploy: official OCR stack + custom libMaaCore).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$ROOT/.build-tools"
SDK="$TOOLS/android-sdk"
MAA_INSTALL=""
FETCH_RUN=""
CORE_VERSION="local-facility-preset"
ABI="arm64-v8a"

usage() {
  cat <<'EOF'
Usage: ./scripts/local_build_apk.sh [options]

Build a debug APK on this machine. After one-time bootstrap_build_env.sh,
you can rebuild in ~10 minutes without downloading GitHub Artifacts.

Options:
  --maa-install PATH   Path to MAA cmake install/ (resource/ + libMaaCore.so ...)
  --fetch-core-run ID  Download maa-android-arm64-install from a GitHub Actions run once
  --core-version VER   Label written to .maaversion (default: local-facility-preset)
  --abi ABI            arm64-v8a (default) or x86_64
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
export PATH="$JAVA_HOME/bin:$SDK/cmdline-tools/latest/bin:$SDK/platform-tools:$PATH"

if [[ -n "$FETCH_RUN" ]]; then
  MAA_INSTALL="$TOOLS/maa-install"
  if [[ ! -f "$MAA_INSTALL/libMaaCore.so" ]]; then
    echo "[FETCH] Downloading maa-android-arm64-install from run $FETCH_RUN ..."
    mkdir -p "$MAA_INSTALL"
    gh run download "$FETCH_RUN" --repo xjbsteven/MAA-Meow \
      --name maa-android-arm64-install -D "$MAA_INSTALL"
  else
    echo "[CACHE] Reusing $MAA_INSTALL"
  fi
fi

if [[ ! -f "$MAA_INSTALL/libMaaCore.so" ]]; then
  echo "[ERROR] libMaaCore.so not found under $MAA_INSTALL"
  exit 1
fi

echo "[DEPLOY] Hybrid deploy (official OCR/utils + custom libMaaCore)..."
python3 "$ROOT/scripts/deploy_local_maa_core.py" \
  --install-dir "$MAA_INSTALL" \
  --abi "$ABI" \
  --version "$CORE_VERSION" \
  --hybrid-official-so

echo "[BUILD] assembleDebug ..."
cd "$ROOT"
chmod +x ./gradlew
./gradlew assembleDebug --no-daemon

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
