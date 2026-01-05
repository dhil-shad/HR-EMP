# hr_app/forms.py
from django import forms
from .models import LeaveRequest,EmployeeProfile,Department,EarlyClockOutRequest
from django.contrib.auth.models import User
from .models import Announcement # <--- Import Announcement
from django.contrib.auth.forms import PasswordResetForm # <--- Import this
from .models import LateArrivalRequest

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    # --- VALIDATION FOR USERNAME ---
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username
# 2. Employee Profile Form (HR Details)
# hr_app/forms.py

class EmployeeProfileForm(forms.ModelForm):
    class Meta:
        model = EmployeeProfile
        # REMOVE 'employee_id' from this list
        fields = ['department', 'job_title', 'salary_per_hour', 'status', 'profile_pic'] 
        widgets = {
            # REMOVE 'employee_id' widget
            'department': forms.Select(attrs={'class': 'form-control'}), # Changed to Select for ForeignKey
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'salary_per_hour': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'profile_pic': forms.FileInput(attrs={'class': 'form-control'}),
        }

# hr_app/forms.py

# ... existing imports ...

# 3. Employee Self-Update Form (Username/Email only)
class EmployeeUserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    
    def clean_email(self):
        # Optional: Ensure email is unique if changed
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already in use.")
        return email
    
class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Marketing'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description...'}),
        }


class EmployeeProfilePicForm(forms.ModelForm):
    class Meta:
        model = EmployeeProfile
        fields = ['profile_pic']
        widgets = {
            'profile_pic': forms.FileInput(attrs={'class': 'form-control'}),
        }


# 6. Announcement Form
class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Office Closed on Friday'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter details here...'}),
        }

class EarlyClockOutForm(forms.ModelForm):
    class Meta:
        model = EarlyClockOutRequest
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Why do you need to leave early?'}),
        }

# hr_app/forms.py

# ... existing imports ...

# 9. Custom Password Reset Form (Requires Username + Email)
class CustomPasswordResetForm(PasswordResetForm):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your username'})
    )
    
    # We don't need to define 'email' because the parent class already has it.
    
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        email = cleaned_data.get("email")

        if username and email:
            # Check if a user exists with BOTH this username AND this email
            if not User.objects.filter(username=username, email=email, is_active=True).exists():
                raise forms.ValidationError("Username and email do not match any active account.")
        
        return cleaned_data
    

class LateArrivalForm(forms.ModelForm):
    class Meta:
        model = LateArrivalRequest
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'My bus broke down...', 'required': True}),
        }