from django.contrib import admin
from .models import UserProfile, ApiCredential, PipelineConfig # Yeni modellerin

admin.site.register(UserProfile)
admin.site.register(ApiCredential)
admin.site.register(PipelineConfig)
