from django import forms
from projects.models import Project, ProjectCategory, ProjectStatus
from accounts.models import User, UserRole

class ProjectForm(forms.ModelForm):
    mentor = forms.ModelChoiceField(
        queryset=User.objects.filter(role=UserRole.MENTOR),
        required=False,
        widget=forms.Select(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
        label="Giảng viên / Mentor hướng dẫn"
    )

    class Meta:
        model = Project
        fields = ['name', 'code', 'description', 'category', 'technology', 'start_date', 'end_date', 'status', 'mentor', 'repo_url', 'demo_url']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
            'code': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
            'category': forms.Select(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
            'technology': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm', 'placeholder': 'VD: Python, Django, ReactJS...'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
            'status': forms.Select(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
            'repo_url': forms.URLInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
            'demo_url': forms.URLInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        if start and end and end < start:
            raise forms.ValidationError("Ngày kết thúc (Deadline) không được nhỏ hơn ngày bắt đầu.")
        return cleaned_data
