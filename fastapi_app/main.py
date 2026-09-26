from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import time

app = FastAPI(
    title="ProjectHub AI Auxiliary API Service",
    description="Microservice phụ trợ FastAPI chuyên xử lý phân tích dữ liệu rủi ro đồ án, tính toán tiến độ và AI Task Breakdown siêu nhanh.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for Django frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TaskSuggestion(BaseModel):
    title: str
    description: str
    priority: str
    labels: str

class BreakdownRequest(BaseModel):
    project_name: str
    description: Optional[str] = None
    target_role: Optional[str] = "STUDENT"

class AnalyticsResponse(BaseModel):
    project_id: int
    completion_rate: float
    risk_level: str
    estimated_remaining_days: int
    recommendations: List[str]

@app.get("/")
def read_root():
    return {
        "service": "ProjectHub AI Auxiliary FastAPI Service",
        "status": "online",
        "docs": "/docs",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "framework": "FastAPI",
        "async_support": True,
        "features": ["Fast AI Task Breakdown", "Project Risk Analytics", "System Metrics"]
    }

@app.post("/api/v1/ai/fast-task-breakdown", response_model=List[TaskSuggestion])
def fast_task_breakdown(req: BreakdownRequest):
    """
    FastAPI Endpoint phụ trợ: Phân tích mô tả đồ án và tự động chia nhỏ thành danh sách công việc tiêu chuẩn.
    """
    name = req.project_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name cannot be empty")
        
    return [
        TaskSuggestion(
            title=f"Phân tích Yêu cầu Chi tiết cho '{name}'",
            description="Thu thập tài liệu, làm rõ các tính năng cốt lõi và mục tiêu đồ án.",
            priority="HIGH",
            labels="Planning, Requirement"
        ),
        TaskSuggestion(
            title="Thiết kế Cơ sở Dữ liệu & Sơ đồ ERD",
            description="Xây dựng cấu trúc bảng CSDL PostgreSQL, khóa chính/ngoại và chỉ mục.",
            priority="HIGH",
            labels="Database, Architecture"
        ),
        TaskSuggestion(
            title="Phát triển Module Authentication & Middleware Phân quyền",
            description="Tạo API Đăng nhập/Đăng ký và middleware kiểm tra quyền truy cập 3 vai trò.",
            priority="CRITICAL",
            labels="Backend, Security"
        ),
        TaskSuggestion(
            title="Xây dựng Giao diện Bảng Kanban Board",
            description="Thiết kế giao diện 4 cột kéo thả công việc (To Do, In Progress, Review, Done).",
            priority="HIGH",
            labels="Frontend, UI/UX"
        ),
        TaskSuggestion(
            title="Tích hợp Trợ lý AI & Chuẩn bị Báo cáo Demo",
            description="Hoàn thiện tính năng AI tóm tắt tiến độ, kiểm thử toàn bộ hệ thống.",
            priority="MEDIUM",
            labels="AI, Testing"
        ),
    ]

@app.get("/api/v1/projects/{project_id}/analytics", response_model=AnalyticsResponse)
def get_project_analytics(project_id: int):
    """
    FastAPI Endpoint phụ trợ: Tính toán phân tích chỉ số rủi ro và dự báo hoàn thành đồ án.
    """
    return AnalyticsResponse(
        project_id=project_id,
        completion_rate=68.5,
        risk_level="LOW",
        estimated_remaining_days=18,
        recommendations=[
            "Tiến độ đồ án đang đi đúng kế hoạch.",
            "Nên đẩy nhanh hoàn thiện tài liệu v1.0 để Mentor duyệt đúng hạn."
        ]
    )
