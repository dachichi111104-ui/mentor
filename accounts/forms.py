from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from accounts.models import User, UserRole, UserStatus

from accounts.utils import generate_mentor_email, generate_student_email

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 focus:ring-1 focus:ring-navy-900 focus:outline-none text-xs',
            'placeholder': 'Tên đăng nhập hoặc Email...'
        }),
        label="Tên đăng nhập / Email"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 focus:ring-1 focus:ring-navy-900 focus:outline-none text-xs',
            'placeholder': 'Mật khẩu...'
        }),
        label="Mật khẩu"
    )

class CustomRegisterForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=[(UserRole.STUDENT, 'Sinh viên (Student)'), (UserRole.MENTOR, 'Giảng viên / Mentor')],
        initial=UserRole.STUDENT,
        required=False,
        widget=forms.Select(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs bg-white focus:ring-1 focus:ring-navy-900 focus:outline-none'}),
        label="Vai trò sử dụng"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs',
            'placeholder': 'Mật khẩu (tối thiểu 6 ký tự)...'
        }),
        label="Mật khẩu"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs',
            'placeholder': 'Xác nhận lại mật khẩu...'
        }),
        label="Xác nhận mật khẩu"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'student_id', 'department', 'phone']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs', 'placeholder': 'VD: 2431540114 hoặc tuannla'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs', 'placeholder': 'VD: 2431540114@vaa.edu.vn hoặc tuannla@vaa.edu.vn'}),
            'first_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs', 'placeholder': 'Họ và tên đệm (VD: Nguyễn Lương)'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs', 'placeholder': 'Tên (VD: Anh Tuấn)'}),
            'student_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs', 'placeholder': 'Mã sinh viên / Mã GV (VD: 2431540114)'}),
            'department': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs', 'placeholder': 'Khoa Công nghệ Thông tin'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs', 'placeholder': 'Số điện thoại...'}),
        }

    def clean_password(self):
        p = self.cleaned_data.get('password')
        if p:
            validate_password(p)
        return p

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Mật khẩu xác nhận không trùng khớp.")

        role = cleaned_data.get('role') or UserRole.STUDENT
        email = cleaned_data.get('email')
        student_id = cleaned_data.get('student_id')
        username = cleaned_data.get('username')
        first_name = cleaned_data.get('first_name', '')
        last_name = cleaned_data.get('last_name', '')

        if not email:
            if role == UserRole.MENTOR:
                cleaned_data['email'] = generate_mentor_email(first_name, last_name)
            else:
                cleaned_data['email'] = generate_student_email(student_id or username)
        elif '@vau.edu.vn' in email:
            cleaned_data['email'] = email.replace('@vau.edu.vn', '@vaa.edu.vn')

        return cleaned_data

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'department', 'class_name', 'bio', 'skills', 'specialization', 'experience', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs'}),
            'department': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs'}),
            'class_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs'}),
            'bio': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs'}),
            'skills': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs'}),
            'specialization': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs'}),
            'experience': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs'}),
            'avatar': forms.FileInput(attrs={'class': 'text-xs text-slate-500'}),
        }

class AdminUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'status', 'password']

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            validate_password(password)
        return password
