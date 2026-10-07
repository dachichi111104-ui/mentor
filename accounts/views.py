from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from accounts.forms import CustomLoginForm, CustomRegisterForm, ProfileUpdateForm
from accounts.models import User, UserStatus, UserRole
from audit_log.models import ActionType
from audit_log.utils import log_action

from core.ratelimit import ratelimit

def _login_rate_key(request):
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '127.0.0.1')).split(',')[0].strip()
    uname = request.POST.get('username', '').strip().lower()
    return f"{ip}:{uname}"

@ratelimit('login_attempt', limit=5, period=900, key_func=_login_rate_key)
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.status == UserStatus.PENDING_APPROVAL:
                messages.warning(request, 'Tài khoản Giảng viên của bạn đang chờ Quản trị viên phê duyệt.')
                return render(request, 'accounts/login.html', {'form': form})
            elif user.status == UserStatus.SUSPENDED:
                messages.error(request, 'Tài khoản của bạn đã bị khóa do vi phạm quy định.')
                return render(request, 'accounts/login.html', {'form': form})
            elif hasattr(UserStatus, 'REJECTED') and user.status == getattr(UserStatus, 'REJECTED'):
                messages.error(request, 'Tài khoản Giảng viên của bạn đã bị từ chối phê duyệt.')
                return render(request, 'accounts/login.html', {'form': form})
            
            login(request, user)
            log_action(
                user=user,
                action=ActionType.LOGIN,
                entity_type='User',
                entity_id=user.id,
                description=f'Đăng nhập hệ thống thành công với vai trò {user.get_role_display()}',
                request=request
            )
            messages.success(request, f'Chào mừng {user.display_name} đăng nhập thành công.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không chính xác.')
    else:
        form = CustomLoginForm()

    return render(request, 'accounts/login.html', {'form': form})

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            
            selected_role = form.cleaned_data.get('role') or UserRole.STUDENT
            if selected_role not in [UserRole.STUDENT, UserRole.MENTOR]:
                selected_role = UserRole.STUDENT
            user.role = selected_role
            
            if selected_role == UserRole.MENTOR:
                user.status = UserStatus.PENDING_APPROVAL
                user.save()
                messages.warning(request, 'Tài khoản Giảng viên / Mentor đã tạo thành công và đang chờ Quản trị viên (Admin) phê duyệt trước khi đăng nhập.')
            else:
                user.status = UserStatus.ACTIVE
                user.save()
                messages.success(request, f'Tạo tài khoản {user.get_role_display()} thành công! Vui lòng đăng nhập để tiếp tục.')
            return redirect('login')

        else:
            messages.error(request, 'Vui lòng kiểm tra lại thông tin đăng ký.')
    else:
        form = CustomRegisterForm()

    return render(request, 'accounts/register.html', {'form': form})

from django.views.decorators.http import require_POST

@login_required
@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        from dashboard.models import TimeLog
        active_log = TimeLog.objects.filter(user=request.user, ended_at__isnull=True).first()
        if active_log:
            active_log.ended_at = timezone.now()
            active_log.duration = int((active_log.ended_at - active_log.started_at).total_seconds())
            active_log.save()

        log_action(
            user=request.user,
            action=ActionType.LOGOUT,
            entity_type='User',
            entity_id=request.user.id,
            description='Đăng xuất khỏi hệ thống',
            request=request
        )
    logout(request)
    messages.info(request, 'Bạn đã đăng xuất khỏi hệ thống.')
    return redirect('login')

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật thông tin hồ sơ thành công.')
            return redirect('profile')
        else:
            messages.error(request, 'Có lỗi xảy ra khi cập nhật hồ sơ.')
    else:
        form = ProfileUpdateForm(instance=request.user)

    password_form = PasswordChangeForm(request.user)
    return render(request, 'accounts/profile.html', {
        'form': form,
        'password_form': password_form,
    })

@login_required
def change_password_view(request):
    if request.method == 'POST':
        password_form = PasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Đổi mật khẩu tài khoản thành công!')
            return redirect('profile')
        else:
            messages.error(request, 'Không thể đổi mật khẩu. Vui lòng kiểm tra các lỗi bên dưới.')
    else:
        password_form = PasswordChangeForm(request.user)

    form = ProfileUpdateForm(instance=request.user)
    return render(request, 'accounts/profile.html', {
        'form': form,
        'password_form': password_form,
        'active_tab': 'password'
    })

from django.contrib.auth.forms import PasswordResetForm

def forgot_password_view(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(
                request=request,
                use_https=request.is_secure(),
                email_template_name='accounts/password_reset_email.html',
                subject_template_name='accounts/password_reset_subject.txt'
            )
            messages.success(request, 'Yêu cầu đặt lại mật khẩu đã được xử lý. Vui lòng kiểm tra hộp thư email (hoặc console log).')
            return redirect('password_reset_done')
        else:
            messages.error(request, 'Địa chỉ email không hợp lệ.')
    return render(request, 'accounts/forgot_password.html')

from django.http import FileResponse, Http404

@login_required
def avatar_view(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if target.avatar:
        try:
            return FileResponse(target.avatar.open('rb'), as_attachment=False)
        except (FileNotFoundError, OSError, Exception):
            pass
    return redirect(target.get_avatar_url())


from accounts.models import UserPreference
from django.http import JsonResponse

@login_required
def settings_page_view(request):
    user = request.user
    pref, created = UserPreference.objects.get_or_create(user=user)
    profile_form = ProfileUpdateForm(instance=user)
    password_form = PasswordChangeForm(user)

    if request.method == 'POST':
        theme = request.POST.get('theme')
        if theme in ['NAVY', 'FOREST', 'PLUM', 'EMBER']:
            pref.theme = theme
            pref.email_notifications = request.POST.get('email_notifications') == 'on'
            pref.push_notifications = request.POST.get('push_notifications') == 'on'
            pref.week_start = request.POST.get('week_start', 'MONDAY')
            pref.save()
            messages.success(request, 'Đã lưu cài đặt giao diện và hệ thống thành công.')
            return redirect('settings')

    return render(request, 'accounts/settings.html', {
        'pref': pref,
        'profile_form': profile_form,
        'password_form': password_form,
    })


@login_required
def user_settings_api_view(request):
    if request.method == 'POST':
        pref, created = UserPreference.objects.get_or_create(user=request.user)
        theme = request.POST.get('theme')
        if theme in ['NAVY', 'FOREST', 'PLUM', 'EMBER']:
            pref.theme = theme
            pref.save()
            return JsonResponse({'status': 'success', 'theme': pref.theme})
    return JsonResponse({'status': 'error', 'message': 'Yêu cầu không hợp lệ'}, status=400)

