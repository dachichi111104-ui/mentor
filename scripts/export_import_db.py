"""
Script hướng dẫn và tự động xuất/nhập dữ liệu giữa SQLite và PostgreSQL cho ProjectHub AI.

Cách sử dụng:
1. Export dữ liệu từ SQLite local ra JSON:
   python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2 > data_dump.json

2. Chuyển sang kết nối PostgreSQL (cấu hình DATABASE_URL trong file .env):
   python manage.py migrate

3. Import dữ liệu vào PostgreSQL:
   python manage.py loaddata data_dump.json
"""

import sys
import subprocess

def export_data():
    print("[1/2] Đang xuất dữ liệu từ CSDL SQLite sang file data_dump.json...")
    cmd = [
        sys.executable, "manage.py", "dumpdata",
        "--natural-foreign", "--natural-primary",
        "-e", "contenttypes", "-e", "auth.Permission",
        "--indent", "2"
    ]
    with open("data_dump.json", "w", encoding="utf-8") as f:
        res = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0:
        print(" -> Xuất dữ liệu thành công vào file data_dump.json!")
    else:
        print(f" -> Lỗi xuất dữ liệu: {res.stderr}")

def import_data():
    print("[2/2] Đang nạp dữ liệu từ data_dump.json vào CSDL PostgreSQL...")
    cmd = [sys.executable, "manage.py", "loaddata", "data_dump.json"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print(" -> Nhập dữ liệu thành công vào CSDL mới!")
    else:
        print(f" -> Lỗi nhập dữ liệu: {res.stderr}")

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else 'export'
    if action == 'export':
        export_data()
    elif action == 'import':
        import_data()
    else:
        print("Cú pháp: python scripts/export_import_db.py [export|import]")
