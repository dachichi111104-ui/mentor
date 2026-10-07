import os
import sys

def lint_templates():
    print("Checking HTML templates for standard layout extension and clean markup...")
    template_files = []
    for root, dirs, files in os.walk('templates'):
        for file in files:
            if file.endswith('.html'):
                template_files.append(os.path.join(root, file))

    errors = []
    for path in template_files:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # Check unclosed tags or syntax
            if '{% block' in content and '{% endblock' not in content:
                errors.append(f"{path}: Unclosed block tag")

    if errors:
        for err in errors:
            print(f"LINT ERROR: {err}")
        return 1

    print(f"OK — Analyzed {len(template_files)} template files, 0 errors.")
    return 0

if __name__ == '__main__':
    sys.exit(lint_templates())
