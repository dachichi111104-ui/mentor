#!/usr/bin/env python
import os
import sys
import re

def lint_templates():
    """
    Template linter for ProjectHub AI.
    Checks templates for raw innerHTML assignments, raw window.confirm calls,
    and missing breadcrumb blocks.
    """
    print("Checking templates for innerHTML, confirm, and breadcrumb standards...")
    errors = []
    template_files = []

    for root, dirs, files in os.walk('templates'):
        if any(skip in root for skip in ['venv', '.git', '__pycache__']):
            continue
        for file in files:
            if file.endswith('.html'):
                template_files.append(os.path.join(root, file))

    for path in template_files:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Check raw innerHTML assignments (XSS SEC-9)
        if re.search(r'innerHTML\s*=', content):
            errors.append(f"{path}: Contains unsafe innerHTML assignment.")

        # Check raw confirm/alert/prompt (exclude UI helper functions or modal calls)
        if re.search(r'\b(window\.confirm|window\.alert|window\.prompt)\s*\(', content):
            errors.append(f"{path}: Uses raw browser confirm/alert/prompt instead of modal UI component.")

        # Check breadcrumb inclusion on detail pages
        if '_detail.html' in path and 'breadcrumb' not in content.lower() and '_breadcrumb' not in content:
            errors.append(f"{path}: Detail page missing breadcrumb block navigation.")

    if errors:
        for err in errors[:10]:
            print(f"LINT ERROR: {err}")
        print(f"Total template errors: {len(errors)}")
        return 1

    print(f"OK — Analyzed {len(template_files)} HTML templates, 0 errors.")
    return 0

if __name__ == '__main__':
    sys.exit(lint_templates())
