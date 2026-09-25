from django import forms
from django.contrib.auth.forms import AuthenticationForm
from accounts.models import User, UserRole

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
            'username': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs'}),
            'first_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs'}),
            'student_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs', 'placeholder': 'Mã sinh viên / Mã GV...'}),
            'department': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-3 py-2 rounded-lg border border-slate-300 text-xs'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Mật khẩu xác nhận không trùng khớp.")
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
