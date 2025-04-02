from django.urls import path, include
from .views import home_view, lease_view, rental_view, asset_view

urlpatterns = [
    path('', home_view, name='home'),          # /dashboard/ (or / if included at root)
    path('asset/', asset_view, name='asset'),
    path('lease/', lease_view, name='lease'),
    path('rental/', rental_view, name='rental'),
    path('accounts/', include('django.contrib.auth.urls')),
]
