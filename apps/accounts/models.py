from django.db import models
from django.contrib.auth.models import User
import uuid

# ==========================================
# KULLANICI PROFİLİ VE ANA AYARLAR
# ==========================================
class UserProfile(models.Model):
    """
    SaaS kullanıcılarının genel ayarlarını ve hesap durumlarını tutar.
    Django'nun auth.User modeli ile OneToOne ilişkilidir.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # İleride ödeme veya abonelik (Stripe/Iyzico) sistemi ekleneceği zaman buralar kullanılacak
    is_premium = models.BooleanField(default=False, help_text="Kullanıcı Premium üye mi?")
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    
    # Kullanıcının tercih ettiği arayüz teması vb. genel ayarlar
    theme_preference = models.CharField(max_length=20, default='light', choices=[('light', 'Light'), ('dark', 'Dark')])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} Profil"


# ==========================================
# API KİMLİK BİLGİLERİ (GÜVENLİK)
# ==========================================
class ApiCredential(models.Model):
    """
    Kullanıcıların sisteme girdiği 3. parti API anahtarlarını tutar.
    NOT: Bu tablo ileride şifreleme (Encryption) mantığına geçirilmeli.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='api_credentials')
    
    # Farklı AI sağlayıcıları için ayrı sütunlar (İleride OpenAI, Anthropic vb eklenebilir)
    replicate_key = models.CharField(max_length=255, blank=True, null=True, help_text="Replicate AI API Key")
    openai_key = models.CharField(max_length=255, blank=True, null=True, help_text="OpenAI API Key (İsteğe Bağlı)")
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - API Keys"


# ==========================================
# PIPELINE (İŞ AKIŞI) KONFİGÜRASYONU
# ==========================================
class PipelineConfig(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pipeline_config')
    
    # --- 1. TESPİT (DETECTION) ---
    enable_detection = models.BooleanField(default=True)
    detection_model = models.CharField(max_length=100, default='grounding-dino')
    detection_prompt = models.TextField(blank=True, null=True)

    # --- 2. GÖRSEL ÜRETİM (GENERATION) - Her Model İçin Ayrı Alan ---
    enable_generation = models.BooleanField(default=True)
    
    gen_model_1_id = models.CharField(max_length=50, default='flux-2-pro')
    gen_model_1_enabled = models.BooleanField(default=True)
    gen_model_1_prompt = models.TextField(blank=True, null=True)
    
    gen_model_2_id = models.CharField(max_length=50, default='seedream-4.5')
    gen_model_2_enabled = models.BooleanField(default=True)
    gen_model_2_prompt = models.TextField(blank=True, null=True)
    
    gen_model_3_id = models.CharField(max_length=50, default='nano-banana')
    gen_model_3_enabled = models.BooleanField(default=True)
    gen_model_3_prompt = models.TextField(blank=True, null=True)

    # --- 3. UPSCALE ---
    enable_upscale = models.BooleanField(default=True)
    upscale_model = models.CharField(max_length=100, default='recraft-crisp')

    # --- 4. ARKA PLAN TEMİZLEME (BG REMOVAL) ---
    enable_bg_removal = models.BooleanField(default=True)
    bg_removal_model = models.CharField(max_length=100, default='bria-rmbg')

    # --- 5. GÖRSEL ANALİZ (VISION AI) ---
    enable_vision = models.BooleanField(default=True)
    vision_model = models.CharField(max_length=100, default='gpt-4o-vision')
    vision_system_prompt = models.TextField(blank=True, null=True)
    vision_user_prompt = models.TextField(blank=True, null=True)

    # --- 6. SEO & İÇERİK ÜRETİMİ ---
    enable_seo = models.BooleanField(default=True)
    seo_model = models.CharField(max_length=100, default='gpt-4o')
    seo_title_system_prompt = models.TextField(blank=True, null=True)
    seo_tags_system_prompt = models.TextField(blank=True, null=True)
    seo_user_prompt = models.TextField(blank=True, null=True)
    
    # İstediğin yedek JSON alanı (Opsiyonel olarak kalabilir)
    dynamic_config = models.JSONField(default=dict, blank=True)

    updated_at = models.DateTimeField(auto_now=True)