from django import forms
from core.models.freeze_models import Freeze

class FreezeForm(forms.ModelForm):
    class Meta:
        model = Freeze
        fields = ['target_type', 'region', 'city', 'club', 'member', 'start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'target_type': forms.HiddenInput(),
            'region': forms.Select(attrs={'class': 'form-control'}),
            'city': forms.Select(attrs={'class': 'form-control'}),
            'club': forms.Select(attrs={'class': 'form-control'}),
            'member': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        target_type = kwargs.pop('target_type', None)
        super().__init__(*args, **kwargs)
        if target_type:
            self.fields['target_type'].initial = target_type
            
            # Hide unrelated fields based on target_type
            all_targets = ['region', 'city', 'club', 'member']
            for target in all_targets:
                if target != target_type:
                    self.fields[target].widget = forms.HiddenInput()
                    self.fields[target].required = False
                else:
                    self.fields[target].required = True
