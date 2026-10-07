# ProjectHub AI - Nền tảng Quản lý Đồ án & NCKH Hàng không

Nền tảng quản lý đồ án thông minh cho Học viện Hàng không Việt Nam (VAU) tích hợp Trợ lý AI Assistant Học thuật, phát hiện rủi ro trễ hạn, ma trận phân quyền RBAC tập trung và dịch vụ AI phụ trợ FastAPI.

---

## 🚀 Tính năng Cốt lõi

1. **Quản lý Đồ án & Kanban Board**:
   - Quản lý vòng đời đồ án (Lên kế hoạch, Đang thực hiện, Đang đánh giá, Hoàn thành, Lưu trữ).
   - Bảng Kanban kéo thả mượt mà với 4 cột chuẩn: `Cần làm (TODO)`, `Đang làm (IN_PROGRESS)`, `Chờ review (REVIEW)`, `Đã xong (DONE)`.
   - Phân quyền chuyển trạng thái: Sinh viên tự chuyển TODO ↔ IN_PROGRESS ↔ REVIEW; Mentor/Admin/Leader phê duyệt REVIEW → DONE.

2. **Trợ lý AI Assistant Học thuật & FastAPI Service**:
   - **AI Task Breakdown**: Phân rã mô tả đồ án thành danh sách task tiêu chuẩn.
   - **AI Weekly Summary**: Tổng hợp báo cáo tiến độ tuần tự động từ dữ liệu DB.
   - **AI Risk Warning**: Phân tích rủi ro quá hạn và cảnh báo sớm.
   - **AI Mentor Questions**: Gợi ý câu hỏi phản biện chuyên sâu dành cho Giảng viên.
   - **Đề xuất AI (Proposals)**: AI chỉ đề xuất, con người quyết định (Sinh viên gửi đề xuất → Leader/Admin duyệt mới tạo task thật).
   - **Pure Python Engine & Decoupled Architecture**: Hoạt động hoàn toàn qua engine trong Django hoặc kết nối qua FastAPI Microservice (`ai_service`).

3. **Ma trận Phân quyền Concentrated RBAC**:
   - Phân quyền theo vai trò (ADMIN, MENTOR, STUDENT) và vai trò trong đồ án (LEADER, MEMBER, MENTOR).
   - Ma trận `PERMISSION_MATRIX` tập trung bảo vệ 100% các endpoint API và views.

4. **Lịch Tiến độ & Cuộc hẹn**:
   - Giao diện Lịch tháng động bắt đầu từ Thứ Hai (Monday-first grid).
   - Chuyển tháng linh hoạt (`?month=YYYY-MM`), tự động tô sáng ngày hiện tại (`timezone.localdate()`).
   - Đặt lịch hẹn hướng dẫn Mentor và xuất lịch chuẩn `.ics`.

5. **Realtime Notifications & Time Tracker**:
   - Thông báo thời gian thực qua WebSocket với cơ chế dự phòng HTTP Polling 30s.
   - Bộ đếm thời gian Time Tracker theo dõi thời lượng làm việc thực tế của thành viên.

---

## 🛠️ Công nghệ Sử dụng

- **Backend**: Django 5.0 (Python 3.11), PostgreSQL.
- **Frontend**: Tailwind CSS, Alpine.js, FontAwesome 6.
- **Microservice**: FastAPI (Python 3.11), Uvicorn.
- **Realtime & Celery**: Django Channels, Daphne, Celery Beat.

---

## ⚡ Hướng dẫn Cài đặt & Chạy Local

### 1. Khởi tạo Môi trường Python
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Khởi tạo CSDL & Seed Dữ liệu Demo
```bash
python manage.py migrate
SEED_DEMO=1 python manage.py seed_demo
```

### 3. Khởi chạy Hệ thống
- **Chạy Django Web Server**:
  ```bash
  python manage.py runserver 0.0.0.0:8000
  ```
- **Chạy FastAPI AI Microservice (Tùy chọn)**:
  ```bash
  uvicorn ai_service.main:app --host 0.0.0.0 --port 8001
  ```

---

## 🧪 Kiểm thử & Quality Assurance

Hệ thống có bộ test suite bao phủ toàn bộ luồng nghiệp vụ:
```bash
# Kiểm tra hệ thống và linter
python manage.py check
python manage.py makemigrations --check
python scripts/lint_enums.py
python scripts/lint_views.py
python scripts/lint_templates.py
python scripts/lint_ai_prompts.py

# Chạy toàn bộ test suite
python manage.py test
```

---

## 🔒 Biến Môi trường (Environment Variables)

| Biến Môi trường | Mô tả | Mặc định |
|---|---|---|
| `DJANGO_SECRET_KEY` | Secret Key bảo mật của Django | (Bắt buộc sản xuất) |
| `DJANGO_DEBUG` | Chế độ Debug | `True` |
| `DATABASE_URL` | URL kết nối PostgreSQL | `sqlite:///db.sqlite3` (dev) |
| `AI_PROVIDER` | Nhà cung cấp LLM (`gemini`, `openai`, `anthropic`, `none`) | `none` |
| `GEMINI_API_KEY` | API Key cho Google Gemini | `""` |
| `OPENAI_API_KEY` | API Key cho OpenAI | `""` |
| `AI_SERVICE_URL` | URL của FastAPI AI microservice | `http://localhost:8001` |
| `AI_SERVICE_TOKEN` | Token xác thực kết nối giữa Django và FastAPI | `dev-secret-token` |

---
© 2026 Học viện Hàng không Việt Nam (VAU) - ProjectHub AI.
