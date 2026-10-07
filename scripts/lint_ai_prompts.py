#!/usr/bin/env python
import os
import sys
import re

def lint_ai_prompts():
    """
    AI Prompts and Engine Linter for ProjectHub AI.
    Verifies that no legacy pollinations provider API endpoints, hardcoded URL query parameters,
    or silent 'except: pass' exception handlers exist in AI assistant modules.
    """
    print("Checking AI modules for forbidden providers, URL keys, and except: pass standards...")
    errors = []
    ai_files = []

    bad_provider = 'pollinations'
    bad_key_param = '?' + 'key='

    for root, dirs, files in os.walk('ai_assistant'):
        if any(skip in root for skip in ['venv', '.git', '__pycache__']):
            continue
        for file in files:
            if file.endswith('.py'):
                ai_files.append(os.path.join(root, file))

    for path in ai_files:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        if bad_provider in content.lower():
            errors.append(f"{path}: Contains forbidden provider reference.")

        if bad_key_param in content:
            errors.append(f"{path}: Contains forbidden URL query parameter (SEC-10 violation). Pass API keys via headers instead.")

        if re.search(r'except[^\n]*:\s*\n\s*pass\b', content):
            errors.append(f"{path}: Contains silent 'except: pass' handler violating logging guidelines.")

    if errors:
        for err in errors[:10]:
            print(f"LINT ERROR: {err}")
        print(f"Total AI lint errors: {len(errors)}")
        return 1

    print(f"OK — Analyzed {len(ai_files)} AI Python files, 0 errors.")
    return 0

if __name__ == '__main__':
    sys.exit(lint_ai_prompts())
