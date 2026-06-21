#!/usr/bin/env bash
# One-time local build environment under .build-tools/ (gitignored).
# Android SDK/NDK: Tencent mirror. JDK: Tsinghua Adoptium mirror (macOS aarch64).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$ROOT/.build-tools"
SDK="$TOOLS/android-sdk"
NDK_VER="29.0.13113456"
CMAKE_VER="3.22.1"
JDK_MAJOR="25"
ANDROID_MIRROR="${ANDROID_MIRROR:-https://mirrors.cloud.tencent.com/AndroidSDK}"
ANDROID_SDK_HOME="${ANDROID_SDK_HOME:-$TOOLS/android-home}"

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

  echo "[JDK] Downloading Temurin ${JDK_MAJOR} (macOS aarch64, Tsinghua mirror)..."
  local tgz="$TOOLS/jdk.tgz"
  curl -fL --retry 3 --connect-timeout 30 -o "$tgz" \
    "https://mirrors.tuna.tsinghua.edu.cn/Adoptium/${JDK_MAJOR}/jdk/aarch64/mac/OpenJDK${JDK_MAJOR}U-jdk_aarch64_mac_hotspot_${JDK_MAJOR}.0.3_9.tar.gz"
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
  mkdir -p "$TOOLS/dl/extract" "$SDK"

  if [[ -x "$SDK/cmdline-tools/latest/bin/sdkmanager" ]]; then
    echo "[SDK] cmdline-tools already present: $SDK"
  else
    echo "[SDK] Downloading commandline-tools (~137MB, Tencent mirror)..."
    mkdir -p "$TOOLS/dl"
    local zip="$TOOLS/dl/commandlinetools-mac.zip"
    curl -fL --retry 3 --connect-timeout 30 -C - --progress-bar -o "$zip" \
      "${ANDROID_MIRROR}/commandlinetools-mac-13114758_latest.zip"
    rm -rf "$SDK/cmdline-tools"
    mkdir -p "$SDK/cmdline-tools"
    unzip -qo "$zip" -d "$SDK/cmdline-tools"
    mv "$SDK/cmdline-tools/cmdline-tools" "$SDK/cmdline-tools/latest"
    rm -f "$zip"
    echo "[SDK] Installed cmdline-tools -> $SDK"
  fi

  mkdir -p "$ANDROID_SDK_HOME/.android" "$SDK/licenses"
  cat > "$ANDROID_SDK_HOME/.android/repositories.cfg" <<EOF
### User Sources for Android SDK Manager (project-local)
count=1
enabled0=true
src0=${ANDROID_MIRROR}/repository2-1.xml
EOF
  export ANDROID_SDK_HOME
  # Pre-accept common licenses so Gradle/sdkmanager won't block later.
  for lic in android-sdk-license android-sdk-preview-license; do
    echo "24333f8a63b6825ea9c5514f83c2829b004d1fee" > "$SDK/licenses/${lic}"
  done

  fetch_and_unzip() {
    local label="$1"
    local url="$2"
    local dest="$3"
    local zip="$TOOLS/dl/$(basename "$url")"
    if [[ -d "$dest" ]]; then
      echo "[SDK] Already present: $label"
      return
    fi
    echo "[SDK] Downloading $label ..."
    echo "      URL: ${ANDROID_MIRROR}/${url}"
    curl -fL --retry 3 --connect-timeout 30 -C - --progress-bar -o "$zip" \
      "${ANDROID_MIRROR}/${url}"
    rm -rf "$TOOLS/dl/extract/"*
    unzip -qo "$zip" -d "$TOOLS/dl/extract"
    rm -f "$zip"
    local top
    top="$(find "$TOOLS/dl/extract" -mindepth 1 -maxdepth 1 -type d | head -1)"
    mkdir -p "$(dirname "$dest")"
    mv "$top" "$dest"
    echo "[SDK] Installed $label -> $dest"
  }

  fetch_and_unzip "build-tools 36.0.0 (~75MB)" \
    "build-tools_r36_macosx.zip" "$SDK/build-tools/36.0.0"
  fetch_and_unzip "platform android-36 (~62MB)" \
    "platform-36-ext19_r01.zip" "$SDK/platforms/android-36"
  fetch_and_unzip "CMake ${CMAKE_VER} (~36MB)" \
    "cmake-${CMAKE_VER}-darwin.zip" "$SDK/cmake/${CMAKE_VER}"
  fetch_and_unzip "NDK ${NDK_VER} (~980MB, slowest step)" \
    "android-ndk-r29-beta1-darwin.zip" "$SDK/ndk/${NDK_VER}"
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
