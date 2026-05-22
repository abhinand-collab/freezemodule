from django import forms
from core.models.location_models import Region, City, Club

class RegionForm(forms.ModelForm):
    class Meta:
        model = Region
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CityForm(forms.ModelForm):
    class Meta:
        model = City
        fields = ['region', 'name', 'is_active']
        widgets = {
            'region': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ClubForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = ['city', 'name', 'address', 'is_active']
        widgets = {
            'city': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
