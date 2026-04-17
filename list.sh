#!/bin/bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <tprwow_folder>" >&2
  exit 1
fi

BASE_DIR="$1"
PREFIX="tpr/wow"

printf "path\tsize\tmd5\n"

export BASE_DIR PREFIX

find "$BASE_DIR/config" "$BASE_DIR/data" "$BASE_DIR/patch" -type f -print0 |
xargs -0 -n1 -P"$(nproc)" bash -c '
  file="$1"
  relpath=${file#"$BASE_DIR"/}
  fname=${relpath##*/}
  dirpath=${relpath%/*}
  size=$(stat -c %s -- "$file")
  md5=$(openssl md5 -r "$file"); md5=${md5%% *}
  printf "%s\t%s\t%s\n" "$PREFIX/$dirpath/$fname" "$size" "$md5"
' _f
