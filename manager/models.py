from django.db import models
from django.contrib.auth.models import User  # <-- SİSTEME KULLANICIYI DAHİL ETTİK

# ==========================================
# 0. MODÜL: KULLANICI AYARLARI (SaaS Core)
# ==========================================
class UserSettings(models.Model):
    # Her kullanıcının sadece 1 ayar profili olabilir (OneToOne)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    
    # API Anahtarı (İleride bunu şifreleyerek kaydedeceğiz)
    replicate_api_key = models.CharField(max_length=255, blank=True, null=True, help_text="Kullanıcının Replicate API Anahtarı")
    
    # Kullanıcının Config sayfasında yaptığı tüm seçimleri ve promptları tek bir JSON'da tutacağız.
    # Bu sayede ileride yeni bir model eklendiğinde veritabanı sütunu eklemek zorunda kalmayız!
    pipeline_config = models.JSONField(default=dict, blank=True, null=True, help_text="Seçili AI modelleri ve custom promptlar")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Ayarları"


# ==========================================
# 1. MODÜL: Etsy'den çekilen ürünlerin ana tablosu
# ==========================================
class EtsyProduct(models.Model):
    # SAHİPLİK BAĞI (Multi-Tenant Mimarisi)
    # Bu ürün kimin? Silinirse ürünleri de silinsin (CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='etsy_products', null=True)

    # Temel Bilgiler
    url = models.URLField(help_text="Etsy Listing URL") # unique=True kaldırdık, çünkü Ali ve Ayşe aynı ürünü çekmek isteyebilir.
    title = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True, help_text="Ürün açıklaması")
    price = models.CharField(max_length=50, blank=True, null=True, help_text="Ürün fiyatı")
    
    # Görseller
    image_url = models.URLField(blank=True, null=True, help_text="Etsy'deki orjinal ürün fotoğrafı")
    local_image_path = models.CharField(max_length=255, blank=True, null=True)
    cropped_image = models.ImageField(upload_to='crops/', blank=True, null=True)
    
    # İstatistikler & Analiz
    tags = models.TextField(blank=True, null=True, help_text="Virgülle ayrılmış tagler")
    favorites_count = models.CharField(max_length=50, default="0") 
    views = models.CharField(max_length=50, blank=True, null=True, help_text="Sepetteki veya görüntülenme sayısı")
    item_review_count = models.CharField(max_length=50, blank=True, null=True, help_text="Bu ürünün yorum sayısı")
    shop_review_count = models.CharField(max_length=50, blank=True, null=True, help_text="Mağazanın toplam yorum sayısı")
    
    # Sistem Logları
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Bir kullanıcı aynı URL'yi iki kez ekleyemesin, ama farklı kullanıcılar ekleyebilsin.
        unique_together = ('user', 'url')

    def __str__(self):
        return self.title[:50] if self.title else self.url


# ==========================================
# 2. ve 3. MODÜL: AI İşlemleri ve Tasarım Varyasyonları
# ==========================================
class DesignVariation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Sırada'),
        ('processing', 'İşleniyor'),
        ('completed', 'Tamamlandı'),
        ('failed', 'Hata'),
        ('approved', 'Kullanıcı Onayladı'),
    ]

    # Varyasyon ürüne bağlı, ürün de kullanıcıya bağlı. Mükemmel hiyerarşi.
    product = models.ForeignKey(EtsyProduct, on_delete=models.CASCADE, related_name='variations')
    
    prompt_used = models.TextField(blank=True, null=True)
    ai_model_name = models.CharField(max_length=100, blank=True, null=True, help_text="Flux, Nano, Seedream vb.")
    
    generated_image = models.ImageField(upload_to='designs/generated/', blank=True, null=True)
    upscaled_image = models.ImageField(upload_to='designs/upscaled/', blank=True, null=True)
    no_bg_image = models.ImageField(upload_to='designs/transparent/', blank=True, null=True) 
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Design for {self.product.id} - {self.status}"


# ==========================================
# 4. MODÜL: SEO ve Title Üretimi
# ==========================================
class SeoOptimization(models.Model):
    product = models.OneToOneField(EtsyProduct, on_delete=models.CASCADE, related_name='seo')
    
    generated_title = models.CharField(max_length=500, blank=True, null=True)
    generated_tags = models.TextField(blank=True, null=True)
    target_keywords = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)