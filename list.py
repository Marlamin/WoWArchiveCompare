#!/usr/bin/env python3
import os
import hashlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from tqdm import tqdm

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <tprwow_folder> <output_file>", file=sys.stderr)
    sys.exit(1)

BASE_DIR = sys.argv[1]
OUTPUT_FILE = sys.argv[2]
PREFIX = "tpr/wow"

TARGET_DIRS = ["config", "data", "patch"]
MAX_WORKERS = 1 # HDD: Use 1, SSD: Use as many threads as you can

def file_stats(path, chunk_size=16 * 1024 * 1024): # 16MB Chunk
    h = hashlib.md5()
    total = 0
    buf = bytearray(chunk_size)
    view = memoryview(buf)

    with open(path, "rb") as f:
        try: # Linux only - Sequential reading
            os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_SEQUENTIAL)
        except AttributeError:
            pass # Not available

        while True:
            n = f.readinto(buf)
            if not n:
                break
            total += n
            h.update(view[:n])

    return h.hexdigest(), total

def process_file(file_path):
    try:
        relpath = os.path.relpath(file_path, BASE_DIR)
        fname = os.path.basename(relpath)
        dirpath = os.path.dirname(relpath)

        fileprefix = f"{fname[0:2]}/{fname[2:4]}"

        md5, size = file_stats(file_path)

        out_path = f"{PREFIX}/{dirpath}/{fileprefix}/{fname}"
        return f"{out_path}\t{size}\t{md5}\n"

    except Exception:
        return None

def collect_files():
    for sub in TARGET_DIRS:
        root = os.path.join(BASE_DIR, sub)
        for dirpath, _, filenames in os.walk(root):
            filenames.sort()
            for name in filenames:
                yield os.path.join(dirpath, name)

def count_files():
    total = 0
    for sub in TARGET_DIRS:
        root = os.path.join(BASE_DIR, sub)
        for _, _, filenames in os.walk(root):
            total += len(filenames)
    return total

def main():
    print("Counting files...")
    total_files = count_files()
    print(f"Total files: {total_files:,}")

    start_time = time.time()

    with open(OUTPUT_FILE, "w", buffering=1024 * 1024) as out:
        out.write("path\tsize\tmd5\n")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            with tqdm(total=total_files, unit="files") as pbar:
                for result in executor.map(process_file, collect_files(), chunksize=1):
                    if result:
                        out.write(result)
                        pbar.update(1)

    elapsed = time.time() - start_time
    print(f"\nDone in {elapsed:.1f}s")

if __name__ == "__main__":
    main()
