#!/usr/bin/env python
"""Bắt lỗi enum sai tên bằng AST (vd ReviewStatus.NEEDS_REVISION). Thoát mã 1 nếu có lỗi."""
import ast, sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", "__pycache__", "migrations", "venv", ".venv", "staticfiles", "node_modules"}
BUILTIN = {"choices", "values", "labels", "names", "label", "value", "name",
           "__members__", "__class__", "__doc__", "__name__", "__module__"}

def py_files():
    for p in ROOT.rglob("*.py"):
        if not (set(p.relative_to(ROOT).parts) & SKIP):
            yield p

def is_choices_class(node):
    for b in node.bases:
        name = b.attr if isinstance(b, ast.Attribute) else getattr(b, "id", "")
        if name in {"TextChoices", "IntegerChoices", "Choices"}:
            return True
    return False

def collect(trees):
    enums = {}
    for tree in trees.values():
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and is_choices_class(node):
                members = {t.id for s in node.body if isinstance(s, ast.Assign)
                           for t in s.targets if isinstance(t, ast.Name)}
                enums.setdefault(node.name, set()).update(members)
    return enums

def main():
    trees = {}
    for p in py_files():
        try:
            trees[p] = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except SyntaxError as e:
            print(f"{p.relative_to(ROOT)}:{e.lineno}: SyntaxError"); return 1
    enums = collect(trees)
    errors = []
    for p, tree in trees.items():
        for n in ast.walk(tree):
            if (isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                    and n.value.id in enums and n.attr not in BUILTIN
                    and n.attr not in enums[n.value.id]):
                errors.append(f"{p.relative_to(ROOT)}:{n.lineno}: {n.value.id}.{n.attr} không tồn tại "
                              f"(có: {', '.join(sorted(enums[n.value.id]))})")
    print("\n".join(errors) if errors else f"OK — {len(enums)} enum, 0 lỗi")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
