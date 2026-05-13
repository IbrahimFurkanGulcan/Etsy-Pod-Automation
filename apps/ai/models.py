from django.db import models


class DesignVariation(models.Model):
    """Pipeline 1: EtsyProduct'tan AI ile üretilen tasarımlar"""

    class Status(models.TextChoices):
        PENDING    = "pending",    "Sırada"
        PROCESSING = "processing", "İşleniyor"
        COMPLETED  = "completed",  "Tamamlandı"
        FAILED     = "failed",     "Hata"
        APPROVED   = "approved",   "Onaylandı"

    product       = models.ForeignKey('etsy.EtsyProduct', on_delete=models.CASCADE, related_name='variations')
    prompt_used   = models.TextField(blank=True)
    ai_model_name = models.CharField(max_length=100, blank=True)

    generated_image = models.ImageField(upload_to='designs/generated/', blank=True, null=True)
    upscaled_image  = models.ImageField(upload_to='designs/upscaled/',  blank=True, null=True)
    no_bg_image     = models.ImageField(upload_to='designs/transparent/', blank=True, null=True)

    status     = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

class SeoOptimization(models.Model):
    """Her iki pipeline'ın SEO çıktısı"""

    # Pipeline 1
    design_variation = models.OneToOneField(
        'ai.DesignVariation', on_delete=models.CASCADE,
        related_name='seo', null=True, blank=True
    )
    # Pipeline 2
    manual_upload = models.OneToOneField(
        'products.ManualUpload', on_delete=models.CASCADE,
        related_name='seo', null=True, blank=True
    )

    # Vision analizi buraya taşındı (SEO için girdi)
    vision_analysis  = models.TextField(blank=True)
    generated_title  = models.CharField(max_length=500, blank=True)
    generated_tags   = models.TextField(blank=True)
    target_keywords  = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(design_variation__isnull=False, manual_upload__isnull=True) |
                    models.Q(design_variation__isnull=True,  manual_upload__isnull=False)
                ),
                name='seo_one_source_only'
            )
        ]