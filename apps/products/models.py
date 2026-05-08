from django.db import models
from django.contrib.auth.models import User

def design_upload_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    h = instance.file_hash or "unknown"
    return f"manual_uploads/{h[:2]}/{h}.{ext}"


class UploadGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='upload_groups')
    name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)


class ManualUpload(models.Model):
    """Pipeline 2: Kullanıcının yüklediği ham tasarım — sadece dosya tutar"""
    group             = models.ForeignKey(UploadGroup, on_delete=models.CASCADE, related_name='uploads')
    image             = models.ImageField(upload_to=design_upload_path)
    original_filename = models.CharField(max_length=255, blank=True, db_index=True)
    file_hash         = models.CharField(max_length=64, db_index=True)  # duplicate guard
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['group', 'file_hash'], name='unique_design_per_group')
        ]

    # vision_analysis    → seo app'ine taşındı (SEO için input)
    # mockup_image_url   → mockups app'ine taşındı (MockupResult)
    # status_seo         → seo app'inde
    # status_mockup      → mockups app'inde
