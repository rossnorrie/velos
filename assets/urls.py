from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssetViewSet, LeaseViewSet, asset_list, asset_ms_graph_asset_list, asset_ms_graph_user_list, asset_ms_graph_user_orbit, asset_list, doc_list, doc_sim, tree_report_view
from . import views

# ✅ API Router
router = DefaultRouter()
router.register(r'assets', AssetViewSet)
router.register(r'leases', LeaseViewSet)

# ✅ URL Patterns
urlpatterns = [
    path('api/', include(router.urls)),  # API endpoints

    path('asset/', views.asset_list, name='asset_list'),
    path('doc_list/', views.doc_list, name='doc_list'),
    path('doc_sim/', views.doc_sim, name='doc_sim'),
    path('tree_report_view/', views.tree_report_view, name='tree_report_view'),
    path('ms_graph_asset_list/', asset_ms_graph_asset_list, name='asset_ms_graph_asset_list'),
    path('ms_graph_user_list/', asset_ms_graph_user_list, name='asset_ms_graph_user_list'),
    path('ms_graph_user_orbit/', asset_ms_graph_user_orbit, name='asset_ms_graph_user_orbit'),
]
