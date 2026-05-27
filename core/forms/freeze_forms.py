from django import forms
from django.utils import timezone
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
            'region': forms.Select(attrs={'class': 'form-control select-region'}),
            'city': forms.Select(attrs={'class': 'form-control select-city'}),
            'club': forms.Select(attrs={'class': 'form-control select-club'}),
            'member': forms.Select(attrs={'class': 'form-control select-member'}),
        }

    def __init__(self, *args, **kwargs):
        target_type = kwargs.pop('target_type', None)
        super().__init__(*args, **kwargs)
        if target_type:
            self.fields['target_type'].initial = target_type
            
            hierarchy = ['region', 'city', 'club', 'member']
            try:
                target_index = hierarchy.index(target_type)
            except ValueError:
                target_index = -1
            
            for i, field_name in enumerate(hierarchy):
                if i > target_index:
                    self.fields[field_name].widget = forms.HiddenInput()
                    self.fields[field_name].required = False
                else:
                    self.fields[field_name].required = True
                    # For dependent fields (except region), start with empty queryset if it's a new form
                    if i > 0 and not self.is_bound and not self.instance.pk:
                        self.fields[field_name].queryset = self.fields[field_name].queryset.none()

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        target_type = cleaned_data.get('target_type')
        
        # Determine the target ID based on target_type
        target_id = None
        if target_type == 'region': target_id = cleaned_data.get('region')
        elif target_type == 'city': target_id = cleaned_data.get('city')
        elif target_type == 'club': target_id = cleaned_data.get('club')
        elif target_type == 'member': target_id = cleaned_data.get('member')

        if start_date:
            if start_date < timezone.now().date():
                raise forms.ValidationError("Start date cannot be in the past.")

        if (start_date or end_date) and target_type and target_id:
            from core.models.subscription_models import MemberSubscription
            from django.db.models import Max
            
            subs_query = MemberSubscription.objects.filter(status='active')
            if target_type == 'region': subs_query = subs_query.filter(member__club__city__region=target_id)
            elif target_type == 'city': subs_query = subs_query.filter(member__club__city=target_id)
            elif target_type == 'club': subs_query = subs_query.filter(member__club=target_id)
            elif target_type == 'member': subs_query = subs_query.filter(member=target_id)
            
            max_date = subs_query.aggregate(Max('effective_end_date'))['effective_end_date__max']
            
            if max_date:
                if start_date and start_date > max_date:
                    self.add_error('start_date', f"Start date cannot be after the subscription end date ({max_date}).")
                if end_date and end_date > max_date:
                    self.add_error('end_date', f"End date cannot be after the subscription end date ({max_date}).")

        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError("End date must be after or equal to start date.")
        
        return cleaned_data
