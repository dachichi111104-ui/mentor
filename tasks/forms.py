from django import forms
from tasks.models import Task, TaskPriority
from milestones.models import Milestone
from projects.models import MemberStatus
from accounts.models import User

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'assignee', 'milestone', 'due_date', 'labels']

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        if project:
            accepted_user_ids = project.memberships.filter(status=MemberStatus.ACCEPTED).values_list('user_id', flat=True)
            self.fields['assignee'].queryset = User.objects.filter(id__in=accepted_user_ids)
            self.fields['milestone'].queryset = Milestone.objects.filter(project=project)

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError("Tiêu đề công việc không được để trống.")
        return title

    def clean_priority(self):
        priority = self.cleaned_data.get('priority')
        if priority not in TaskPriority.values:
            raise forms.ValidationError("Mức độ ưu tiên không hợp lệ.")
        return priority

    def clean(self):
        cleaned_data = super().clean()
        assignee = cleaned_data.get('assignee')
        milestone = cleaned_data.get('milestone')

        if self.project:
            if assignee:
                mem_exists = self.project.memberships.filter(user=assignee, status=MemberStatus.ACCEPTED).exists()
                if not mem_exists:
                    self.add_error('assignee', "Người được giao không thuộc nhóm dự án.")
            if milestone and milestone.project != self.project:
                self.add_error('milestone', "Milestone không thuộc dự án này.")

        return cleaned_data
