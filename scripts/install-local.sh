#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd "$SCRIPT_DIR/.." && pwd)
SOURCE="$ROOT_DIR/dignity-sentinel"
BIN_DIR="${DIGNITY_SENTINEL_BIN_DIR:-$HOME/.local/bin}"
TARGET="$BIN_DIR/dignity-sentinel"

if [ ! -x "$SOURCE" ]; then
  echo "dignity-sentinel source is not executable: $SOURCE" >&2
  exit 1
fi

mkdir -p "$BIN_DIR"

if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then
  CURRENT=$(readlink "$TARGET" 2>/dev/null || true)
  if [ "$CURRENT" = "$SOURCE" ]; then
    echo "dignity-sentinel already installed at: $TARGET"
    echo "No shell profile, PATH, telemetry, updater, or background service was modified."
    exit 0
  fi
  echo "Refusing to overwrite existing file: $TARGET" >&2
  echo "Set DIGNITY_SENTINEL_BIN_DIR to a different directory if needed." >&2
  exit 1
fi

ln -s "$SOURCE" "$TARGET"

echo "Installed dignity-sentinel symlink at: $TARGET"
echo "Source: $SOURCE"
echo "Add this directory to PATH manually if you choose: $BIN_DIR"
echo "No shell profile, PATH, telemetry, updater, or background service was modified."
