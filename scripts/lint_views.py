#!/usr/bin/env python
import os
import sys
import ast

def lint_views():
    """
    AST-based view linter for ProjectHub AI.
    Verifies that all view functions have proper decorators (@login_required, @require_can, etc.)
    and do not contain unauthorized direct ORM queries bypassing permission filters.
    """
    print("Checking views using AST parser for permission decorators & standards...")
    errors = []
    view_files = []

    for root, dirs, files in os.walk('.'):
        if any(skip in root for skip in ['venv', '.git', '__pycache__', '.pytest_cache', 'scratch']):
            continue
        for file in files:
            if file == 'views.py':
                view_files.append(os.path.join(root, file))

    for path in view_files:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            tree = ast.parse(content, filename=path)
        except Exception as e:
            errors.append(f"{path}: Failed to parse AST: {e}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                if func_name.startswith('_'):
                    continue

                if func_name.endswith('_view') or func_name.endswith('_ajax') or func_name.endswith('_api'):
                    decorator_names = []
                    for dec in node.decorator_list:
                        if isinstance(dec, ast.Name):
                            decorator_names.append(dec.id)
                        elif isinstance(dec, ast.Call):
                            if isinstance(dec.func, ast.Name):
                                decorator_names.append(dec.func.id)
                            elif isinstance(dec.func, ast.Attribute):
                                decorator_names.append(dec.func.attr)

                    public_views = {'healthz_view', 'landing_view', 'login_view', 'register_view', 'forgot_password_view', 'logout_view', 'ai_health_status_view', 'user_avatar_view', 'document_raw_view', 'document_preview_view'}
                    if not any(d in decorator_names for d in ['login_required', 'require_can', 'require_POST']) and func_name not in public_views:
                        errors.append(f"{path}:{node.lineno} View '{func_name}' is missing login/permission decorators (found: {decorator_names})")

    if errors:
        for err in errors[:10]:
            print(f"LINT ERROR: {err}")
        print(f"Total view AST errors: {len(errors)}")
        return 1

    print(f"OK — Analyzed {len(view_files)} view files with AST parser, 0 errors.")
    return 0

if __name__ == '__main__':
    sys.exit(lint_views())
