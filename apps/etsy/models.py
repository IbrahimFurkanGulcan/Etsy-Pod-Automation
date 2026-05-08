from django.db import models
from django.contrib.auth.models import User 

class EtsyProduct(models.Model):
    user  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='etsy_products')
    url   = models.URLField()
    title = models.CharField(max_length=500, blank=True)
    description    = models.TextField(blank=True)
    price          = models.CharField(max_length=50, blank=True)
    image_url      = models.URLField(blank=True)
    cropped_image  = models.ImageField(upload_to='crops/', blank=True, null=True)
    tags           = models.TextField(blank=True)          # scrape'ten gelen ham tag
    favorites_count   = models.PositiveIntegerField(default=0)   # CharField değil!
    views             = models.PositiveIntegerField(default=0)
    item_review_count = models.PositiveIntegerField(default=0)
    shop_review_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'url')
        

    # local_image_path kaldırıldı → cropped_image.path zaten bunu veriyor