#!/usr/bin/env python3
import hashlib
import os
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from tqdm import tqdm

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <tprwow_folder> <output_file>", file=sys.stderr)
    sys.exit(1)

BASE_DIR = sys.argv[1]
OUTPUT_FILE = sys.argv[2]
CACHE_FILE = OUTPUT_FILE + ".cache"
PREFIX = "tpr/wow"

TARGET_DIRS = ["config", "data", "patch"]
MAX_WORKERS = 1 # HDD: Use 1, SSD: Use as many threads as you can

STOP_REQUESTED = False

def handle_sigint(signum, frame):
    global STOP_REQUESTED
    STOP_REQUESTED = True
    print("\n!!! Interrupt received, finishing current work and saving...")


signal.signal(signal.SIGINT, handle_sigint)

def load_cache():
    cache = {}
    if not os.path.exists(CACHE_FILE):
        return cache

    with open(CACHE_FILE, "r") as f:
        for line in f:
            path, mtime = line.strip().split("\t")
            cache[path] = int(mtime)
    return cache


def load_output():
    data = {}
    if not os.path.exists(OUTPUT_FILE):
        return data

    with open(OUTPUT_FILE, "r") as f:
        next(f, None) # Skip header
        for line in f:
            path, size, md5 = line.strip().split("\t")
            data[path] = (int(size), md5)
    return data

def save_outputs(results, new_cache):
    print("\nSaving progress...")

    with open(OUTPUT_FILE, "w", buffering=1024 * 1024) as out:
        out.write("path\tsize\tmd5\n")
        for line in results.values():
            out.write(line)

    with open(CACHE_FILE, "w") as c:
        for path, mtime in new_cache.items():
            c.write(f"{path}\t{mtime}\n")

    print("Progress saved.")

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

def process_file(file_path, cache, old_data):
    try:
        relpath = os.path.relpath(file_path, BASE_DIR)
        fname = os.path.basename(relpath)
        dirpath = os.path.dirname(relpath)

        fileprefix = f"{fname[0:2]}/{fname[2:4]}"
        out_path = f"{PREFIX}/{dirpath}/{fileprefix}/{fname}"

        mtime = os.stat(file_path).st_mtime_ns

        # File hasn't changed, use the cached MD5
        if relpath in cache and cache[relpath] == mtime:
            if out_path in old_data:
                size, md5 = old_data[out_path]
                return relpath, mtime, f"{out_path}\t{size}\t{md5}\n"

        md5, size = file_stats(file_path)
        return relpath, mtime, f"{out_path}\t{size}\t{md5}\n"

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

    print("Loading cache...")
    cache = load_cache()

    print("Loading previous output...")
    old_data = load_output()

    start_time = time.time()
    new_cache = {}
    results = {}

    try:
       with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = set()
            file_iter = collect_files()

            for _ in range(MAX_WORKERS * 2):
                try:
                    path = next(file_iter)
                    futures.add(executor.submit(process_file, path, cache, old_data))
                except StopIteration:
                    break

            with tqdm(total=total_files, unit="files") as pbar:
                while futures:
                    done, futures = wait(futures, return_when=FIRST_COMPLETED)

                    for future in done:
                        if STOP_REQUESTED:
                            futures.clear()
                            break

                        result = future.result()
                        if result:
                            relpath, mtime, line = result
                            new_cache[relpath] = mtime
                            out_path = line.split("\t", 1)[0]
                            results[out_path] = line

                        pbar.update(1)

                        if not STOP_REQUESTED:
                            try:
                                path = next(file_iter)
                                futures.add(executor.submit(process_file, path, cache, old_data))
                            except StopIteration:
                                pass

                    if STOP_REQUESTED:
                        break
    except KeyboardInterrupt:
        pass

    save_outputs(results, new_cache)

    elapsed = time.time() - start_time
    print(f"\nDone in {elapsed:.1f}s")

if __name__ == "__main__":
    main()
