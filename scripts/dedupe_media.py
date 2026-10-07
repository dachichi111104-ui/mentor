#!/usr/bin/env python
import os
import sys
import hashlib
from collections import defaultdict

def main():
    media_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'media')
    if not os.path.exists(media_dir):
        print("Media directory does not exist.")
        return 0

    hashes = defaultdict(list)
    for root, dirs, files in os.walk(media_dir):
        for f in files:
            path = os.path.join(root, f)
            try:
                with open(path, 'rb') as fp:
                    h = hashlib.sha256(fp.read()).hexdigest()
                hashes[h].append(path)
            except Exception as e:
                print(f"Error reading {path}: {e}")

    duplicates_found = 0
    removed_count = 0
    for h, path_list in hashes.items():
        if len(path_list) > 1:
            duplicates_found += 1
            print(f"Duplicate hash {h[:12]}: {len(path_list)} files")
            # Keep first file, remove rest if clean parameter set
            keep = path_list[0]
            print(f"  Keeping: {keep}")
            for extra in path_list[1:]:
                print(f"  Duplicate: {extra}")

    print(f"\nDone. Found {duplicates_found} sets of duplicate files.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
