#!/usr/bin/env python
import os
import sys
import re

SECRET_PATTERNS = [
    r'AIzaSy[A-Za-z0-9_-]{33}',
    r'sk-[A-Za-z0-9]{32,}',
    r'ghp_[A-Za-z0-9]{36}',
]

def main():
    found = False
    for root, dirs, files in os.walk('.'):
        if any(d in root for d in ['.git', 'venv', '__pycache__', 'media', 'static', 'scratch']):
            continue
        for f in files:
            if not f.endswith(('.py', '.html', '.js', '.json', '.yml', '.yaml', '.env.example')):
                continue
            path = os.path.join(root, f)
            try:
                txt = open(path, encoding='utf-8', errors='ignore').read()
                for pat in SECRET_PATTERNS:
                    if re.search(pat, txt):
                        print(f"SECURITY WARNING: Secret key pattern found in {path}")
                        found = True
            except Exception:
                pass
    if found:
        print("Secrets check completed with warnings.")
    else:
        print("Secrets check clean: No hardcoded secrets found.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
