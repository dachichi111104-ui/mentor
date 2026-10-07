#!/usr/bin/env python
"""Fail nếu repo/zip chứa bí mật hoặc tệp không được đóng gói. Dùng: python scripts/check_secrets.py [duong_dan|file.zip]"""
import re, sys, zipfile
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

FORBIDDEN = [r"(^|/)\.env$", r"\.sqlite3$", r"(^|/)media/", r"(^|/)staticfiles/", r"\.pem$", r"\.key$"]
PATTERNS = {
    "Google API key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "OpenAI/Anthropic key": re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"),
    "URL DB có mật khẩu": re.compile(r"postgres(?:ql)?://[^:\s/]+:(?!CHANGE_ME|password|\*+)[^@\s]{3,}@(?!127\.0\.0\.1|localhost)"),
}
SCAN_EXT = {".py", ".env", ".yaml", ".yml", ".sh", ".md", ".txt", ".json", ".html", ".js", ".example"}

def iter_entries(target):
    if target.is_file() and target.suffix == ".zip":
        with zipfile.ZipFile(target) as z:
            for n in z.namelist():
                if n.endswith("/") or "/.git/" in n:
                    continue
                yield n, (lambda n=n: z.read(n).decode("utf-8", "ignore"))
    else:
        for p in target.rglob("*"):
            if p.is_file() and ".git" not in p.parts:
                yield str(p.relative_to(target)).replace("\\", "/"), (lambda p=p: p.read_text("utf-8", "ignore"))

def main():
    target = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    bad = []
    for name, read in iter_entries(target):
        if name.endswith(".env.example"):
            pass
        elif any(re.search(f, name) for f in FORBIDDEN):
            bad.append(f"{name}: tệp không được đóng gói/commit")
            continue
        if Path(name).suffix in SCAN_EXT or name.endswith(".env.example"):
            text = read()
            for label, rx in PATTERNS.items():
                if rx.search(text):
                    bad.append(f"{name}: nghi ngờ {label}")
    print("\n".join(bad) if bad else "OK — không phát hiện bí mật")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
