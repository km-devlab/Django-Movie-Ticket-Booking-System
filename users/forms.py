from django import forms
from django.contrib.auth.models import User

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adds Bootstrap styles so the fields look nice inside your theme layout
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'