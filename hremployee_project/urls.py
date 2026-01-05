from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 1. Root URL Redirect
    # If someone goes to http://127.0.0.1:8000/, send them to the dashboard
    path('', RedirectView.as_view(pattern_name='employee_dashboard', permanent=False), name='home'),

    # 2. Django Admin Interface
    path('admin/', admin.site.urls),

    # 3. Built-in Authentication URLs
    # (Useful for background password logic)
    path('accounts/', include('django.contrib.auth.urls')),

    # 4. Your HR App URLs
    # This connects all the views we wrote in hr_app/urls.py
    path('', include('hr_app.urls')),
]

# 5. Media Files Configuration (Crucial for Profile Pictures)
# This allows Django to serve uploaded images while in Debug mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)