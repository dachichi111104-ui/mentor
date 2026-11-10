# BÁO CÁO THIẾT KẾ & HIỆN THỰC — TASK 4
## REALTIME COMMENT, NOTIFICATION VÀ CẢNH BÁO TRỄ HẠN
**Hệ thống**: ProjectHub AI — Nền tảng Quản lý Đồ án & NCKH Hàng không (Học viện Hàng không Việt Nam - VAA)  
**Nhánh Git**: `main` / `fix/vong-4`

---

### 1. CƠ CHẾ THÔNG BÁO & BÌNH LUẬN THỜI GIAN THỰC (REALTIME NOTIFICATION & COMMENT)

#### 1.1. Kiến trúc Giao thức & Kết nối (WebSockets + HTTP Polling Fallback)
* **Giao thức Chính (WebSockets via Django Channels)**:
  - Hệ thống sử dụng **Django Channels** kết hợp máy chủ **Daphne (ASGI)** (`projecthub_config/asgi.py`) để duy trì kết nối hai chiều liên tục giữa trình duyệt của người dùng và máy chủ.
  - Mỗi người dùng đăng nhập sẽ tự động tham gia vào một kênh riêng biệt: `user_{user.id}` thông qua `NotificationConsumer`.
  - Hỗ trợ phòng chat đồ án theo nhóm: `chat_project_{project_id}` qua `ProjectChatConsumer` có kiểm tra ma trận phân quyền truy cập (`chat.read`).
* **Cơ chế Dự phòng Thông minh (30s HTTP Polling Fallback - `static/js/realtime.js`)**:
  - Tại tầng Frontend, file `static/js/realtime.js` tự động khởi tạo kết nối `ws://` (hoặc `wss://` trên HTTPS/Render).
  - Nếu kết nối WebSocket gặp sự cố (mạng yếu, firewall, proxy chặn WebSocket), client tự động chuyển mượt sang chế độ **HTTP Long-Polling** định kỳ mỗi **30 giây** gọi tới endpoint `/notifications/unread-count/`.
  - Khi WebSocket kết nối lại thành công, hệ thống tự động giải phóng (clear) interval Polling để tối ưu tài nguyên máy chủ.

#### 1.2. Luồng Phát Thông báo An toàn (`notify()` Service)
* **Đảm bảo tính Toàn vẹn CSDL (Transaction on-commit)**:
  - Hàm dịch vụ tập trung `notify()` (`notifications/services.py`) lưu bản ghi `Notification` vào CSDL PostgreSQL trước.
  - Sử dụng cơ chế `transaction.on_commit(send_ws)`: Sự kiện WebSocket chỉ được phát đi (`channel_layer.group_send`) **sau khi giao dịch CSDL đã commit thành công**, triệt tiêu hoàn toàn lỗi bất đồng bộ (trình duyệt nhận thông báo nhưng bấm vào thì dữ liệu chưa có trong DB).
* **Cơ chế Chống Lặp / Chống Spam (Deduplication)**:
  - Hỗ trợ tham số `dedupe_key` lưu vết trên **Redis Cache** với TTL 24 giờ (`timeout=86400`). Nếu cùng một loại cảnh báo đã phát trong ngày, hệ thống sẽ bỏ qua để không làm phiền người dùng.
* **Tôn trọng Quyền Riêng tư (User Preferences)**:
  - Kiểm tra cờ `notify_system` trong `UserPreference` của người nhận trước khi gửi.

#### 1.3. Cơ chế Bình luận Công việc (Task Comments)
* Lưu trữ qua Model `TaskComment` liên kết trực tiếp với công việc (`Task`) và người gửi (`User`).
* **Bình luận Tự động theo Quy trình (Workflow System Comments)**:
  - Khi Mentor hoặc Trưởng nhóm từ chối kết quả nghiệm thu (chuyển trạng thái từ `REVIEW` về lại `IN_PROGRESS`), hệ thống bắt buộc nhập lý do ($\ge 10$ ký tự) và tự động tạo bình luận dạng:  
    `[YÊU CẦU SỬA]: <Nội dung góp ý của Mentor>`
  - Tự động kích hoạt thông báo Realtime đến Sinh viên phụ trách (`assignee`) để chỉnh sửa kịp thời.

---

### 2. KIẾN TRÚC TÁC VỤ NỀN VỚI REDIS & CELERY (BACKGROUND JOBS)

#### 2.1. Cấu hình Hạ tầng (Broker & Result Backend)
* **Redis**: Đóng vai trò làm Message Broker và Result Backend trung gian lưu trữ hàng đợi tác vụ (`REDIS_URL`, port 6379).
* **Celery Application** (`projecthub_config/celery.py`):
  - Tích hợp sâu vào vòng đời của Django (`autodiscover_tasks`).
  - Múi giờ thiết lập chuẩn theo Việt Nam: `Asia/Ho_Chi_Minh`.

#### 2.2. Lập lịch Định kỳ với Celery Beat (Periodic Tasks)
Hệ thống thiết lập 2 tiến trình chạy ngầm định kỳ tự động:
1. **Kiểm tra trễ hạn hàng ngày (`check-overdue-tasks-and-milestones-daily`)**:
   - **Tần suất**: Chạy vào **08:00 sáng mỗi ngày** (`crontab(hour=8, minute=0)`).
   - **Nhiệm vụ**: Quét toàn bộ các công việc (`Task`) và giai đoạn mốc (`Milestone`) sắp đến hạn hoặc đã vượt quá hạn chót.
2. **Tổng hợp báo cáo tuần bằng AI (`generate-weekly-project-summaries`)**:
   - **Tần suất**: Chạy vào **07:00 sáng Thứ Hai hàng tuần** (`crontab(day_of_week='monday', hour=7, minute=0)`).
   - **Nhiệm vụ**: Tự động quét dữ liệu tiến độ của các đồ án đang thực hiện (`IN_PROGRESS`), gọi AI Engine tổng hợp bản tin tóm tắt tuần và gửi thông báo đến Giảng viên hướng dẫn & Trưởng nhóm.

#### 2.3. Lệnh Quản trị Dự phòng (CLI Commands)
* Cho phép chạy độc lập hoặc gắn vào Cron Job trên môi trường triển khai (Render/VPS) mà không bắt buộc phụ thuộc hoàn toàn vào Celery Beat Daemon:
  - `python manage.py check_overdue`: Quét và bắn cảnh báo trễ hạn tức thì.
  - `python manage.py scan_risks`: Quét toàn diện các đồ án có mức độ rủi ro nghiêm trọng (`CRITICAL`).

---

### 3. QUY TẮC CẢNH BÁO TRỄ HẠN & ĐÁNH GIÁ RỦI RO (OVERDUE & RISK WARNING RULES)

Hệ thống thiết lập các quy tắc rõ ràng dựa trên dữ liệu thực tế:

#### 3.1. Quy tắc Cảnh báo Trễ hạn Công việc (Task Overdue)
* **Điều kiện kích hoạt**:
  $$\text{Task.due\_date} < \text{current\_date} \quad \text{và} \quad \text{Task.status} \neq \text{DONE}$$
* **Đối tượng nhận cảnh báo**:
  1. Người được phân công thực hiện (`assignee`).
  2. Người tạo công việc (`created_by`).
  3. Giảng viên hướng dẫn của đồ án (`mentor`).
* **Kênh gửi cảnh báo**:
  - Gửi thông báo đẩy Realtime lên giao diện Web (chuông thông báo cập nhật số đỏ tức thì).
  - Gửi Email tự động qua dịch vụ thư điện tử (`django.core.mail.send_mail`).

#### 3.2. Quy tắc Cảnh báo Giai đoạn Cột mốc (Milestone Overdue)
* **Điều kiện kích hoạt**:
  $$\text{Milestone.due\_date} < \text{current\_date} \quad \text{và} \quad \text{Milestone.status} \neq \text{COMPLETED}$$
* **Xử lý tự động**:
  - Cập nhật trạng thái CSDL của Milestone sang `OVERDUE` (Quá hạn).
  - Bắn cảnh báo Realtime đến **toàn bộ thành viên trong nhóm đồ án** và **Giảng viên hướng dẫn**, nêu rõ tỷ lệ hoàn thành hiện tại (`progress_percentage%`).

#### 3.3. Bộ Quy tắc Cảnh báo Rủi ro Chuyên sâu (Rules Engine R1 — R9)
Ngoài việc quá hạn theo ngày, hệ thống còn tích hợp bộ luật đánh giá rủi ro đa chiều để cảnh báo sớm trước khi trễ hạn:

| Mã Luật | Tên Quy tắc Cảnh báo | Tiêu chí Kích hoạt | Mức độ |
|---|---|---|:---:|
| **R1** | **Task quá hạn** | Có task chưa xong vượt deadline (cộng thêm điểm phạt nếu task có độ ưu tiên `CRITICAL`). | 🔴 Cao |
| **R2** | **Task bị đình trệ (Stuck Tasks)** | Task nằm ở trạng thái `IN_PROGRESS` $\ge 3$ ngày hoặc `REVIEW` $\ge 2$ ngày không có cập nhật mới. | 🟡 Vừa |
| **R3** | **Milestone nguy cơ trễ** | Milestone còn $\le 14$ ngày nhưng tiến độ đạt dưới 30%. | 🔴 Cao |
| **R4** | **Tiến độ tụt hậu (Progress Lag)** | Tỷ lệ % hoàn thành thực tế thấp hơn đáng kể so với tỷ lệ % thời gian đồ án đã trôi qua. | 🔴 Cao |
| **R5** | **Thiếu hoạt động (Inactivity)** | Toàn nhóm không có bất kỳ log thời gian (`TimeLog`) hay cập nhật nào trong suốt 7 ngày. | 🟡 Vừa |
| **R6** | **Mất cân bằng tải (Workload Imbalance)** | Một sinh viên phải gánh $>50\%$ tổng số task hoặc đang mở $\ge 5$ task cùng lúc. | 🟡 Vừa |
| **R7** | **Tồn đọng góp ý chỉnh sửa** | Phản hồi yêu cầu sửa bài (`NEED_REVISION`) của Mentor quá 5 ngày chưa có task khắc phục. | 🔴 Cao |
| **R8** | **Task mồ côi sát deadline** | Task chưa có người nhận (`assignee = NULL`) mà hạn chót còn dưới 7 ngày. | 🟡 Vừa |
| **R9** | **Milestone rỗng** | Cột mốc tiến độ đã tạo nhưng không được gắn bất kỳ công việc con nào. | 🔵 Thấp |

---

### 4. BẢNG TỔNG HỢP GIÁ TRỊ VÀ ĐIỂM NỔI BẬT CỦA TASK 4

| Tiêu chí | Giải pháp Hiện thực trong ProjectHub | Lợi ích Đạt được |
|---|---|---|
| **Trải nghiệm Thời gian thực** | WebSockets qua Channels + HTTP Polling fallback 30s | Đồng bộ trạng thái tức thì, không cần tải lại trang, không gián đoạn kết nối. |
| **Độ tin cậy Thông báo** | `transaction.on_commit` + Redis dedupe 24h | Đảm bảo thông báo luôn có dữ liệu thật trong DB, loại bỏ spam lặp tin. |
| **Tác vụ Nền Tự động** | Celery Beat + Redis Broker quét 08:00 hàng ngày và 07:00 thứ Hai | Tự động hóa hoàn toàn quy trình cảnh báo trễ hạn và xuất báo cáo tuần AI. |
| **Phát hiện Điểm nghẽn Sớm** | Bộ luật cảnh báo rủi ro 9 cấp độ (R1-R9) | Can thiệp trước khi trễ hạn thật, hỗ trợ Giảng viên và Nhóm tối ưu tiến độ. |
