from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # ==========================================
    # 🔐 AUTHENTICATION
    # ==========================================
    path('login/', auth_views.LoginView.as_view(template_name='hr_app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Password Management
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(template_name='hr_app/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='hr_app/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='hr_app/password_reset_complete.html'), name='password_reset_complete'),
    path('change_password/', views.EmployeePasswordChangeView.as_view(), name='change_password'),


    # ==========================================
    # 🏠 DASHBOARDS
    # ==========================================
    path('dashboard/', views.EmployeeDashboardView.as_view(), name='employee_dashboard'),
    path('admin_dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),


    # ==========================================
    # ⏱️ ATTENDANCE & SHIFTS
    # ==========================================
    path('attendance_toggle/', views.AttendanceToggleView.as_view(), name='attendance_toggle'),
    
    # Early Out System
    path('request_early_out/', views.RequestEarlyOutView.as_view(), name='request_early_out'),
    path('manage_early_outs/', views.ManageEarlyOutsView.as_view(), name='manage_early_outs'),
    path('update_early_out/<int:req_id>/<str:status>/', views.UpdateEarlyOutStatusView.as_view(), name='update_early_out'),    
    # Late Arrival System (NEW)
    path('request_late_arrival/', views.RequestLateArrivalView.as_view(), name='request_late_arrival'),
    path('manage_late_arrivals/', views.ManageLateArrivalsView.as_view(), name='manage_late_arrivals'),
    path('update_late_arrival/<int:req_id>/<str:status>/', views.UpdateLateArrivalStatusView.as_view(), name='update_late_arrival'),


    # ==========================================
    # 👤 USER PROFILE
    # ==========================================
    path('my_profile/', views.EmployeeProfileView.as_view(), name='employee_profile'),


    # ==========================================
    # 🏖️ LEAVE MANAGEMENT
    # ==========================================
    path('apply_leave/', views.ApplyLeaveView.as_view(), name='apply_leave'),
    path('manage_leaves/', views.ManageLeavesView.as_view(), name='manage_leaves'),
    path('update_leave_status/<int:leave_id>/<str:status>/', views.UpdateLeaveStatusView.as_view(), name='update_leave_status'),


    # ==========================================
    # 👮 ADMIN: EMPLOYEE MANAGEMENT
    # ==========================================
    path('create_employee/', views.CreateEmployeeView.as_view(), name='create_employee'),
    path('all_employees/', views.AllEmployeesView.as_view(), name='all_employees'),
    path('employee/<int:profile_id>/', views.AdminEmployeeDetailView.as_view(), name='admin_employee_detail'),
    path('edit_employee/<int:profile_id>/', views.EditEmployeeView.as_view(), name='edit_employee'),
    path('delete_employee/<int:profile_id>/', views.DeleteEmployeeView.as_view(), name='delete_employee'),


    # ==========================================
    # 🏢 MISC TOOLS & ANNOUNCEMENTS
    # ==========================================
    path('add_department/', views.AddDepartmentView.as_view(), name='add_department'),
    path('create_announcement/', views.CreateAnnouncementView.as_view(), name='create_announcement'),
    path('delete_announcement/<int:notice_id>/', views.DeleteAnnouncementView.as_view(), name='delete_announcement'),


    # ==========================================
    # 💰 REPORTS & API
    # ==========================================
    path('salary_report/', views.MonthlySalaryReportView.as_view(), name='salary_report'),
    path('api/check_user/', views.check_user_existence, name='check_user_existence'),
]