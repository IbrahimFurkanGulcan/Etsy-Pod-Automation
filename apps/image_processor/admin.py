from django.contrib import admin
from .models import MockupGroup, MockupItem, MockupResult

admin.site.register(MockupGroup)
admin.site.register(MockupItem)
admin.site.register(MockupResult)