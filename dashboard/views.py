from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Asset, Lease
from assets.serializers import AssetSerializer, LeaseSerializer

@login_required
def home_view(request):
    return render(request, 'dashboard/home.html')

#@login_required
#def asset_view(request):
#    return render(request, 'dashboard/asset.html')

@login_required
def asset_view(request):
    return render(request, 'assets/asset_list.html')


@login_required
def lease_view(request):
    return render(request, 'dashboard/lease.html')

@login_required
def rental_view(request):
    return render(request, 'dashboard/rental.html')

#@login_required
#def reports_view(request):
#    return render(request, 'dashboard/reports.html')

