from django.contrib import admin
from .models import EmployeeProfile, Attendance, LeaveRequest,Department,Announcement

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'date_posted')


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'user', 'department', 'job_title', 'status', 'salary_per_hour')
    
    list_filter = ('department', 'job_title', 'status')
    
    search_fields = ('employee_id', 'user__username', 'user__first_name', 'user__last_name')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'employee_id', 'status'),
        }),
        ('Job Details', {
            'fields': ('department', 'job_title'),
        }),
        ('Compensation', {
            'fields': ('salary_per_hour',),
        }),
    )


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'check_in', 'check_out', 'total_work_time')
    list_filter = ('employee__department', 'employee__job_title')
    search_fields = ('employee__user__username', 'employee__employee_id')

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'start_date', 'end_date', 'status', 'approved_by')
    list_filter = ('status', 'employee__department')
    search_fields = ('employee__user__username', 'reason')
    
    fieldsets = (
        (None, {
            'fields': ('employee', 'start_date', 'end_date', 'reason'),
        }),
        ('HR Review', {
            'fields': ('status', 'approved_by'),
        }),
    )