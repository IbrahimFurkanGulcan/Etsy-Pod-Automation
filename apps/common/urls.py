from django.urls import path
from . import views

app_name = 'common'

urlpatterns = [
    # Pipeline 1 Export Endpoint
    path('api/export-pipeline1/', views.export_pipeline1_action, name='export_pipeline1'),
    path('api/export-pipeline2/', views.export_pipeline2_action, name='export_pipeline2_action'),
]