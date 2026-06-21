#!/usr/bin/env bash
# Download maa-android-arm64-install from a GitHub Actions run (Azure blob, resumable).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$ROOT/.build-tools"
DEST="$TOOLS/maa-install"
ZIP="$TOOLS/maa-install.zip"
RUN_ID=""
REPO="${GITHUB_REPO:-xjbsteven/MAA-Meow}"
ARTIFACT_NAME="maa-android-arm64-install"

usage() {
  cat <<'EOF'
Usage: ./scripts/fetch_ci_maa_core.sh RUN_ID

Downloads CI artifact maa-android-arm64-install (~175MB) to .build-tools/maa-install/
Uses GitHub API redirect -> Azure blob (usually faster than gh run download).
Supports resume if .build-tools/maa-install.zip already exists.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    *) RUN_ID="$1"; shift ;;
  esac
done

if [[ -z "$RUN_ID" ]]; then
  echo "[ERROR] Provide GitHub Actions run ID"
  usage
  exit 1
fi

if [[ -f "$DEST/libMaaCore.so" ]]; then
  echo "[CACHE] Already present: $DEST"
  exit 0
fi

artifact_id="$(gh api "repos/${REPO}/actions/runs/${RUN_ID}/artifacts" \
  --jq ".artifacts[] | select(.name==\"${ARTIFACT_NAME}\") | .id" | head -1)"
if [[ -z "$artifact_id" || "$artifact_id" == "null" ]]; then
  echo "[ERROR] Artifact ${ARTIFACT_NAME} not found on run ${RUN_ID}"
  exit 1
fi

size_bytes="$(gh api "repos/${REPO}/actions/artifacts/${artifact_id}" --jq '.size_in_bytes')"
size_mb="$(python3 - <<PY
print(f"{int('${size_bytes}')/1024/1024:.1f}")
PY
)"

blob_url="$(curl -sI \
  -H "Authorization: Bearer $(gh auth token)" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPO}/actions/artifacts/${artifact_id}/zip" \
  | grep -i '^location:' | cut -d' ' -f2- | tr -d '\r\n')"

if [[ -z "$blob_url" ]]; then
  echo "[ERROR] Could not resolve Azure blob URL for artifact ${artifact_id}"
  exit 1
fi

mkdir -p "$TOOLS" "$DEST"
if [[ -f "$ZIP" ]]; then
  have="$(stat -f%z "$ZIP" 2>/dev/null || stat -c%s "$ZIP")"
  if [[ "$have" -eq "$size_bytes" ]]; then
    echo "[FETCH] Zip already complete (${size_mb}MB), extracting..."
  elif [[ "$have" -gt "$size_bytes" ]]; then
    echo "[WARN] Existing zip is larger than artifact; re-downloading fresh"
    rm -f "$ZIP"
  else
    echo "[FETCH] Resuming ${have} / ${size_bytes} bytes"
  fi
fi

echo "[FETCH] ${ARTIFACT_NAME} (~${size_mb}MB) from run ${RUN_ID}"
echo "        dest:   ${DEST}"

if [[ ! -f "$ZIP" ]] || [[ "$(stat -f%z "$ZIP" 2>/dev/null || stat -c%s "$ZIP")" -ne "$size_bytes" ]]; then
  if command -v aria2c >/dev/null; then
    aria2c -x 16 -s 16 -k 1M --file-allocation=none -c -o "$(basename "$ZIP")" -d "$TOOLS" "$blob_url"
  else
    curl -fL --retry 5 --retry-delay 2 --connect-timeout 30 --http2 \
      -C - --progress-bar -o "$ZIP" "$blob_url"
  fi
fi

echo "[FETCH] Verifying zip..."
unzip -t "$ZIP" >/dev/null

echo "[FETCH] Extracting..."
rm -rf "$DEST"
mkdir -p "$DEST"
unzip -qo "$ZIP" -d "$DEST"
rm -f "$ZIP"

if [[ ! -f "$DEST/libMaaCore.so" ]]; then
  echo "[ERROR] libMaaCore.so missing after extract"
  exit 1
fi

echo "[FETCH OK] $(du -sh "$DEST" | awk '{print $1}') -> $DEST"
