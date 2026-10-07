# BÁO CÁO TỔNG KẾT DỰ ÁN VÒNG 3 — PROJECTHUB AI (VAU)

## 1. TỔNG QUAN HỆ THỐNG & KẾT QUẢ VÒNG 3
Báo cáo này tổng hợp kết quả thực hiện Đợt Refactoring & Verification Vòng 3 cho dự án **ProjectHub AI (Học viện Hàng không Việt Nam - VAU)** trên nhánh `fix/vong-3`.

- **Mục tiêu chính**: Khắc phục triệt để 20/20 lỗi P0, 15/15 lỗ hổng bảo mật, chuẩn hóa Ma trận phân quyền ma trận độc quyền `can()`, xây dựng Động cơ AI Thuần Python 4 chức năng gắn chặt vào DB PostgreSQL, chuẩn hóa State Machine nhiệm vụ & dự án, tích hợp Hệ thống Thông báo thời gian thực và Seed dữ liệu mẫu với hình ảnh & tài liệu chuẩn.
- **Trạng thái**:
  - `python manage.py check`: **0 lỗi**
  - `python manage.py makemigrations --check`: **No changes detected**
  - `python scripts/lint_enums.py`: **OK — 20 enum, 0 lỗi**
  - `python manage.py test`: **31/31 unit tests PASS** (100% xanh)

---

## 2. CHI TIẾT SỬA LỖI P0 (20/20 LỖI)

| # | Lỗi P0 | Vị trí | Giải pháp đã triển khai | Trạng thái |
|---|---|---|---|---|
| 1 | Sập `ReviewStatus.NEED_REVISION` | `reviews/views.py` | Import đúng enum `ReviewStatus.CHANGES_REQUESTED` | PASS |
| 2 | Sập `Task.checklist_progress` | `tasks/models.py`, `templates/tasks/task_card.html` | Thêm `@property checklist_progress` tính tỉ lệ checklist | PASS |
| 3 | Sập `strftime` trên `str` datetime | `ai_assistant/context.py` | Chuyển đổi timestamp an toàn với `parse_datetime` trước khi gọi `strftime` | PASS |
| 4 | Trống lịch do thiếu `JsonResponse` | `milestones/views.py`, `projects/views.py` | Import đầy đủ `JsonResponse` và bọc dữ liệu sự kiện chuẩn JSON | PASS |
| 5 | Thiếu `import timezone`, `TimeLog` | `dashboard/views.py` | Import `timezone` và `TimeLog`, khắc phục 500 xuất PDF/biểu đồ | PASS |
| 6 | Thất bại preview tài liệu 500 | `documents/views.py` | Kiểm tra Magic bytes file PDF/PNG, xử lý `FileNotFoundError` với HTTP 410 | PASS |
| 7 | Thiếu nút Sửa/Xóa Task trên UI | `templates/tasks/` | Bổ sung Modal Popup Sửa/Xóa Task, kết nối với API `/tasks/<id>/edit/` & `/delete/` | PASS |
| 8 | Lỗ hổng Backdoor đăng nhập | `accounts/views.py` | Loại bỏ hoàn toàn `fallback_map` khôi phục mật khẩu backdoor | PASS |
| 9 | Mismatch Enum `FileCategory` | `documents/views.py` | Đồng bộ enum `FileCategory` giữa backend & template (`WORD`, `EXCEL`, `POWERPOINT`, `ZIP`, `IMAGE`, `CODE`, `PDF`) | PASS |
| 10| Trống dữ liệu biểu đồ Dashboard | `dashboard/views.py` | Kết nối ORM PostgreSQL thật tính tỉ lệ hoàn thành nhiệm vụ & biểu đồ | PASS |
| 11| Lỗi Timer Time Tracker khi Logout | `accounts/views.py`, `dashboard/views.py` | Tự động chốt log thời gian đang chạy khi User đăng xuất | PASS |
| 12| AI bịa đặt dữ liệu (Hallucination) | `ai_assistant/engine/` | Lọc ID giả bằng Pydantic & Facts Builder, fallback sang 9 Quy tắc R1-R9 khi mất API | PASS |
| 13| Mentor/Admin xem UI AI | `templates/ai_assistant/` | Chỉ cho phép Mentor/Admin xem đề xuất AI sau khi Sinh viên đã khởi tạo | PASS |
| 14| Chat nhóm sai context dự án | `projects/views.py` | Ràng buộc room chat theo `project_id` của đồ án đang chọn | PASS |
| 15| Lỗi Avatar mất file 500 | `accounts/views.py` | Bọc try-except `FileNotFoundError` trả về avatar mặc định SVG | PASS |
| 16| Sai đường dẫn Breadcrumbs | `core/context_processors.py` | Chuẩn hóa Context Processor Breadcrumb theo cấp (Trang chủ -> Bảng điều khiển -> Đồ án) | PASS |
| 17| Sai tên vai trò Admin | Base Templates | Đổi "Admin Hàng không" thành "Quản trị viên HVHK" toàn bộ hệ thống | PASS |
| 18| Thêm chức danh Mentor | `accounts/models.py`, Templates | Thêm trường `academic_title` (ThS.NCS., TS.) hiển thị kèm họ tên Mentor | PASS |
| 19| Danh sách Sinh viên VAU | `seed_demo.py` | Seed đúng 5 sinh viên VAU (Lê Ngọc Trinh nhóm trưởng) & 3 Giảng viên Mentor | PASS |
| 20| Loại bỏ thông báo/sự kiện cũ | Database | Xóa toàn bộ dữ liệu mock cũ, kết nối Notification & Calendar thật | PASS |

---

## 3. ĐỘNG CƠ PHÂN QUYỀN ĐỒNG NHẤT (`projects/permissions.py`)

Hệ thống phân quyền được tái cấu trúc thành một **Single Source of Truth** sử dụng hàm `can(user, action, target_obj)`:

```python
# Kiểm tra quyền tác vụ
can(user, 'task.create', project)
can(user, 'project.edit', project)
can(user, 'document.upload', project)
```

### Bảng Ma trận Phân quyền (Permission Matrix):
- **Admin**: Quyền Quản trị viên HVHK tối cao (xem tất cả đồ án, quản lý tài khoản, cấu hình hệ thống, duyệt tiến độ). KHÔNG tham gia nộp tài liệu cá nhân của sinh viên.
- **Mentor (Giảng viên)**: Theo dõi tiến độ các đồ án được phân công hướng dẫn, duyệt Task (REVIEW -> DONE), đánh giá cột mốc, xem kết quả AI phân tích.
- **Student Leader (Nhóm trưởng)**: Quản lý thành viên nhóm, tạo/sửa/xóa/phân công Task, tải tài liệu đồ án, sử dụng 4 tính năng AI.
- **Student Member (Thành viên)**: Cập nhật trạng thái Task (TODO <-> IN_PROGRESS -> REVIEW), tải tài liệu, bình luận, điểm danh Time Tracker.

---

## 4. ĐỘNG CƠ AI THUẦN PYTHON & QUY TẮC R1–R9 (`ai_assistant/engine/`)

- **Kiến trúc**:
  - `facts_builder.py`: Tổng hợp dữ liệu thực tế (Facts) từ DB PostgreSQL thành context ngắn gọn.
  - `llm.py`: Tích hợp Google Gemini via `x-goog-api-key`, OpenAI & Anthropic qua REST API thuần (không phụ thuộc SDK cồng kềnh).
  - `parse.py` & `schemas.py`: Validate kết quả trả về bằng Pydantic v2, loại bỏ ID bịa đặt.
  - `rules.py`: Tự động tính toán 9 chỉ số rủi ro cứng (R1-R9) khi API LLM hết key hoặc mất kết nối:
    - **R1**: Task trễ hạn (Overdue Task)
    - **R2**: Task kẹt ở In Progress > 5 ngày
    - **R3**: Milestone sắp hạn nhưng tiến độ < 50%
    - **R4**: Đồ án không có hoạt động trong 7 ngày
    - **R5**: Thành viên bị dồn quá 4 task cùng lúc
    - **R6**: Đồ án thiếu tài liệu SRS / Báo cáo
    - **R7**: Tỉ lệ hoàn thành đồ án chậm hơn thời gian đã trôi qua
    - **R8**: Chưa có phản hồi/đánh giá từ Mentor > 14 ngày
    - **R9**: Không có log bấm giờ Time Tracker trong 3 ngày

- **4 Chức năng AI chính**:
  1. **Chia nhỏ yêu cầu (Task Breakdown)**: Đề xuất task nhỏ kèm ưu tiên & ước lượng.
  2. **Tóm tắt tuần (Weekly Summary)**: Tổng hợp task hoàn thành, giờ làm, thảo luận trong 7 ngày.
  3. **Phân tích Rủi ro Task kẹt (Risk Analysis)**: Nhận diện điểm nghẽn & đề xuất khắc phục.
  4. **Gợi ý Câu hỏi cho Mentor (Mentor Questions)**: Tạo 5-7 câu hỏi trọng tâm cho buổi làm việc.

---

## 5. BỘ DATASET MẪU HỌC VIỆN HÀNG KHÔNG (`seed_demo.py`)

Chạy lệnh `python manage.py seed_demo --reset` để tái tạo toàn bộ dữ liệu thật:
- **5 Sinh viên chuẩn**:
  1. **Lê Ngọc Trinh** (Nhóm trưởng) — MSSV: 2431540114 — Lớp: 24ĐHTT02
  2. **Nguyễn Doãn Ngọc Hân** — MSSV: 2431540093 — Lớp: 24ĐHTT02
  3. **Phạm Thị Thanh Trúc** — MSSV: 2431540102 — Lớp: 24ĐHTT02
  4. **Trần Đàm Gia Nghi** — MSSV: 2431540080 — Lớp: 24ĐHTT02
  5. **Nguyễn Lâm Huyền Tuyết** — MSSV: 2431540137 — Lớp: 24ĐHTT03
- **3 Giảng viên Mentor**:
  1. **ThS.NCS. Nguyễn Thanh Hiếu** (Trưởng bộ môn)
  2. **TS. Nguyễn Lương Anh Tuấn**
  3. **TS. Trần Hoàng Lộc**
- **1 Quản trị viên**: **Quản trị viên HVHK** (admin / password)
- **6 Đồ án mẫu**: `PRJ-2026-AI`, `AVIA`, `DRONE`, `CARGO`, `RESERVE`, `SAFETY`
- File tài liệu PDF 1 trang thật & ảnh đại diện được khởi tạo chuẩn xác trong `media/`.

---

## 6. KIỂM THỬ SUITE (& INTEGRATION TESTS)

Bộ kiểm thử tự động gồm 31 unit test bao phủ toàn bộ luồng nghiệp vụ quan trọng:
- `test_permission_matrix.py`: Kiểm tra ma trận phân quyền 4 vai trò.
- `test_regressions_vong3.py`: Kiểm tra 20 lỗi P0 đã được khắc phục.
- `test_ai.py`: Kiểm tra Facts Builder, Pydantic Schema Validation & Rules Engine fallback.

**Kết quả chạy test (`python manage.py test`)**:
```
Ran 31 tests in 97.247s
OK
```

---
*Báo cáo được khởi tạo tự động sau khi hoàn thành Phase Vòng 3 trên nhánh `fix/vong-3`.*
