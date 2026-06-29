#!/usr/bin/env sh
set -eu

DATA_DIR="${HERMES_DATA_DIR:-/opt/data}"
PROFILE_SRC="${AETHOS_ATLAS_PROFILE_SRC:-/opt/aethos/atlas-profile}"
REFRESH_PROFILE="${AETHOS_HERMES_REFRESH_PROFILE:-false}"

copy_if_missing_or_refresh() {
  src="$1"
  dst="$2"
  if [ "$REFRESH_PROFILE" = "true" ] || [ ! -f "$dst" ]; then
    cp "$src" "$dst"
  fi
}

mkdir -p "$DATA_DIR" "$DATA_DIR/skills"

if [ -f "$PROFILE_SRC/SOUL.md" ]; then
  copy_if_missing_or_refresh "$PROFILE_SRC/SOUL.md" "$DATA_DIR/SOUL.md"
fi

if [ -f "$PROFILE_SRC/config.yaml" ]; then
  copy_if_missing_or_refresh "$PROFILE_SRC/config.yaml" "$DATA_DIR/config.yaml"
fi

if [ -f "$PROFILE_SRC/mcp.json" ]; then
  copy_if_missing_or_refresh "$PROFILE_SRC/mcp.json" "$DATA_DIR/mcp.json"
fi

if [ -d "$PROFILE_SRC/skills" ]; then
  cp -R "$PROFILE_SRC/skills/." "$DATA_DIR/skills/"
fi

exec hermes "$@"
