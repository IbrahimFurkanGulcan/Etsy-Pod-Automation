from django.urls import path
from . import views
from apps.image_processor.views import mockup_templates_page

app_name = 'ui'

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('app/', views.app_home_view, name='app_home'),   
    # Araçlar
    path('app/tshirt/', views.tshirt_category_view, name='tshirt_category'),
    path('app/tshirt/pipeline1/', views.tshirt_pipeline1_view, name='tshirt_pipeline1'),
    path('app/tshirt/pipeline2/', views.tshirt_pipeline2_view, name='tshirt_pipeline2'),
    
    # Ayarlar ve Yönetim Merkezi (Hub ve Alt Sayfalar)
    path('app/settings/', views.settings_hub_view, name='settings'),
    path('app/settings/pipeline/', views.settings_pipeline_view, name='settings_pipeline'), # EKSİKTİ, EKLENDİ
    path('app/settings/mockups/', mockup_templates_page, name='mockup_templates'), # URL'si settings altına alındı
    path('app/settings/history/tshirt/', views.history_tshirt_view, name='history_tshirt'), # URL'si settings altına alındı
]