# BÁO CÁO THIẾT KẾ & HIỆN THỰC — TASK 3
## QUẢN LÝ TÀI LIỆU, NHẬT KÝ THAY ĐỔI (AUDIT LOG) VÀ REVIEW TASK
**Hệ thống**: ProjectHub AI — Nền tảng Quản lý Đồ án & NCKH Hàng không (Học viện Hàng không Việt Nam - VAA)  
**Nhánh Git**: `main` / `fix/vong-4`

---

### 1. QUẢN LÝ TÀI LIỆU ĐỒ ÁN (DOCUMENT MANAGEMENT & UPLOAD)

#### 1.1. Mô hình Dữ liệu Tài liệu
Hệ thống tổ chức tài liệu đồ án qua 2 Model chính trong ứng dụng `documents/`:
* **`Document`**:
  - `project`: Liên kết Foreign Key tới Đồ án (`Project`).
  - `uploaded_by`: Người tải lên (Sinh viên nhóm trưởng, thành viên hoặc Mentor).
  - `title`: Tên hiển thị của tài liệu.
  - `file`: Đường dẫn lưu trữ tệp tin trên hệ thống máy chủ (`project_documents/`).
  - `file_type`: Phân loại tệp tự động (`FileCategory` enum: `PDF`, `WORD`, `EXCEL`, `POWERPOINT`, `ZIP`, `IMAGE`, `CODE`, `OTHER`).
  - `file_size`: Dung lượng tệp đã định dạng (`KB` hoặc `MB`).
  - `current_version`: Số phiên bản hiện tại của tài liệu (mặc định khởi tạo là `1`).
  - `description`: Mô tả mục đích hoặc nội dung tóm tắt của tài liệu.

#### 1.2. Cơ chế Xác thực An toàn khi Tải lên (Security & Validation)
Nhằm chống các lỗ hổng tải tệp độc hại (RCE, XSS, Zip Slip, DoS), hàm `validate_uploaded_file` (`documents/views.py`) thực hiện chuỗi kiểm định nghiêm ngặt:
1. **Giới hạn dung lượng**: Tối đa **20 MB** (`MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024`).
2. **Kiểm tra định dạng cho phép (Whitelisting)**:
   - Danh sách đuôi tệp hợp lệ: `pdf`, `doc`, `docx`, `xls`, `xlsx`, `ppt`, `pptx`, `zip`, `rar`, `png`, `jpg`, `jpeg`, `py`, `js`, `java`, `cpp`, `md`, `txt`.
3. **Xác thực chữ ký nhị phân (Magic Bytes Validation - SEC-14)**:
   - Không chỉ dựa vào đuôi file, hệ thống đọc trực tiếp header nhị phân của tệp:
     - `PDF`: Khởi đầu bằng `%PDF`.
     - `PNG`: Khởi đầu bằng `\x89PNG\r\n\x1a\n`.
     - `JPEG/JPG`: Khởi đầu bằng `\xff\xd8\xff`.
     - `DOCX/XLSX/PPTX/ZIP`: Khởi đầu bằng chữ ký nén `PK\x03\x04`.
   - Ngăn chặn hoàn toàn việc đổi tên file mã độc (ví dụ `shell.php` thành `shell.png`).
4. **Kiểm tra tính toàn vẹn (SHA-256 Checksum)**:
   - Tự động băm `hashlib.sha256` nội dung tệp tin để theo dõi tính toàn vẹn và hỗ trợ loại bỏ trùng lặp.
5. **Giới hạn tần suất tải lên (Rate Limiting)**:
   - Sử dụng decorator `@ratelimit('document_upload', limit=30, period=3600)` — tối đa 30 lượt tải lên/giờ trên mỗi tài khoản để chống tấn công làm tràn ổ đĩa.
6. **Xem trước & Tải về an toàn (Safe Preview & Download)**:
   - File PDF và hình ảnh được mở an toàn trong trình duyệt thông qua `FileResponse`.
   - Bổ sung header `@xframe_options_sameorigin` chống tấn công Clickjacking khi nhúng tài liệu trong iframe.

---

### 2. QUẢN LÝ PHIÊN BẢN (VERSIONING) & NHẬT KÝ THAY ĐỔI (AUDIT LOG)

#### 2.1. Quản lý Lịch sử Phiên bản Tài liệu (Document Versioning)
* **Model `DocumentVersion`**:
  - `document`: Khóa ngoại trỏ đến tài liệu gốc `Document`.
  - `file`: Tệp tin tương ứng với phiên bản đó (`project_documents/versions/`).
  - `version_number`: Số thứ tự phiên bản (`v1`, `v2`, `v3`...).
  - `uploaded_by`: Người thực hiện cập nhật phiên bản mới.
  - `change_log`: Ghi chú lý do cập nhật (ví dụ: *"Chỉnh sửa theo góp ý của Thầy Tuấn tại Mốc 2"*).
  - `created_at`: Dấu mốc thời gian tải phiên bản lên.
* **Quy trình Cập nhật Phiên bản (`document_version_upload_view`)**:
  - Khi sinh viên cập nhật tài liệu đã có, hệ thống không ghi đè mất file cũ mà tự động tăng số phiên bản `current_version = current_version + 1`.
  - Bản ghi `DocumentVersion` mới được lưu lại, bảo lưu toàn bộ các phiên bản trước đó để Giảng viên và Nhóm đồ án có thể tra cứu hoặc tải lại các bản thảo cũ khi cần đối chiếu.

#### 2.2. Hệ thống Nhật ký Thay đổi Toàn diện (Audit Log)
* **Model `ActivityLog` (`audit_log/models.py`)**:
  - `user`: Tài khoản thực hiện hành động (nếu xóa tài khoản, hệ thống dùng `SET_NULL` để bảo toàn lịch sử nhật ký).
  - `project`: Đồ án liên quan.
  - `action`: Phân loại theo bộ enum chuẩn `ActionType` gồm 32 hành vi (VD: `UPLOAD_DOCUMENT`, `DELETE_DOCUMENT`, `CREATE_TASK`, `UPDATE_TASK`, `CHANGE_STATUS`, `SUBMIT_REVIEW`, `ADD_COMMENT`, `LOGIN`, `LOGOUT`...).
  - `entity_type`: Tên đối tượng chịu tác động (`Document`, `Task`, `Feedback`, `Milestone`...).
  - `entity_id`: Khóa chính định danh của đối tượng.
  - `description`: Mô tả chi tiết hành động bằng ngôn ngữ tự nhiên.
  - `ip_address`: Địa chỉ IP của máy khách (tự động nhận dạng qua header `HTTP_X_FORWARDED_FOR` hoặc `REMOTE_ADDR`).
  - `created_at`: Thời gian thực hiện chính xác tới từng giây.
* **Tích hợp Tự động qua Helper `log_action()`**:
  - Mọi thao tác cốt lõi trên tài liệu, công việc, đồ án và đánh giá đều tự động ghi log vào CSDL PostgreSQL.
  - Dữ liệu Audit Log được xuất ra trên Dashboard của Quản trị viên, Dashboard cá nhân và tab "Lịch sử hoạt động" của từng đồ án, bảo đảm tính minh bạch, hỗ trợ truy vết sự cố và ngăn chặn gian lận học thuật.

---

### 3. QUY TRÌNH MENTOR REVIEW VÀ PHẢN HỒI (TASK & PROJECT REVIEW WORKFLOW)

#### 3.1. Mô hình Đánh giá Phản hồi (`Feedback` & `ReviewStatus`)
* **Model `Feedback` (`reviews/models.py`)**:
  - `project`: Đồ án được đánh giá.
  - `task` / `milestone`: Tùy chọn liên kết với công việc hoặc cột mốc cụ thể.
  - `mentor`: Giảng viên hướng dẫn thực hiện đánh giá.
  - `content`: Nội dung nhận xét chi tiết, chỉ dẫn kỹ thuật hoặc yêu cầu sửa đổi.
  - `rating`: Đánh giá chất lượng theo thang điểm 1 đến 5 sao.
  - `status`: Kết quả đánh giá theo enum `ReviewStatus`:
    - `PENDING`: Đang chờ xem xét hoặc góp ý thông thường.
    - `APPROVED`: Đã phê duyệt đạt yêu cầu.
    - `NEED_REVISION`: Yêu cầu sinh viên chỉnh sửa, bổ sung.
  - `acknowledged_at` & `acknowledged_by`: Thời điểm và người đại diện nhóm xác nhận đã đọc và tiếp thu ý kiến của Giảng viên.

#### 3.2. Cơ chế Phân quyền & Khóa Chống Trùng lặp
1. **Phân quyền tập trung (`projects/permissions.py`)**:
   - Chỉ Giảng viên hướng dẫn đã được duyệt (`mentor_status == ACCEPTED`) hoặc Admin mới có quyền thực thi `review.submit`.
   - Sinh viên trong nhóm đồ án chỉ được phép xem (`review.view`) và bấm xác nhận tiếp thu (`review.ack`).
2. **Khóa chống gửi đúp (Anti-Double Submission Lock)**:
   - Sử dụng Redis Cache Lock với key `review_lock:{project.id}:{user.id}` thời gian 5 giây để tránh lỗi mạng khiến Mentor bấm đúp nút Gửi tạo ra 2 bản đánh giá trùng nhau.

#### 3.3. Tích hợp Máy trạng thái Đồ án & Nhiệm vụ (State Machine Integration)
Quy trình Review được đồng bộ chặt chẽ với Bảng Kanban và Trạng thái Đồ án:
* **Đối với Nhiệm vụ (Task Kanban Review)**:
  1. Sinh viên kéo task vào cột `REVIEW` (Chờ duyệt).
  2. Mentor kiểm tra sản phẩm/mã nguồn:
     - **Nếu Đạt**: Mentor chuyển trạng thái từ `REVIEW` $\rightarrow$ `DONE` (Hoàn thành).
     - **Nếu Chưa đạt**: Mentor chuyển từ `REVIEW` $\rightarrow$ `IN_PROGRESS` (Cần sửa lại). Hệ thống **bắt buộc nhập lý do tối thiểu 10 ký tự** và tự động sinh bình luận trên task:  
       `[YÊU CẦU SỬA]: <Nội dung góp ý của Mentor>`
* **Đối với Toàn bộ Đồ án (`submit_review_view`)**:
  - Khi đồ án ở trạng thái `REVIEW`:
    - Mentor chọn `APPROVED` $\rightarrow$ Đồ án tự động chuyển sang `COMPLETED` (Nghiệm thu thành công).
    - Mentor chọn `NEED_REVISION` $\rightarrow$ Đồ án quay trở lại `IN_PROGRESS` kèm ghi nhận số sao và phản hồi vào cơ sở dữ liệu.

#### 3.4. Thông báo Đa kênh & Khép kín Vòng lặp Phản hồi
* **Thông báo Realtime**: Ngay khi Mentor gửi review, hàm `notify()` tự động phát thông báo tới tất cả thành viên chính thức (`MemberStatus.ACCEPTED`) trong nhóm qua WebSockets và Notification Center.
* **Xác nhận Đã xử lý (Feedback Acknowledgment)**:
  - Sinh viên sau khi chỉnh sửa theo yêu cầu sẽ bấm nút *"Xác nhận đã xử lý"*.
  - Hệ thống cập nhật trường `acknowledged_at = timezone.now()` và ghi vết vào `ActivityLog`, giúp Giảng viên theo dõi được mức độ phản hồi và thái độ học tập của nhóm.

---

### 4. BẢNG TỔNG HỢP GIÁ TRỊ VÀ ĐIỂM NỔI BẬT CỦA TASK 3

| Tiêu chí | Giải pháp Hiện thực trong ProjectHub | Lợi ích Đạt được |
|---|---|---|
| **Bảo mật Tải tệp** | Whitelist đuôi file, Magic Bytes Validation, Giới hạn 20MB, Rate Limit 30 req/h | Chống mã độc tệp tin tải lên, bảo vệ an toàn cho máy chủ học viện. |
| **Lịch sử Phiên bản** | Bảng `DocumentVersion` tự động tăng số version, lưu log thay đổi | Không bao giờ mất dữ liệu cũ, dễ dàng so sánh tiến trình làm đồ án. |
| **Nhật ký Hoạt động** | Bảng `ActivityLog` ghi vết 32 loại hành động cùng IP và Timestamp | Minh bạch hóa 100% quá trình làm việc nhóm và đánh giá của giảng viên. |
| **Quy trình Mentor Review** | State Machine ràng buộc chặt chẽ, bắt buộc nhập lý do khi yêu cầu sửa bài | Đảm bảo tính sư phạm, sinh viên nắm rõ cần sửa gì, giảng viên theo dõi sát sao. |
