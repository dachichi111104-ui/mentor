from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from accounts.models import UserStatus

class ActiveUserMiddleware:
    """
    Middleware that checks if an authenticated user's account is still ACTIVE.
    If SUSPENDED or PENDING_APPROVAL, logs them out immediately.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if request.user.status == UserStatus.SUSPENDED:
                logout(request)
                messages.error(request, "Tài khoản của bạn đã bị khóa do vi phạm quy định hoặc yêu cầu từ Quản trị viên.")
                return redirect('login')
            elif request.user.status == UserStatus.PENDING_APPROVAL:
                logout(request)
                messages.warning(request, "Tài khoản Giảng viên của bạn đang chờ Quản trị viên HVHK duyệt.")
                return redirect('login')

        return self.get_response(request)
