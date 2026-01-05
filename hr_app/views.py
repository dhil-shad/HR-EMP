from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView, PasswordResetView
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Sum, Count
from django.http import HttpResponse, JsonResponse
from datetime import timedelta, date
import calendar
import math

# Import Models
from .models import ( 
    EmployeeProfile, 
    Attendance, 
    Department, 
    LeaveRequest, 
    Announcement, 
    EarlyClockOutRequest,
    LateArrivalRequest  # <--- Make sure this is imported!
)

# Import Forms
from .forms import (
    UserForm, 
    EmployeeProfileForm, 
    EmployeeUserUpdateForm,
    EmployeeProfilePicForm,
    DepartmentForm, 
    LeaveRequestForm, 
    AnnouncementForm,
    EarlyClockOutForm,
    CustomPasswordResetForm,
    LateArrivalForm  # <--- Make sure this is imported!
)


# =========================================================
# 🔐 AUTHENTICATION & SECURITY
# =========================================================

# 1. Custom Password Reset (Forgot Password)
class CustomPasswordResetView(PasswordResetView):
    template_name = 'hr_app/password_reset_request.html'
    form_class = CustomPasswordResetForm
    from_email = 'noreply@yourdomain.com'
    success_url = '/password_reset_done/'

# 2. Change Password (Logged In User)
@method_decorator(login_required, name='dispatch')
class EmployeePasswordChangeView(PasswordChangeView):
    template_name = 'hr_app/change_password.html'
    success_url = '/dashboard/'

    def form_valid(self, form):
        messages.success(self.request, "Your password was changed successfully!")
        return super().form_valid(form)


# =========================================================
# 🏠 DASHBOARDS
# =========================================================

# 3. Employee Dashboard (Home)
@method_decorator(login_required, name='dispatch')
class EmployeeDashboardView(View):
    def get(self, request):
        if request.user.is_superuser or request.user.is_staff:
            return redirect('admin_dashboard')

        try:
            profile = request.user.employeeprofile
        except EmployeeProfile.DoesNotExist:
            logout(request)
            messages.error(request, "Access Denied: No Profile Found.")
            return redirect('login')
            
        # ---------------------------------------------------------
        # 🤖 AUTO-CLOCK OUT LOGIC
        # If it's past 6:00 PM (18:00) and user is still "Working",
        # automatically close the shift at 6:00 PM.
        # ---------------------------------------------------------
        now = timezone.now()
        current_shift = Attendance.objects.filter(
            employee=profile,
            check_out__isnull=True
        ).first()

        six_pm = now.replace(hour=18, minute=0, second=0, microsecond=0)

        if current_shift and now > six_pm:
            current_shift.check_out = six_pm
            current_shift.save()
            current_shift = None 
            messages.info(request, "System: You were automatically clocked out at 6:00 PM.")
        # ---------------------------------------------------------

        today_record = Attendance.objects.filter(
            employee=profile,
            check_in__date=now.date()
        ).first()
        
        announcements = Announcement.objects.all().order_by('-date_posted')[:5]

        return render(request, 'hr_app/employee_dashboard.html', {
            'profile': profile,
            'current_shift': current_shift,
            'today_record': today_record,
            'announcements': announcements
        })

# 4. Admin Dashboard (Analytics)
@method_decorator(staff_member_required, name='dispatch')
class AdminDashboardView(View):
    def get(self, request):
        total_employees = EmployeeProfile.objects.count()
        present_today = Attendance.objects.filter(check_in__date=timezone.now().date()).count()
        pending_leaves = LeaveRequest.objects.filter(status='Pending').count()
        recent_logins = Attendance.objects.order_by('-check_in')[:5]

        context = {
            'total_employees': total_employees,
            'present_today': present_today,
            'pending_leaves': pending_leaves,
            'recent_logins': recent_logins,
        }
        return render(request, 'hr_app/admin_dashboard.html', context)


# =========================================================
# ⏱️ ATTENDANCE SYSTEM (STRICT RULES)
# =========================================================

# 5. Attendance Toggle (Strict 9:00-9:10 & 6:00 PM Rules)
@method_decorator(login_required, name='dispatch')
class AttendanceToggleView(View):
    def post(self, request):
        try:
            profile = request.user.employeeprofile
        except EmployeeProfile.DoesNotExist:
            return redirect('employee_dashboard')

        # 1. Get UTC Time (for Database)
        now_utc = timezone.now()
        
        # 2. Convert to Local Time (for 9:00 AM Logic)
        # This fixes the "3:30 AM vs 9:00 AM" bug
        now_local = timezone.localtime(now_utc)
        
        # Check for open shift
        latest_attendance = Attendance.objects.filter(
            employee=profile,
            check_out__isnull=True
        ).first()
        
        # --- CLOCK OUT LOGIC ---
        if latest_attendance:
            # Use Local Time to check for 6:00 PM (18:00)
            six_pm = now_local.replace(hour=18, minute=0, second=0, microsecond=0)
            
            if now_local < six_pm:
                messages.warning(request, "It is before 6:00 PM. You must submit an Early Out Request.")
                return redirect('request_early_out')
            
            latest_attendance.check_out = now_utc
            latest_attendance.save()
            messages.success(request, "You have successfully clocked out.")
            
        # --- CLOCK IN LOGIC ---
        else:
            if profile.status != 'Active':
                messages.error(request, f"Access Denied: You cannot clock in while your status is '{profile.status}'.")
                return redirect('employee_dashboard')
            
            # Location Check (Keep existing logic)
            lat_str = request.POST.get('latitude')
            lon_str = request.POST.get('longitude')

            if not lat_str or not lon_str:
                messages.error(request, "Location Error: Could not detect your location. Please allow GPS access.")
                return redirect('employee_dashboard')

            try:
                user_lat = float(lat_str)
                user_lon = float(lon_str)
            except ValueError:
                messages.error(request, "Invalid location data received.")
                return redirect('employee_dashboard')

            distance = calculate_distance(user_lat, user_lon, OFFICE_LAT, OFFICE_LON)
            
            if distance > PERMITTED_RADIUS_METERS:
                messages.error(request, f"Clock In Failed: You are away from the office! (Limit: {PERMITTED_RADIUS_METERS}m)")
                return redirect('employee_dashboard')

            # 3. TIME CHECKS (Using Local Time)
            start_window = now_local.replace(hour=9, minute=0, second=0, microsecond=0)
            end_window = now_local.replace(hour=9, minute=10, second=0, microsecond=0)
            
            # Debugging: Print to console to see exactly what the server sees
            print(f"DEBUG TIME: Current Local: {now_local} | Window: {start_window} to {end_window}")

            if now_local < start_window:
                 messages.error(request, f"You cannot clock in before 9:00 AM. (Server time: {now_local.strftime('%I:%M %p')})")
                 return redirect('employee_dashboard')
            elif start_window <= now_local <= end_window:
                Attendance.objects.create(employee=profile, check_in=now_utc)
                messages.success(request, "Good Morning! Location Verified. You are clocked in.")
            else:
                messages.warning(request, "You are late! Please submit a reason.")
                return redirect('request_late_arrival')
        
        return redirect('employee_dashboard')
# =========================================================
# 🐢 LATE ARRIVAL SYSTEM
# =========================================================

# 6. Request Late Arrival (Employee)
@method_decorator(login_required, name='dispatch')
class RequestLateArrivalView(View):
    def get(self, request):
        form = LateArrivalForm()
        return render(request, 'hr_app/request_late_arrival.html', {'form': form})

    def post(self, request):
        form = LateArrivalForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.employee = request.user.employeeprofile
            req.save()
            messages.info(request, "Late request submitted. Waiting for HR approval.")
            return redirect('employee_dashboard')
        return render(request, 'hr_app/request_late_arrival.html', {'form': form})

# 7. Manage Late Arrivals (Admin List)
@method_decorator(staff_member_required, name='dispatch')
class ManageLateArrivalsView(View):
    def get(self, request):
        requests = LateArrivalRequest.objects.filter(status='Pending').order_by('requested_at')
        return render(request, 'hr_app/manage_late_arrivals.html', {'requests': requests})

# 8. Update Late Arrival Status (Admin Action)
@method_decorator(staff_member_required, name='dispatch')
class UpdateLateArrivalStatusView(View):
    def get(self, request, *args, **kwargs):
        req_id = kwargs.get('req_id')
        status = kwargs.get('status')
        
        try:
            late_req = LateArrivalRequest.objects.get(id=req_id)
        except LateArrivalRequest.DoesNotExist:
            messages.error(request, "Request not found.")
            return redirect('manage_late_arrivals')

        if status == 'Approved':
            late_req.status = 'Approved'
            late_req.save()
            
            # Create the Attendance Record using the requested time
            Attendance.objects.create(
                employee=late_req.employee,
                check_in=late_req.requested_at
            )
            messages.success(request, f"Approved. {late_req.employee.user.username} is now Clocked In.")

        elif status == 'Rejected':
            late_req.status = 'Rejected'
            late_req.save()
            messages.info(request, "Request rejected. Employee NOT clocked in.")
            
        return redirect('manage_late_arrivals')


# =========================================================
# 🏃 EARLY OUT SYSTEM
# =========================================================

# 9. Request Early Out (Employee Form)
@method_decorator(login_required, name='dispatch')
class RequestEarlyOutView(View):
    def get(self, request):
        form = EarlyClockOutForm()
        return render(request, 'hr_app/request_early_out.html', {'form': form})

    def post(self, request):
        try:
            profile = request.user.employeeprofile
            open_shift = Attendance.objects.filter(employee=profile, check_out__isnull=True).first()
        except:
            return redirect('logout')
            
        if not open_shift:
            messages.error(request, "No open shift found.")
            return redirect('employee_dashboard')
            
        form = EarlyClockOutForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.employee = profile
            req.attendance = open_shift
            req.save()
            messages.success(request, "Request submitted. Waiting for Admin approval.")
            return redirect('employee_dashboard')
        return render(request, 'hr_app/request_early_out.html', {'form': form})

# 10. Manage Early Outs (Admin List)
@method_decorator(staff_member_required, name='dispatch')
class ManageEarlyOutsView(View):
    def get(self, request):
        requests = EarlyClockOutRequest.objects.filter(status='Pending').order_by('requested_at')
        return render(request, 'hr_app/manage_early_outs.html', {'requests': requests})

# 11. Approve/Reject Early Out (Admin Action)
@method_decorator(staff_member_required, name='dispatch')
class UpdateEarlyOutStatusView(View):
    def get(self, request, *args, **kwargs):
        req_id = kwargs.get('req_id')
        status = kwargs.get('status')
        
        try:
            req = EarlyClockOutRequest.objects.get(id=req_id)
        except EarlyClockOutRequest.DoesNotExist:
            messages.error(request, "Early Out Request not found.")
            return redirect('manage_early_outs')

        if status == 'Approved':
            req.status = 'Approved'
            req.save()
            
            attendance = req.attendance
            if not attendance.check_out:
                attendance.check_out = timezone.now()
                attendance.save()
                messages.success(request, f"Approved & Clocked Out {req.employee.user.username}.")
            else:
                messages.warning(request, "Request approved, but employee was already clocked out.")

        elif status == 'Rejected':
            req.status = 'Rejected'
            req.save()
            messages.info(request, "Request rejected.")
            
        return redirect('manage_early_outs')


# =========================================================
# 👤 USER PROFILE & SETTINGS
# =========================================================

# 12. Employee Profile (View & Edit Own Profile)
@method_decorator(login_required, name='dispatch')
class EmployeeProfileView(View):
    def get(self, request):
        try:
            profile = request.user.employeeprofile
        except EmployeeProfile.DoesNotExist:
            messages.error(request, "Profile not found.")
            return redirect('logout')

        user_form = EmployeeUserUpdateForm(instance=request.user)
        pic_form = EmployeeProfilePicForm(instance=profile)
        
        return render(request, 'hr_app/employee_profile.html', {
            'profile': profile,
            'user_form': user_form,
            'pic_form': pic_form
        })

    def post(self, request):
        profile = request.user.employeeprofile
        
        if 'update_info' in request.POST:
            user_form = EmployeeUserUpdateForm(request.POST, instance=request.user)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, "Personal details updated.")
                return redirect('employee_profile')
        
        elif 'update_pic' in request.POST:
            pic_form = EmployeeProfilePicForm(request.POST, request.FILES, instance=profile)
            if pic_form.is_valid():
                pic_form.save()
                messages.success(request, "Profile picture updated.")
                return redirect('employee_profile')

        return redirect('employee_profile')


# =========================================================
# 🏖️ LEAVE MANAGEMENT
# =========================================================

# 13. Apply for Leave (Employee)
@method_decorator(login_required, name='dispatch')
class ApplyLeaveView(View):
    def get(self, request):
        form = LeaveRequestForm()
        profile = request.user.employeeprofile
        today = timezone.now()

        # 1. Calculate Leaves Taken THIS MONTH
        current_month_leaves = LeaveRequest.objects.filter(
            employee=profile,
            status='Approved',
            start_date__year=today.year,
            start_date__month=today.month
        )

        leaves_taken_count = 0
        for leave in current_month_leaves:
            delta = leave.end_date - leave.start_date
            leaves_taken_count += (delta.days + 1)
        
        # 2. Determine Available vs Taken
        # Quota is 2
        available_paid = max(0, 2 - leaves_taken_count)
        
        my_leaves = LeaveRequest.objects.filter(employee=profile).order_by('-created_at')
        
        return render(request, 'hr_app/apply_leave.html', {
            'form': form, 
            'my_leaves': my_leaves,
            'available_paid': available_paid,
            'leaves_taken_count': leaves_taken_count
        })

    def post(self, request):
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = request.user.employeeprofile
            leave.save()
            messages.success(request, "Leave request submitted successfully.")
            return redirect('apply_leave')
            
        # If error, we still need context
        profile = request.user.employeeprofile
        my_leaves = LeaveRequest.objects.filter(employee=profile).order_by('-created_at')
        return render(request, 'hr_app/apply_leave.html', {'form': form, 'my_leaves': my_leaves})

# 14. Manage Leaves (Admin)
@method_decorator(staff_member_required, name='dispatch')
class ManageLeavesView(View):
    def get(self, request):
        leaves = LeaveRequest.objects.all().order_by('-created_at')
        return render(request, 'hr_app/manage_leaves.html', {'leaves': leaves})

# 15. Update Leave Status (Admin Action)
@method_decorator(staff_member_required, name='dispatch')
class UpdateLeaveStatusView(View):
    def get(self, request, *args, **kwargs):
        leave_id = kwargs.get('leave_id')
        status = kwargs.get('status')
        
        try:
            leave = LeaveRequest.objects.get(id=leave_id)
        except LeaveRequest.DoesNotExist:
            messages.error(request, "Leave request not found.")
            return redirect('manage_leaves')
            
        if status in ['Approved', 'Rejected']:
            leave.status = status
            leave.save()
            if status == 'Approved':
                leave.employee.status = 'On Leave'
                leave.employee.save()
                
            messages.success(request, f"Leave request {status}.")
            
        return redirect('manage_leaves')


# =========================================================
# 👮 ADMIN: EMPLOYEE MANAGEMENT
# =========================================================

# 16. Create Employee (Onboarding)
@method_decorator(staff_member_required, name='dispatch')
class CreateEmployeeView(View):
    def get(self, request):
        user_form = UserForm()
        profile_form = EmployeeProfileForm()
        return render(request, 'hr_app/create_employee.html', {
            'user_form': user_form, 
            'profile_form': profile_form
        })

    def post(self, request):
        user_form = UserForm(request.POST)
        profile_form = EmployeeProfileForm(request.POST, request.FILES)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            raw_password = user_form.cleaned_data.get('password')
            user.set_password(raw_password)
            user.save()
            
            profile = profile_form.save(commit=False)
            profile.user = user
            count = EmployeeProfile.objects.count() + 1
            profile.employee_id = f"EMP{count:03d}"
            profile.save()
            
            messages.success(request, f"Employee {user.username} created successfully!")
            return redirect('all_employees')
        return render(request, 'hr_app/create_employee.html', {
            'user_form': user_form, 
            'profile_form': profile_form
        })

# 17. All Employees (Directory)
@method_decorator(staff_member_required, name='dispatch')
class AllEmployeesView(View):
    def get(self, request):
        employees = EmployeeProfile.objects.all()
        today = timezone.now().date()
        for emp in employees:
            emp.today_attendance = Attendance.objects.filter(employee=emp, check_in__date=today).first()
            
        context = {
            'employees': employees,
            'total_employees': employees.count(),
            'total_active': employees.filter(status='Active').count()
        }
        return render(request, 'hr_app/all_employees.html', context)

# 18. Admin View Details (Read-Only)
@method_decorator(staff_member_required, name='dispatch')
class AdminEmployeeDetailView(View):
    def get(self, request, *args, **kwargs):
        profile_id = kwargs.get('profile_id')
        try:
            profile = EmployeeProfile.objects.get(id=profile_id)
        except EmployeeProfile.DoesNotExist:
            messages.error(request, "Employee profile not found.")
            return redirect('all_employees')
            
        return render(request, 'hr_app/admin_employee_detail.html', {'profile': profile})

# 19. Edit Employee (Admin Update)
@method_decorator(staff_member_required, name='dispatch')
class EditEmployeeView(View):
    def get(self, request, *args, **kwargs):
        profile_id = kwargs.get('profile_id')
        try:
            profile = EmployeeProfile.objects.get(id=profile_id)
        except EmployeeProfile.DoesNotExist:
            messages.error(request, "Employee not found.")
            return redirect('all_employees')
            
        form = EmployeeProfileForm(instance=profile)
        return render(request, 'hr_app/edit_employee.html', {'form': form, 'profile': profile})

    def post(self, request, *args, **kwargs):
        profile_id = kwargs.get('profile_id')
        try:
            profile = EmployeeProfile.objects.get(id=profile_id)
        except EmployeeProfile.DoesNotExist:
            messages.error(request, "Employee not found.")
            return redirect('all_employees')
            
        form = EmployeeProfileForm(request.POST, request.FILES, instance=profile)
        
        if form.is_valid():
            form.save()
            messages.success(request, "Employee details updated.")
            return redirect('all_employees')
        return render(request, 'hr_app/edit_employee.html', {'form': form, 'profile': profile})

# 20. Delete Employee (Danger Zone)
@method_decorator(staff_member_required, name='dispatch')
class DeleteEmployeeView(View):
    def post(self, request, *args, **kwargs):
        profile_id = kwargs.get('profile_id')
        try:
            profile = EmployeeProfile.objects.get(id=profile_id)
            user = profile.user
            user.delete() 
            messages.success(request, "Employee account deleted successfully.")
        except EmployeeProfile.DoesNotExist:
            messages.error(request, "Employee not found or already deleted.")
            
        return redirect('all_employees')


# =========================================================
# 🏢 MISC ADMIN TOOLS
# =========================================================

# 21. Add Department
@method_decorator(staff_member_required, name='dispatch')
class AddDepartmentView(View):
    def get(self, request):
        form = DepartmentForm()
        departments = Department.objects.all() 
        return render(request, 'hr_app/add_department.html', {
            'form': form, 
            'departments': departments
        })
    
    def post(self, request):
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "New Department added!")
            return redirect('add_department')
            
        departments = Department.objects.all()
        return render(request, 'hr_app/add_department.html', {
            'form': form, 
            'departments': departments
        })

# 22. Create Announcement
@method_decorator(staff_member_required, name='dispatch')
class CreateAnnouncementView(View):
    def get(self, request):
        form = AnnouncementForm()
        announcements = Announcement.objects.all().order_by('-date_posted')
        return render(request, 'hr_app/create_announcement.html', {
            'form': form,
            'announcements': announcements  
        })

    def post(self, request):
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            notice = form.save(commit=False)
            notice.posted_by = request.user
            notice.save()
            messages.success(request, "Announcement posted successfully!")
            return redirect('create_announcement') 
        announcements = Announcement.objects.all().order_by('-date_posted')
        return render(request, 'hr_app/create_announcement.html', {
            'form': form,
            'announcements': announcements
        })

# 23. Delete Announcement (Admin Only)
@method_decorator(staff_member_required, name='dispatch')
class DeleteAnnouncementView(View):
    def post(self, request, *args, **kwargs):
        notice_id = kwargs.get('notice_id')
        try:
            notice = Announcement.objects.get(id=notice_id)
            notice.delete()
            messages.success(request, "Announcement deleted successfully.")
        except Announcement.DoesNotExist:
            messages.error(request, "Announcement not found.")
            
        return redirect('create_announcement')


# =========================================================
# 💰 REPORTS & API
# =========================================================

# 24. Monthly Salary Report
@method_decorator(login_required, name='dispatch')
class MonthlySalaryReportView(View):
    def get(self, request):
        profile = request.user.employeeprofile
        today = timezone.now()
        
        req_month = request.GET.get('month')
        req_year = request.GET.get('year')

        try:
            target_month = int(req_month) if req_month else today.month
            target_year = int(req_year) if req_year else today.year
        except ValueError:
            target_month = today.month
            target_year = today.year

        # 1. CALCULATE WORKED HOURS (From Attendance)
        attendances = Attendance.objects.filter(
            employee=profile,
            check_in__year=target_year,
            check_in__month=target_month,
            check_out__isnull=False
        ).order_by('check_in')
        
        total_seconds = 0
        for att in attendances:
            duration = att.check_out - att.check_in
            total_seconds += duration.total_seconds()
        
        work_hours_float = total_seconds / 3600
        
        # 2. CALCULATE PAID LEAVE HOURS
        # Logic: Find approved leaves that fall in this month
        approved_leaves = LeaveRequest.objects.filter(
            employee=profile,
            status='Approved',
            start_date__year=target_year,
            start_date__month=target_month
        )
        
        leave_days_count = 0
        for leave in approved_leaves:
            # Calculate duration of leave in days (inclusive)
            # Simplification: We assume start & end are in the same month for now
            delta = leave.end_date - leave.start_date
            days = delta.days + 1 
            leave_days_count += days

        # RULE: Max 2 Paid Leaves. Each counts as 9 Hours income.
        paid_leave_days = min(leave_days_count, 2)
        unpaid_leave_days = max(0, leave_days_count - 2)
        
        paid_leave_hours = paid_leave_days * 9  # 9 hours per day
        
        # 3. FINAL TOTALS
        total_payable_hours = work_hours_float + paid_leave_hours
        
        # Convert to Decimal for currency math
        total_hours_decimal = Decimal(str(round(total_payable_hours, 2)))       
        hourly_rate = profile.salary_per_hour if profile.salary_per_hour else Decimal('0.00')
        
        gross_salary = total_hours_decimal * hourly_rate    
        month_name = calendar.month_name[target_month]
        
        return render(request, 'hr_app/salary_report.html', {
            'profile': profile,
            'attendances': attendances,
            'work_hours': round(work_hours_float, 2), # Actual worked
            'paid_leave_hours': paid_leave_hours,     # Bonus hours
            'paid_leave_days': paid_leave_days,
            'unpaid_leave_days': unpaid_leave_days,
            'estimated_salary': round(gross_salary, 2),
            'selected_month': target_month,
            'selected_year': target_year,
            'month_name': month_name
        })

# 25. AJAX API: Check User Existence
def check_user_existence(request):
    username = request.GET.get('username', None)
    email = request.GET.get('email', None)
    
    data = {'username_taken': False, 'email_taken': False}

    if username:
        data['username_taken'] = User.objects.filter(username__iexact=username).exists()
    if email:
        data['email_taken'] = User.objects.filter(email__iexact=email).exists()

    return JsonResponse(data)



# ==========================================
# 📍 OFFICE LOCATION CONFIGURATION
# ==========================================
# REPLACE THESE WITH YOUR ACTUAL OFFICE COORDINATES!
# You can get these from Google Maps (Right click -> Valid numbers)
OFFICE_LAT = 11.258845355278732  # Example: Calicut
OFFICE_LON =  75.78368254232883 
PERMITTED_RADIUS_METERS = 200 # How close they need to be (in meters)

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points in meters using Haversine formula
    """
    R = 6371000 # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c