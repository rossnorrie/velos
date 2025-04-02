from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('assets.urls')),  # ✅ This should work
    path('', include('dashboard.urls')),  # ✅ This makes `/` the dashboard


]
