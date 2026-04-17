#!/bin/bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <tprwow_folder> <output_file>" >&2
  exit 1
fi

BASE_DIR="$1"
OUTPUT_FILE="$2"
PREFIX="tpr/wow"

echo -e "path\tsize\tmd5" > "$OUTPUT_FILE"

export BASE_DIR PREFIX OUTPUT_FILE

echo "Counting files..."
TOTAL=$(find "$BASE_DIR/config" "$BASE_DIR/data" "$BASE_DIR/patch" -type f | wc -l)
echo "Total files: $TOTAL"

COUNTER_FILE=$(mktemp)
echo 0 > "$COUNTER_FILE"

progress() {
  while true; do
    done=$(cat "$COUNTER_FILE")
    percent=$(( done * 100 / TOTAL ))

    width=40
    filled=$(( percent * width / 100 ))
    empty=$(( width - filled ))

    bar=$(printf "%${filled}s" | tr ' ' '#')
    space=$(printf "%${empty}s")

    printf "\r[%s%s] %d%% (%d/%d)" "$bar" "$space" "$percent" "$done" "$TOTAL"

    sleep 0.2
  done
}

progress &
PROGRESS_PID=$!

export COUNTER_FILE TOTAL

find "$BASE_DIR/config" "$BASE_DIR/data" "$BASE_DIR/patch" -type f -print0 |
xargs -0 -n1 -P"$(nproc)" bash -c '
  file="$1"

  relpath=${file#"$BASE_DIR"/}
  fname=${relpath##*/}
  dirpath=${relpath%/*}
  fileprefix=${fname:0:2}/${fname:2:2}

  size=$(stat -c %s -- "$file")
  md5=$(openssl md5 -r "$file"); md5=${md5%% *}

  printf "%s\t%s\t%s\n" "$PREFIX/$dirpath/$fileprefix/$fname" "$size" "$md5" >> "$OUTPUT_FILE"

  # atomic increment
  (
    flock 200
    count=$(<"$COUNTER_FILE")
    echo $((count + 1)) > "$COUNTER_FILE"
  ) 200>"$COUNTER_FILE.lock"
' _

kill "$PROGRESS_PID"
wait "$PROGRESS_PID" 2>/dev/null || true

rm -f "$COUNTER_FILE" "$COUNTER_FILE.lock"

echo -e "\nDone."
