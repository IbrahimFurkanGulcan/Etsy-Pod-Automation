from django.urls import path
from . import views

app_name = 'etsy'

urlpatterns = [
    # Scraping (Kazıma) Endpoint'i
    path('api/analyze/', views.analyze_url_action, name='analyze_url'),
]