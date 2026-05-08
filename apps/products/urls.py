from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Pipeline 2 Endpointleri
    path('upload-manual-designs/', views.upload_manual_designs_action, name='upload_manual_designs'),
    path('process-batch/', views.process_batch_action, name='process_batch'),
    path('get-batch-mockups/<int:upload_id>/', views.get_batch_mockups, name='get_batch_mockups'),
    path('api/get-library/', views.get_user_library, name='get_user_library'),
]