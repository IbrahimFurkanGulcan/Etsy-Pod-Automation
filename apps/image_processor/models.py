from django.db import models
from django.contrib.auth.models import User


class MockupGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mockup_groups')
    name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)


class MockupItem(models.Model):
    group          = models.ForeignKey(MockupGroup, on_delete=models.CASCADE, related_name='items')
    name           = models.CharField(max_length=150)
    mockup_image   = models.ImageField(upload_to='mockups/items/')
    placement_data = models.JSONField(default=dict)  # koordinatlar burada kalabilir
    created_at     = models.DateTimeField(auto_now_add=True)


class MockupResult(models.Model):
    """Her iki pipeline'ın mockup çıktısı — eksik olan buydu"""

    mockup_item = models.ForeignKey(MockupItem, on_delete=models.CASCADE, related_name='results')

    # Pipeline 1: DesignVariation'dan
    design_variation = models.ForeignKey(
        'ai.DesignVariation', on_delete=models.CASCADE,
        related_name='mockup_results', null=True, blank=True
    )
    # Pipeline 2: ManualUpload'dan
    manual_upload = models.ForeignKey(
        'products.ManualUpload', on_delete=models.CASCADE,
        related_name='mockup_results', null=True, blank=True
    )

    result_image = models.ImageField(upload_to='mockups/results/')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # İkisinden biri mutlaka dolu olmalı — DB seviyesinde garanti
            models.CheckConstraint(
                condition=(
                    models.Q(design_variation__isnull=False, manual_upload__isnull=True) |
                    models.Q(design_variation__isnull=True,  manual_upload__isnull=False)
                ),
                name='mockup_result_one_source_only'
            )
        ]