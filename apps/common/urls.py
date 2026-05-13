from django.urls import path
from . import views

app_name = 'common'

urlpatterns = [
    # Pipeline 1 Export Endpoint
    path('api/export-pipeline1/', views.export_pipeline1_action, name='export_pipeline1'),
    path('api/export-pipeline2/', views.export_pipeline2_action, name='export_pipeline2_action'),
    path('api/get-history/', views.get_history_api, name='get_history_api'),
    path('api/get-assets/', views.get_asset_library_api, name='get_asset_library_api'),
    path('api/upload-asset/', views.upload_asset_api, name='upload_asset_api'),
    path('api/delete-asset/', views.delete_asset_api, name='delete_asset_api'),
    path('api/route-assets/', views.route_assets_api, name='route_assets_api'),
]