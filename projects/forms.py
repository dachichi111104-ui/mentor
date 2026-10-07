from django import forms
from projects.models import Project, ProjectCategory, ProjectStatus
from accounts.models import User, UserRole, UserStatus

from django.utils import timezone

class ProjectForm(forms.ModelForm):
    mentor = forms.ModelChoiceField(
        queryset=User.objects.filter(role=UserRole.MENTOR, status=UserStatus.ACTIVE),
        required=False,
        widget=forms.Select(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
        label="Giảng viên / Mentor hướng dẫn"
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'})
    )
    technology = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm', 'placeholder': 'VD: Python, Django, ReactJS...'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'})
    )

    class Meta:
        model = Project
        fields = ['name', 'code', 'description', 'category', 'technology', 'start_date', 'end_date', 'mentor', 'repo_url', 'demo_url']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
            'code': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
            'category': forms.Select(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
            'repo_url': forms.URLInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
            'demo_url': forms.URLInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        if not code:
            raise forms.ValidationError("Mã đồ án không được để trống.")
        qs = Project.objects.filter(code=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f'Mã đồ án "{code}" đã tồn tại trong hệ thống!')
        return code

    def clean_start_date(self):
        val = self.cleaned_data.get('start_date')
        if not val:
            if self.instance and self.instance.pk:
                return self.instance.start_date
            return timezone.now().date()
        return val

    def clean_end_date(self):
        val = self.cleaned_data.get('end_date')
        if not val:
            if self.instance and self.instance.pk:
                return self.instance.end_date
            return (timezone.now() + timezone.timedelta(days=90)).date()
        return val

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        if start and end and end < start:
            raise forms.ValidationError("Ngày kết thúc (Deadline) không được nhỏ hơn ngày bắt đầu.")
        return cleaned_data
