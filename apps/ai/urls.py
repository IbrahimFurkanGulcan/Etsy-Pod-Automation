from django.urls import path
from . import views

# Namespace tanımlıyoruz 
app_name = 'ai'

urlpatterns = [
    
    path('api/generate/', views.generate_designs_action, name='generate_designs'),
    path('api/process-selected/', views.process_selected_designs_action, name='process_selected'),
    path('api/generate-seo-batch/', views.generate_seo_batch_api, name='generate_seo_batch'),
]