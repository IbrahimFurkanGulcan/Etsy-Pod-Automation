from django.urls import path
from . import views




urlpatterns = [
    # Fonksiyonun adı views.py'da 'dashboard' olduğu için burayı da öyle yapıyoruz
    # --- AUTH (Giriş / Kayıt) YOLLARI ---
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_action, name='logout'),

    # --- UYGULAMA YOLLARI ---
    path('', views.config_page, name='config_page'), 
    path('save-config/', views.save_config_action, name='save_config'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('scrape-action/', views.scrape_action, name='scrape_action'),
    path('generate-designs/', views.generate_designs_action, name='generate_designs'),
    path('process-selected/', views.process_selected_designs_action, name='process_selected'),
    path('generate-seo/', views.generate_seo_action, name='generate_seo'),
    path('export-project/', views.export_project_action, name='export_project'),
    path('history/', views.history_page, name='history'),
    path('delete-history/', views.delete_history_item, name='delete_history'),
    
    
]