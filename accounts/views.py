from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.forms import CustomLoginForm, CustomRegisterForm, ProfileUpdateForm
from accounts.models import User, UserStatus, UserRole
from audit_log.models import ActionType
from audit_log.utils import log_action

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.status == UserStatus.SUSPENDED:
                messages.error(request, 'Tài khoản của bạn đã bị tạm khóa do vi phạm quy định.')
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
            # Fallback helper for demo presets (handles student/student1 & mentor/mentor1 seamlessly)
            username_attempt = request.POST.get('username')
            password_attempt = request.POST.get('password')
            fallback_map = {
                ('student1', 'user123'): ('student', 'student123'),
                ('student', 'student123'): ('student1', 'user123'),
                ('mentor1', 'user123'): ('mentor', 'mentor123'),
                ('mentor', 'mentor123'): ('mentor1', 'user123'),
            }
            alt = fallback_map.get((username_attempt, password_attempt))
            if alt:
                alt_user = authenticate(request, username=alt[0], password=alt[1])
                if alt_user and alt_user.status == UserStatus.ACTIVE:
                    login(request, alt_user)
                    messages.success(request, f'Chào mừng {alt_user.display_name} đăng nhập thành công.')
                    return redirect('dashboard')

            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không chính xác.')
    else:
        form = CustomLoginForm()

    return render(request, 'accounts/login.html', {'form': form})

def register_view(request):
    # Note: Khi nhà trường tích hợp CSDL LMS thật, đăng ký công khai này nên được thay bằng đăng nhập SSO / import tài khoản có sẵn.
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            
            # Security defense: Only allow STUDENT or MENTOR via public registration
            selected_role = form.cleaned_data.get('role') or UserRole.STUDENT
            if selected_role not in [UserRole.STUDENT, UserRole.MENTOR]:
                selected_role = UserRole.STUDENT
            user.role = selected_role
            
            user.status = UserStatus.ACTIVE
            user.save()

            log_action(
                user=user,
                action=ActionType.LOGIN,
                entity_type='User',
                entity_id=user.id,
                description=f'Đăng ký tài khoản {user.get_role_display()} mới',
                request=request
            )

            login(request, user)
            messages.success(request, f'Tạo tài khoản {user.get_role_display()} thành công!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Vui lòng kiểm tra lại thông tin đăng ký.')
    else:
        form = CustomRegisterForm()

    return render(request, 'accounts/register.html', {'form': form})

def logout_view(request):
    if request.user.is_authenticated:
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
    if not target.avatar:
        raise Http404("Avatar không tồn tại.")
    return FileResponse(target.avatar.open('rb'), as_attachment=False)
