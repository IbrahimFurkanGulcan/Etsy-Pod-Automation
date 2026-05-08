from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_action, name='logout'),
    path('api/save-config/', views.save_config_action, name='save_config'),
]