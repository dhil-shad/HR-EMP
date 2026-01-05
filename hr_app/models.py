from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

STATUS_CHOICES = [
    ('Active', 'Active'),
    ('Inactive', 'Inactive'),
    ('On Leave', 'On Leave'),
    ('Deactivated', 'Deactivated'),
]

LEAVE_STATUS_CHOICES = [
    ('Pending', 'Pending'),
    ('Approved', 'Approved'),
    ('Rejected', 'Rejected'),
]

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    date_posted = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class EmployeeProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    employee_id = models.CharField(max_length=10, unique=True, blank=True) 
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    job_title = models.CharField(max_length=50)
    salary_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"

    def calculate_monthly_salary(self, year, month):
        """Calculates the total gross salary for a given month and year."""
        
        attendance_records = self.attendance_set.filter(
            check_in__year=year,
            check_in__month=month,
            check_out__isnull=False 
        )
        
        total_time_worked = timedelta(0)
        
        for record in attendance_records:
            total_time_worked += record.total_work_time
            
        total_hours = total_time_worked.total_seconds() / 3600.0
        
        total_pay = Decimal(total_hours) * self.salary_per_hour
        
        return (total_hours, total_pay)

    def save(self, *args, **kwargs):
        if not self.employee_id:
            last_profile = EmployeeProfile.objects.all().order_by('id').last()
            
            if not last_profile:
                self.employee_id = 'EMP001'
            else:
                try:
                    last_number = int(last_profile.employee_id.replace('EMP', ''))
                    new_number = last_number + 1
                    self.employee_id = f'EMP{new_number:03d}'
                except ValueError:
                    self.employee_id = f'EMP{EmployeeProfile.objects.count() + 1:03d}'

        super().save(*args, **kwargs)


class Attendance(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee.user.username} - {self.check_in.date()}"

    @property
    def total_work_time(self):
        """Calculates total time worked if both check_in and check_out exist."""
        if self.check_in and self.check_out:
            return self.check_out - self.check_in
        return timezone.timedelta(0)


class LeaveRequest(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    reason = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=LEAVE_STATUS_CHOICES, default='Pending')
    
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')

    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Leave for {self.employee.user.username} ({self.status})"


class EarlyClockOutRequest(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE) 
    reason = models.TextField()
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=LEAVE_STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"Early Out: {self.employee.user.username}"
    


class LateArrivalRequest(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    reason = models.TextField()
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Pending', choices=[
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected')
    ])

    def __str__(self):
        return f"Late: {self.employee.user.username} ({self.status})"