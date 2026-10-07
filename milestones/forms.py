from django import forms
from milestones.models import Milestone

class MilestoneForm(forms.ModelForm):
    description = forms.CharField(required=False, widget=forms.Textarea)

    class Meta:
        model = Milestone
        fields = ['name', 'description', 'start_date', 'due_date']

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Tên cột mốc không được để trống.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        due = cleaned_data.get('due_date')
        if start and due and due < start:
            raise forms.ValidationError("Ngày hoàn thành không được nhỏ hơn ngày bắt đầu.")
        return cleaned_data
