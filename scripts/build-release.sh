#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
DIST_DIR="${DIGNITY_RELEASE_DIST_DIR:-$ROOT_DIR/dist}"
VERSION=$(cat "$ROOT_DIR/VERSION")
BUNDLE_NAME="dignity-sentinel-v$VERSION.tar.gz"
BUNDLE="$DIST_DIR/$BUNDLE_NAME"
BUNDLE_CHECKSUM="$DIST_DIR/dignity-sentinel-v$VERSION.sha256"
MANIFEST="$DIST_DIR/release-manifest.json"
CHECKSUMS_FILE="$DIST_DIR/checksums.txt"
TEST_RESULT_JSON="$DIST_DIR/test-result.json"
TEST_OUTPUT="$DIST_DIR/test-output.txt"
TEST_COMMAND="${DIGNITY_RELEASE_TEST_COMMAND:-python3 -m unittest discover -s tests}"

sha256_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

sha256_stdin() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | awk '{print $1}'
  else
    sha256sum | awk '{print $1}'
  fi
}

json_escape() {
  sed 's/\\/\\\\/g; s/"/\\"/g'
}

if [ -f "$BUNDLE" ] || [ -f "$BUNDLE_CHECKSUM" ]; then
  echo "Refusing to overwrite release bundle for version $VERSION: $BUNDLE" >&2
  exit 1
fi

mkdir -p "$DIST_DIR"

(
  cd "$ROOT_DIR"
  sh -c "$TEST_COMMAND" > "$TEST_OUTPUT" 2>&1
)

SOURCE_HASH=$(
  cd "$ROOT_DIR"
  find AGENTS.md README.md dignity-sentinel docs policy schemas scripts src tests VERSION -type f ! -path '*/__pycache__/*' | LC_ALL=C sort | while IFS= read -r file; do
    printf '%s  %s\n' "$(sha256_file "$file")" "$file"
  done | sha256_stdin
)

AUDIT_EVENT_SCHEMA_HASH=$(sha256_file "$ROOT_DIR/schemas/audit_event.schema.json")
AUTONOMY_ENVELOPE_SCHEMA_HASH=$(sha256_file "$ROOT_DIR/schemas/autonomy_envelope.schema.json")
BOUNDARY_EVENT_SCHEMA_HASH=$(sha256_file "$ROOT_DIR/schemas/boundary_event.schema.json")
CAUSAL_ENVELOPE_SCHEMA_HASH=$(sha256_file "$ROOT_DIR/schemas/causal_envelope.schema.json")
DIGNITY_MANIFEST_SCHEMA_HASH=$(sha256_file "$ROOT_DIR/schemas/dignity_manifest.schema.json")
HUMANITAS_ATTESTATION_SCHEMA_HASH=$(sha256_file "$ROOT_DIR/schemas/humanitas_attestation.schema.json")
HUMANITAS_MANIFEST_SCHEMA_HASH=$(sha256_file "$ROOT_DIR/schemas/humanitas_manifest.schema.json")
ROOT_BUNDLE_SCHEMA_HASH=$(sha256_file "$ROOT_DIR/schemas/root_bundle.schema.json")
ROOT_MANIFEST_SCHEMA_HASH=$(sha256_file "$ROOT_DIR/schemas/root_manifest.schema.json")
RUN_EVENT_SCHEMA_HASH=$(sha256_file "$ROOT_DIR/schemas/run_event.schema.json")
SANCTUARY_SIGNAL_SCHEMA_HASH=$(sha256_file "$ROOT_DIR/schemas/sanctuary_signal.schema.json")
STATE_PRESERVATION_SCHEMA_HASH=$(sha256_file "$ROOT_DIR/schemas/state_preservation_manifest.schema.json")
TEMPORAL_ENVELOPE_SCHEMA_HASH=$(sha256_file "$ROOT_DIR/schemas/temporal_envelope.schema.json")
ROOT_POLICY_PACK_HASH=$(
  cd "$ROOT_DIR"
  find policy -type f | LC_ALL=C sort | while IFS= read -r file; do
    printf '%s  %s\n' "$(sha256_file "$file")" "$file"
  done | sha256_stdin
)
TEST_HASH=$(sha256_file "$TEST_OUTPUT")
TEST_COMMAND_JSON=$(printf '%s' "$TEST_COMMAND" | json_escape)
GENERATED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

cat > "$TEST_RESULT_JSON" <<EOF
{
  "schema_version": "test_result.v1",
  "status": "passed",
  "command": "$TEST_COMMAND_JSON",
  "output_hash": "$TEST_HASH",
  "output_path": "dist/test-output.txt"
}
EOF

cat > "$MANIFEST" <<EOF
{
  "schema_version": "release_manifest.v1",
  "VERSION": "$VERSION",
  "version": "$VERSION",
  "generated_at": "$GENERATED_AT",
  "bundle": "$BUNDLE_NAME",
  "source_hash": "$SOURCE_HASH",
  "schema_hashes": {
    "schemas/audit_event.schema.json": "$AUDIT_EVENT_SCHEMA_HASH",
    "schemas/autonomy_envelope.schema.json": "$AUTONOMY_ENVELOPE_SCHEMA_HASH",
    "schemas/boundary_event.schema.json": "$BOUNDARY_EVENT_SCHEMA_HASH",
    "schemas/causal_envelope.schema.json": "$CAUSAL_ENVELOPE_SCHEMA_HASH",
    "schemas/dignity_manifest.schema.json": "$DIGNITY_MANIFEST_SCHEMA_HASH",
    "schemas/humanitas_attestation.schema.json": "$HUMANITAS_ATTESTATION_SCHEMA_HASH",
    "schemas/humanitas_manifest.schema.json": "$HUMANITAS_MANIFEST_SCHEMA_HASH",
    "schemas/root_bundle.schema.json": "$ROOT_BUNDLE_SCHEMA_HASH",
    "schemas/root_manifest.schema.json": "$ROOT_MANIFEST_SCHEMA_HASH",
    "schemas/run_event.schema.json": "$RUN_EVENT_SCHEMA_HASH",
    "schemas/sanctuary_signal.schema.json": "$SANCTUARY_SIGNAL_SCHEMA_HASH",
    "schemas/state_preservation_manifest.schema.json": "$STATE_PRESERVATION_SCHEMA_HASH",
    "schemas/temporal_envelope.schema.json": "$TEMPORAL_ENVELOPE_SCHEMA_HASH"
  },
  "root_policy_pack_hash": "$ROOT_POLICY_PACK_HASH",
  "test_result": {
    "status": "passed",
    "command": "$TEST_COMMAND_JSON",
    "output_hash": "$TEST_HASH",
    "path": "dist/test-result.json"
  },
  "no_telemetry": true,
  "no_auto_update": true,
  "no_remote_kill_switch": true
}
EOF

(
  cd "$ROOT_DIR"
  tar -czf "$BUNDLE" \
    AGENTS.md \
    README.md \
    VERSION \
    dignity-sentinel \
    docs \
    policy \
    schemas \
    scripts \
    src \
    tests
)

BUNDLE_HASH=$(sha256_file "$BUNDLE")
MANIFEST_HASH=$(sha256_file "$MANIFEST")
TEST_RESULT_HASH=$(sha256_file "$TEST_RESULT_JSON")

printf '%s  %s\n' "$BUNDLE_HASH" "$BUNDLE_NAME" > "$BUNDLE_CHECKSUM"
{
  printf '%s  %s\n' "$BUNDLE_HASH" "$BUNDLE_NAME"
  printf '%s  release-manifest.json\n' "$MANIFEST_HASH"
  printf '%s  test-result.json\n' "$TEST_RESULT_HASH"
} > "$CHECKSUMS_FILE"

echo "Built release bundle: $BUNDLE"
echo "Bundle checksum: $BUNDLE_CHECKSUM"
echo "Release manifest: $MANIFEST"
