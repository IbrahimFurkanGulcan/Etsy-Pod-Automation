from django.apps import AppConfig

class AiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # BEFORE: name = 'ai'
    # AFTER:
    name = 'apps.ai'