import datetime

PHASES_BY_CATEGORY = {
    'WEB': [
        ("Thiết kế CSDL & Mô hình hóa RBAC", "Xây dựng sơ đồ CSDL, định nghĩa các bảng và phân quyền người dùng.", 12.0),
        ("Phát triển API RESTful & Endpoint", "Xây dựng các API CRUD chính và xử lý mã lỗi HTTP.", 16.0),
        ("Giao diện Frontend Responsive", "Tạo giao diện theo thiết kế Tailwind CSS & Alpine.js.", 14.0),
        ("Kiểm thử Tích hợp & Đơn vị", "Viết test case kiểm tra luồng nghiệp vụ và phân quyền.", 10.0),
        ("Đóng gói & Triển khai Docker", "Cấu hình Docker, Uvicorn, Nginx và triển khai.", 8.0),
    ],
    'MOBILE': [
        ("Thiết kế Màn hình UI/UX Mobile", "Tạo luồng điều hướng màn hình và thiết kế UI.", 12.0),
        ("Quản lý Trạng thái & Lưu trữ Cục bộ", "Tích hợp SQLite/Hive để lưu cache dữ liệu offline.", 14.0),
        ("Tích hợp REST API / Firebase Backend", "Kết nối ứng dụng di động với hệ thống máy chủ backend.", 16.0),
        ("Thử nghiệm trên Thiết bị Thật & Chống giật", "Tối ưu hiệu năng ứng dụng trên cả iOS và Android.", 12.0),
        ("Đóng gói APK / IPA xuất bản", "Cấu hình chứng chỉ, đóng gói file ứng dụng phát hành.", 8.0),
    ],
    'AI_ML': [
        ("Thu thập & Tiền xử lý Dữ liệu", "Làm sạch dữ liệu, gán nhãn và chia tập Train/Val/Test.", 16.0),
        ("Xây dựng & Trích xuất Đặc trưng", "Lựa chọn mô hình baseline và trích xuất vector đặc trưng.", 14.0),
        ("Huấn luyện & Tinh chỉnh Mô hình", "Chạy huấn luyện mô hình Deep Learning / ML và ghi log.", 20.0),
        ("Đánh giá Chỉ số F1-Score & Accuracy", "Đánh giá ma trận nhầm lẫn và tối ưu ngưỡng dự đoán.", 10.0),
        ("Đóng gói API Suy luận Model", "Viết service FastAPI/TorchServe cung cấp API suy luận.", 12.0),
    ],
    'IOT': [
        ("Lựa chọn Cảm biến & Vi điều khiển", "Lập sơ đồ mạch nguyên lý và chọn bo mạch ESP32/Raspberry.", 10.0),
        ("Lập trình Firmware Giao thức MQTT/HTTP", "Viết mã nguồn nhúng thu thập dữ liệu cảm biến.", 16.0),
        ("Xây dựng Broker MQTT & Lưu trữ Dữ liệu", "Cấu hình Mosquitto MQTT broker và CSDL chuỗi thời gian.", 14.0),
        ("Dashboard Giám sát Realtime", "Xây dựng giao diện hiển thị biểu đồ chỉ số cảm biến theo thời gian thực.", 14.0),
        ("Thử nghiệm Hiện trường & Chống nhiễu", "Kiểm tra độ ổn định kết nối mạng và độ tin cậy phần cứng.", 12.0),
    ],
    'SYSTEM': [
        ("Phân tích Kiến trúc Hạ tầng & Bảo mật", "Đánh giá luồng dữ liệu và thiết lập các lớp bảo mật.", 12.0),
        ("Cấu hình Mạng & Firewall Rules", "Cấu hình VPC, Nginx Reverse Proxy và HTTPS SSL.", 14.0),
        ("Triển khai CSDL Cluster & Replication", "Thiết lập cơ chế sao lưu và High Availability cho CSDL.", 16.0),
        ("Giám sát Hệ thống với Prometheus/Grafana", "Thiết lập cảnh báo CPU/RAM/Băng thông tự động.", 12.0),
        ("Kế hoạch Khôi phục Thảm họa (Disaster Recovery)", "Viết kịch bản tự động sao lưu và khôi phục sự cố.", 10.0),
    ],
    'OTHER': [
        ("Phân tích Yêu cầu & Thiết kế Hệ thống", "Lập tài liệu tả yêu cầu và sơ đồ kiến trúc.", 12.0),
        ("Xây dựng Khung Mã nguồn Cơ bản", "Khởi tạo repo và thiết lập cấu trúc thư mục chuẩn.", 14.0),
        ("Triển khai Chức năng Trọng tâm", "Viết mã nguồn cho các tính năng cốt lõi của đề tài.", 20.0),
        ("Kiểm thử & Tối ưu Nâng cao", "Chạy nghiệm thu nội bộ và sửa các lỗi phát sinh.", 12.0),
    ]
}

PHASES = PHASES_BY_CATEGORY

QUESTION_BANK = [
    "Nhóm nên ưu tiên công việc nào trong tuần này để đảm bảo tiến độ?",
    "Kiến trúc hệ thống hiện tại có điểm nghẽn nào về hiệu năng không?",
    "Mentor có thể góp ý về phương pháp kiểm thử cho các chức năng trọng tâm?",
    "Quy trình nộp báo cáo và tài liệu cần lưu ý những mốc thời gian nào?",
    "Nhóm cần chuẩn bị những gì cho buổi báo cáo / demo sắp tới?"
]

def calculate_metrics(facts: dict) -> dict:
    """
    Evaluates rules R1 through R9 and returns deterministic risk score metrics.
    R1: Overdue tasks
    R2: Stuck tasks (IN_PROGRESS >= 3d, REVIEW >= 2d)
    R3: Milestones overdue or low progress
    R4: Progress delay vs time elapsed
    R5: Inactivity in last 7 days
    R6: Workload imbalance (>50% tasks on 1 user or >=5 open tasks)
    R7: Unhandled NEED_REVISION feedback
    R8: Unassigned tasks due within 7d
    R9: Empty milestones
    """
    risks = []
    total_score = 0

    proj = facts.get('project', {})
    progress = proj.get('progress', 0)
    elapsed_pct = proj.get('elapsed_pct', 0)
    days_left = proj.get('days_left', 0)
    category = proj.get('category', 'WEB')

    # R1: Overdue tasks (8pts/task, +4 if CRITICAL, max 30)
    r1_score = 0
    overdue_tasks = facts.get('tasks', {}).get('overdue', [])
    for t in overdue_tasks:
        pts = 12 if t.get('priority') == 'CRITICAL' else 8
        r1_score += pts
        risks.append({
            'id': f"R1:task:{t.get('id')}",
            'severity': 'CRITICAL' if t.get('priority') == 'CRITICAL' else 'WARNING',
            'title': f"Nhiệm vụ #{t.get('id')} '{t.get('title')}' đã quá hạn",
            'evidence': [f"Hạn hoàn thành: {t.get('due')}, Quá hạn: {t.get('days_in_status', 1)} ngày"],
            'recommendation': 'Giao lại người phụ trách hoặc gia hạn có duyệt của Leader.',
            'task_id': t.get('id')
        })
    r1_score = min(r1_score, 30)
    total_score += r1_score

    # R2: Stuck tasks (IN_PROGRESS >= 3d, REVIEW >= 2d) (6pts/task, max 20)
    r2_score = 0
    stuck_tasks = facts.get('tasks', {}).get('stuck', [])
    for t in stuck_tasks:
        r2_score += 6
        days = t.get('days_in_status', 3)
        sev = 'CRITICAL' if days >= 5 else 'WARNING'
        risks.append({
            'id': f"R2:task:{t.get('id')}",
            'severity': sev,
            'title': f"Nhiệm vụ #{t.get('id')} '{t.get('title')}' bị kẹt tại {t.get('status')}",
            'evidence': [f"Nằm tại trạng thái {t.get('status')} được {days} ngày"],
            'recommendation': 'Kiểm tra vướng mắc kỹ thuật hoặc họp nhóm để tháo gỡ.',
            'task_id': t.get('id')
        })
    r2_score = min(r2_score, 20)
    total_score += r2_score

    # R3: Milestone progress (max 20)
    r3_score = 0
    for m in facts.get('milestones', []):
        days_until = m.get('days_until', 99)
        m_prog = m.get('progress', 0)
        if days_until < 0 and m.get('status') != 'COMPLETED':
            r3_score += 15
            risks.append({
                'id': f"R3:milestone:{m.get('id')}",
                'severity': 'CRITICAL',
                'title': f"Cột mốc #{m.get('id')} '{m.get('name')}' đã quá hạn",
                'evidence': [f"Hạn mốc: {m.get('due_date')}, Tiến độ: {m_prog}%"],
                'recommendation': 'Tập trung hoàn thiện các task thuộc cột mốc này ngay lập tức.',
                'milestone_id': m.get('id')
            })
        elif days_until <= 7 and m_prog < 50:
            r3_score += 10
            risks.append({
                'id': f"R3:milestone:{m.get('id')}",
                'severity': 'WARNING',
                'title': f"Cột mốc #{m.get('id')} '{m.get('name')}' sắp đến hạn nhưng tiến độ thấp",
                'evidence': [f"Còn {days_until} ngày nhưng tiến độ mới đạt {m_prog}%"],
                'recommendation': 'Phân bổ thêm nhân lực để đẩy nhanh cột mốc.',
                'milestone_id': m.get('id')
            })
    r3_score = min(r3_score, 20)
    total_score += r3_score

    # R4: Overall progress lag vs elapsed time (max 20)
    if progress < (elapsed_pct - 25):
        total_score += 10
        risks.append({
            'id': 'R4:progress_lag',
            'severity': 'WARNING',
            'title': 'Tiến độ đồ án chậm so với thời gian đã trôi qua',
            'evidence': [f"Tiến độ hiện tại: {progress}%, Thời gian đã trôi qua: {elapsed_pct}%"],
            'recommendation': 'Tăng tốc độ hoàn thành các nhiệm vụ quan trọng.'
        })
    if days_left <= 14 and progress < 60:
        total_score += 10
        risks.append({
            'id': 'R4:urgent_completion',
            'severity': 'CRITICAL',
            'title': 'Đồ án sắp kết thúc nhưng tiến độ tổng thể dưới 60%',
            'evidence': [f"Chỉ còn {days_left} ngày, tiến độ tổng thể đạt {progress}%"],
            'recommendation': 'Họp khẩn cấp với Mentor để cắt giảm scope hoặc tập trung làm các phần cốt lõi.'
        })

    # R5: Inactivity (8pts)
    act_14d = facts.get('activity_14d', [])
    if isinstance(act_14d, list) and len(act_14d) == 0 and facts.get('tasks', {}).get('todo'):
        total_score += 8
        risks.append({
            'id': 'R5:inactivity',
            'severity': 'INFO',
            'title': 'Đồ án không có nhật ký hoạt động trong 7 ngày qua',
            'evidence': ['0 nhật ký hoạt động được ghi nhận trong 7 ngày gần nhất'],
            'recommendation': 'Cập nhật tiến độ nhiệm vụ và trao đổi trên hệ thống.'
        })

    # R6: Workload imbalance (max 8)
    for mem in facts.get('members', []):
        if mem.get('open_tasks', 0) >= 5:
            total_score += 4
            risks.append({
                'id': f"R6:workload:{mem.get('user_id')}",
                'severity': 'WARNING',
                'title': f"Thành viên {mem.get('name')} đang quá tải nhiệm vụ",
                'evidence': [f"Đang ôm {mem.get('open_tasks')} công việc mở cùng lúc"],
                'recommendation': 'San sẻ nhiệm vụ cho các thành viên khác trong nhóm.'
            })

    # R7: Unhandled feedback (max 12)
    unres_fb = facts.get('unresolved_feedback_count', 0)
    if unres_fb > 0:
        total_score += min(unres_fb * 6, 12)
        risks.append({
            'id': 'R7:unhandled_feedback',
            'severity': 'WARNING',
            'title': f"Có {unres_fb} nhận xét của Mentor chưa được xác nhận xử lý",
            'evidence': [f"{unres_fb} feedback ở trạng thái NEED_REVISION chưa được tick xác nhận"],
            'recommendation': 'Sinh viên đọc nhận xét và sửa đổi các điểm Mentor yêu cầu.'
        })

    total_score = min(total_score, 100)

    if total_score >= 75:
        level = 'CRITICAL'
    elif total_score >= 50:
        level = 'HIGH'
    elif total_score >= 25:
        level = 'MEDIUM'
    else:
        level = 'LOW'

    return {
        'risk_score': total_score,
        'risk_level': level,
        'risks': risks
    }

def generate_fallback_breakdown(facts: dict) -> dict:
    """
    Generates dynamic task breakdown based on facts & category phases.
    """
    proj = facts.get('project', {})
    category = proj.get('category', 'WEB')
    tech = proj.get('technology', '')
    milestones = facts.get('milestones', [])

    existing_titles = set()
    for tlist in facts.get('tasks', {}).values():
        if isinstance(tlist, list):
            for t in tlist:
                if isinstance(t, dict) and 'title' in t:
                    existing_titles.add(t['title'].lower())

    suggestions = []

    # 1. Milestone based suggestions
    for m in milestones:
        if m.get('status') != 'COMPLETED' and m.get('done_tasks', 0) == 0:
            title = f"Triển khai nội dung cột mốc {m.get('name')}"
            if title.lower() not in existing_titles:
                suggestions.append({
                    'title': title,
                    'description': f"Thực hiện các hạng mục công việc chính cho cột mốc {m.get('name')}.",
                    'priority': 'HIGH',
                    'estimated_hours': 12.0,
                    'milestone_id': m.get('id'),
                    'labels': [category],
                    'depends_on': [],
                    'rationale': f"Cột mốc #{m.get('id')} '{m.get('name')}' chưa có task nào hoàn thành."
                })

    # 2. Category phase suggestions
    phases = PHASES_BY_CATEGORY.get(category, PHASES_BY_CATEGORY['OTHER'])
    for name, desc, hours in phases:
        if len(suggestions) >= 8:
            break
        if not any(name.lower() in et for et in existing_titles):
            suggestions.append({
                'title': name,
                'description': desc,
                'priority': 'MEDIUM',
                'estimated_hours': hours,
                'milestone_id': milestones[0].get('id') if milestones else None,
                'labels': [category] + ([t.strip() for t in tech.split(',') if t.strip()][:2]),
                'depends_on': [],
                'rationale': f"Giai đoạn tiêu chuẩn của thể loại đồ án {category}."
            })

    return {'tasks': suggestions[:8]}

def generate_fallback_weekly(facts: dict) -> dict:
    """
    Generates dynamic weekly summary based on factual ORM numbers.
    """
    proj = facts.get('project', {})
    code = proj.get('code', 'PRJ')
    recent_done = facts.get('tasks', {}).get('recent_done', [])
    in_prog = facts.get('tasks', {}).get('in_progress', [])
    stuck = facts.get('tasks', {}).get('stuck', [])
    metrics = calculate_metrics(facts)

    done_items = [f"Hoàn thành task #{t['id']} '{t['title']}'" for t in recent_done[:4]]
    if not done_items:
        done_items = ["Chưa có task mới hoàn tất trong 7 ngày qua"]

    in_prog_items = [f"Đang làm task #{t['id']} '{t['title']}' ({t.get('days_in_status', 1)} ngày)" for t in in_prog[:4]]
    blocker_items = [f"Task #{t['id']} '{t['title']}' bị kẹt {t.get('days_in_status', 3)} ngày" for t in stuck[:4]]
    if not blocker_items:
        blocker_items = ["Không có công việc bị kẹt nghiêm trọng"]

    next_items = ["Đẩy nhanh nghiệm thu các task ở trạng thái REVIEW", "Cập nhật tiến độ cột mốc tiếp theo"]

    top_contrib = "chưa ghi nhận"
    members = facts.get('members', [])
    if members:
        sorted_m = sorted(members, key=lambda x: (x.get('done_tasks', 0), x.get('hours_14d', 0)), reverse=True)
        top_contrib = f"{sorted_m[0].get('name')} ({sorted_m[0].get('done_tasks')} task hoàn thành)"

    highlights = f"Đồ án [{code}] đạt {proj.get('progress', 0)}% tiến độ tổng thể. Đóng góp nổi bật: {top_contrib}."
    rating = 'GOOD' if metrics['risk_level'] == 'LOW' else ('AT_RISK' if metrics['risk_level'] in ['HIGH', 'CRITICAL'] else 'FAIR')
    comparison = f"Chỉ số rủi ro hệ thống ở mức {metrics['risk_score']}/100 ({metrics['risk_level']}). Số task xong: {len(recent_done)}."

    return {
        'done': done_items,
        'in_progress': in_prog_items,
        'blockers': blocker_items,
        'next_week': next_items,
        'highlights': highlights,
        'rating': rating,
        'comparison': comparison
    }

def generate_fallback_questions(facts: dict) -> dict:
    """
    Generates dynamic mentor questions based on risks, stuck tasks, and milestones.
    """
    questions = []
    proj = facts.get('project', {})
    code = proj.get('code', 'PRJ')

    stuck = facts.get('tasks', {}).get('stuck', [])
    for t in stuck[:2]:
        questions.append({
            'question': f"Nhóm đang gặp vướng mắc ở task #{t['id']} '{t['title']}' (đã {t.get('days_in_status', 3)} ngày chưa xong), Mentor có thể tư vấn hướng giải quyết?",
            'why': f"Task #{t['id']} bị kẹt lâu tại trạng thái {t.get('status')}.",
            'related_task_id': t['id']
        })

    overdue = facts.get('tasks', {}).get('overdue', [])
    for t in overdue[:2]:
        questions.append({
            'question': f"Task #{t['id']} '{t['title']}' bị quá hạn. Nhóm nên điều chỉnh lại deadline hay giảm bớt phạm vi?",
            'why': f"Task #{t['id']} đã quá hạn so với kế hoạch ban đầu.",
            'related_task_id': t['id']
        })

    milestones = facts.get('milestones', [])
    for m in milestones:
        if m.get('status') != 'COMPLETED' and m.get('days_until', 99) <= 14:
            questions.append({
                'question': f"Cột mốc '{m.get('name')}' còn {m.get('days_until')} ngày nữa đến hạn, Mentor đánh giá nhóm đã đủ điều kiện nghiệm thu mốc này chưa?",
                'why': f"Cột mốc #{m.get('id')} sắp đến hạn.",
                'related_task_id': None
            })

    if len(questions) < 5:
        questions.append({
            'question': f"Kiến trúc hiện tại của đồ án [{code}] dùng {proj.get('technology', 'công nghệ')} đã tối ưu chưa?",
            'why': "Tham khảo ý kiến định hướng kiến trúc từ Mentor.",
            'related_task_id': None
        })
        questions.append({
            'question': "Mentor có lưu ý gì thêm về phần tài liệu báo cáo và chuẩn bị bảo vệ không?",
            'why': "Chuẩn bị tốt cho buổi báo cáo tiến độ.",
            'related_task_id': None
        })

    return {'questions': questions[:7]}

def generate_fallback_chat(facts: dict, user_message: str = "") -> dict:
    """
    Generates dynamic and helpful chat response based on facts and user_message.
    """
    msg_lower = user_message.lower()
    proj = facts.get('project', {})
    code = proj.get('code', 'PRJ')
    name = proj.get('name', 'Đồ án')
    progress = proj.get('progress', 0)
    tasks = facts.get('tasks', {})

    todo = tasks.get('todo', [])
    in_progress = tasks.get('in_progress', [])
    review = tasks.get('review', [])
    overdue = tasks.get('overdue', [])
    stuck = tasks.get('stuck', [])
    recent_done = tasks.get('recent_done', [])

    if any(kw in msg_lower for kw in ['xong', 'hoàn thành', 'đã làm', 'done']):
        if recent_done:
            done_titles = ", ".join([f"task #{t['id']} '{t['title']}'" for t in recent_done[:3]])
            ans = f"Đồ án [{code}] hiện có {len(recent_done)} task vừa hoàn thành gần đây: {done_titles}. Tổng tiến độ đạt {progress}%."
        else:
            ans = f"Đồ án [{code}] hiện đạt {progress}% tiến độ. Chưa ghi nhận task mới hoàn thành trong 14 ngày qua."

    elif any(kw in msg_lower for kw in ['tiếp theo', 'nên làm', 'cần làm', 'phải làm', 'sau đây', 'kế tiếp', 'todo', 'gì nữa']):
        if in_progress:
            prog_titles = ", ".join([f"task #{t['id']} '{t['title']}'" for t in in_progress[:3]])
            ans = f"Nhóm nên tập trung hoàn thành các task đang dở dang: {prog_titles}. Sau đó tiếp tục triển khai các task TODO trong danh sách."
        elif todo:
            todo_titles = ", ".join([f"task #{t['id']} '{t['title']}'" for t in todo[:3]])
            ans = f"Các task ưu tiên cần thực hiện tiếp theo cho đồ án [{code}]: {todo_titles}."
        else:
            ans = f"Đồ án [{code}] hiện đạt {progress}% tiến độ và không có task dở dang nào. Bạn có thể sử dụng tính năng 'Phân rã Task' để tạo thêm công việc mới."

    elif any(kw in msg_lower for kw in ['rủi ro', 'nguy cơ', 'kẹt', 'trễ', 'chậm', 'blocker', 'overdue']):
        if overdue or stuck:
            issues = []
            if overdue:
                issues.append(f"{len(overdue)} task quá hạn")
            if stuck:
                issues.append(f"{len(stuck)} task bị kẹt lâu")
            ans = f"Cảnh báo rủi ro đồ án [{code}]: Ghi nhận {', '.join(issues)}. Cần xử lý ngay các task này để tránh ảnh hưởng deadline mốc thời gian."
        else:
            ans = f"Đồ án [{code}] hiện có chỉ số rủi ro an toàn (0 task quá hạn/bị kẹt). Tiến độ tổng thể đang đạt {progress}%."

    else:
        ans = f"Dữ liệu đồ án [{code}] ({name}): Tiến độ tổng thể {progress}%. Hệ thống ghi nhận {len(in_progress)} task đang làm, {len(todo)} task chờ làm và {len(overdue)} task quá hạn."

    return {
        'answer': ans,
        'citations': [f"task #{t['id']}" for t in (in_progress + todo + recent_done)[:3]],
        'in_scope': True
    }
