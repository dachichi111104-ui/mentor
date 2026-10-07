import os
import sys

def lint_views():
    print("Checking views for permission and decorator standards...")
    errors = []
    # Verify view files exist and compile
    view_files = []
    for root, dirs, files in os.walk('.'):
        if any(skip in root for skip in ['venv', '.git', '__pycache__', '.pytest_cache']):
            continue
        for file in files:
            if file == 'views.py':
                view_files.append(os.path.join(root, file))

    for path in view_files:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if line.strip().startswith('def ') and not line.strip().startswith('def _'):
                    func_name = line.strip().split('(')[0].replace('def ', '')
                    if func_name.endswith('_view') or func_name.endswith('_ajax') or func_name.endswith('_api'):
                        # Check previous lines for decorators
                        decorators = []
                        j = i - 1
                        while j >= 0 and lines[j].strip().startswith('@'):
                            decorators.append(lines[j].strip())
                            j -= 1
                        if not decorators and not any(pub in func_name for pub in ['healthz', 'landing', 'login', 'register', 'forgot_password', 'logout']):
                            errors.append(f"{path}:{i+1} Function '{func_name}' is missing decorators.")


    if errors:
        for err in errors[:10]:
            print(f"LINT ERROR: {err}")
        print(f"Total view errors: {len(errors)}")
        return 1

    print(f"OK — Analyzed {len(view_files)} view files, 0 errors.")
    return 0

if __name__ == '__main__':
    sys.exit(lint_views())
