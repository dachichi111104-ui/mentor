import os
import sys

def dump_matrix():
    print("Dumping PERMISSION_MATRIX configuration...")
    sys.path.insert(0, '.')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projecthub_config.settings')
    import django
    django.setup()

    from projects.permissions import PERMISSION_MATRIX
    print(f"Total permissions mapped: {len(PERMISSION_MATRIX)}")
    for perm, roles in sorted(PERMISSION_MATRIX.items()):
        print(f"  - {perm}: {', '.join(roles)}")

    return 0

if __name__ == '__main__':
    sys.exit(dump_matrix())
