from django.contrib import admin
from .models import UploadGroup, ManualUpload

admin.site.register(UploadGroup)
admin.site.register(ManualUpload)