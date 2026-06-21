#!/usr/bin/env bash
# One-time local build environment under .build-tools/ (gitignored).
# Android SDK/NDK: Aliyun mirror. JDK: Tsinghua Adoptium mirror (macOS aarch64).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$ROOT/.build-tools"
SDK="$TOOLS/android-sdk"
NDK_VER="29.0.13113456"
CMAKE_VER="3.22.1"
JDK_MAJOR="25"
ANDROID_MIRROR="${ANDROID_MIRROR:-https://mirrors.aliyun.com/android/repository}"

mkdir -p "$TOOLS"

find_java_home() {
  if [[ -n "${JAVA_HOME:-}" && -x "$JAVA_HOME/bin/java" ]]; then
    echo "$JAVA_HOME"
    return
  fi
  local cached="$TOOLS/jdk-${JDK_MAJOR}"
  if [[ -d "$cached" && -x "$cached/Contents/Home/bin/java" ]]; then
    echo "$cached/Contents/Home"
    return
  fi
  if /usr/libexec/java_home -v "${JDK_MAJOR}" 2>/dev/null; then
    return
  fi
  echo ""
}

install_jdk() {
  local jhome
  jhome="$(find_java_home || true)"
  if [[ -n "$jhome" ]]; then
    echo "[JDK] Using $jhome"
    export JAVA_HOME="$jhome"
    return
  fi

  echo "[JDK] Downloading Temurin ${JDK_MAJOR} (macOS aarch64)..."
  local tgz="$TOOLS/jdk.tgz"
  curl -fL --retry 3 --connect-timeout 30 -o "$tgz" \
    "https://api.adoptium.net/v3/binary/latest/${JDK_MAJOR}/ga/mac/aarch64/jdk/hotspot/normal/eclipse?project=jdk"
  rm -rf "$TOOLS/jdk-${JDK_MAJOR}"
  tar -xzf "$tgz" -C "$TOOLS"
  rm -f "$tgz"
  local extracted
  extracted="$(find "$TOOLS" -maxdepth 1 -type d -name 'jdk-*' | head -1)"
  mv "$extracted" "$TOOLS/jdk-${JDK_MAJOR}"
  export JAVA_HOME="$TOOLS/jdk-${JDK_MAJOR}/Contents/Home"
  echo "[JDK] Installed to $JAVA_HOME"
}

install_android_sdk() {
  if [[ -x "$SDK/cmdline-tools/latest/bin/sdkmanager" ]]; then
    echo "[SDK] Already present: $SDK"
  else
    echo "[SDK] Downloading commandline-tools (Aliyun)..."
    mkdir -p "$TOOLS/dl"
    local zip="$TOOLS/dl/commandlinetools-mac.zip"
    curl -fL --retry 3 --connect-timeout 30 -o "$zip" \
      "${ANDROID_MIRROR}/commandlinetools-mac-13114758_latest.zip"
    rm -rf "$SDK/cmdline-tools"
    mkdir -p "$SDK/cmdline-tools"
    unzip -qo "$zip" -d "$SDK/cmdline-tools"
    mv "$SDK/cmdline-tools/cmdline-tools" "$SDK/cmdline-tools/latest"
    rm -f "$zip"
    echo "[SDK] Installed cmdline-tools -> $SDK"
  fi

  yes | "$SDK/cmdline-tools/latest/bin/sdkmanager" --sdk_root="$SDK" --licenses >/dev/null || true
  echo "[SDK] Installing NDK ${NDK_VER} and CMake ${CMAKE_VER}..."
  "$SDK/cmdline-tools/latest/bin/sdkmanager" --sdk_root="$SDK" \
    "ndk;${NDK_VER}" "cmake;${CMAKE_VER}" "platforms;android-36" "build-tools;36.0.0"
}

write_local_properties() {
  cat > "$ROOT/local.properties" <<EOF
sdk.dir=$SDK
EOF
  echo "[CONFIG] Wrote $ROOT/local.properties"
}

install_jdk
install_android_sdk
write_local_properties

cat <<EOF

[Bootstrap OK]
  JAVA_HOME=$JAVA_HOME
  Android SDK=$SDK

Next:
  # If you already have MAA install/ (from CI artifact or local MAA build):
  ./scripts/local_build_apk.sh --maa-install /path/to/install

  # Or fetch Core install tree once from a successful CI run:
  ./scripts/local_build_apk.sh --fetch-core-run 27905867677

EOF
