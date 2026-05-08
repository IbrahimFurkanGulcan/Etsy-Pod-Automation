from django.urls import path
from . import views

app_name = 'image_processor'

urlpatterns = [
    # Ana Arayüz
    path('mockup-templates/', views.mockup_templates_page, name='mockup_templates'),
    
    # API Endpoints
    path('api/save-mockups/', views.save_mockups_action, name='save_mockups'),
    path('api/get-templates/', views.get_mockup_templates_api, name='get_templates'),
    path('api/generate-mockups/', views.generate_mockups_api, name='generate_mockups'),
]