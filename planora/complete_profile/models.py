from django import forms
from registration.models import CustomUser

class CompleteProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['full_name', 'student_group']
