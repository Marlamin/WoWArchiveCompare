#!/bin/bash
set -euo pipefail

if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <source_manifest> <remote_manifest_url> <remote_name> <output_folder>" >&2
  exit 1
fi

SOURCE_MANIFEST="$1"
REMOTE_MANIFEST_URL="$2"
REMOTE_NAME="$3"
OUTPUT_FOLDER="$4"

TOOL_BIN="WoWArchiveCompare"
TOOL_URL="https://github.com/Marlamin/WoWArchiveCompare/releases/latest/download/Release-linux-x64.zip"

# Check if the tool is available
if ! command -v "$TOOL_BIN" &> /dev/null; then
  echo "Downloading $TOOL_BIN from $TOOL_URL..."
  curl -L -o "$TOOL_BIN.zip" "$TOOL_URL"
  unzip "$TOOL_BIN.zip" -d .
  rm "$TOOL_BIN.zip"
fi

# Download source manifest
echo "Downloading manifest from $REMOTE_MANIFEST_URL..."
curl -L -o "$REMOTE_NAME.tsv" "$REMOTE_MANIFEST_URL"

# Run the comparison
echo "Comparing $REMOTE_NAME.tsv with local manifest..."
"$TOOL_BIN" "$SOURCE_MANIFEST" "$REMOTE_NAME.tsv" "$REMOTE_NAME" "$OUTPUT_FOLDER"
