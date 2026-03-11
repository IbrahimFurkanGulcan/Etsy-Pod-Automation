from django.contrib import admin
from django import forms
from django.utils.html import format_html
from .models import EtsyProduct, DesignVariation, SeoOptimization, UserSettings

# --- 1. Ürün Detayının İçindeki Varyasyon Listesi ---
class DesignVariationInline(admin.TabularInline):
    model = DesignVariation
    extra = 0
    # Önizlemeleri sadece okunabilir yapıyoruz
    readonly_fields = ('image_preview', 'upscale_preview', 'nobg_preview', 'ai_model_name', 'status', 'created_at')
    # Formda hangi sırayla gözüksün?
    fields = ('image_preview', 'generated_image', 'upscale_preview', 'nobg_preview', 'no_bg_image', 'prompt_used', 'ai_model_name', 'status')

    # 1. Ham Tasarım Önizleme
    def image_preview(self, obj):
        if obj.generated_image:
            return format_html('<img src="{}" style="max-height: 150px; border:1px solid #ddd;" />', obj.generated_image.url)
        return "Görsel Yok"
    image_preview.short_description = "1. AI Tasarımı"

    # 2. Upscale Önizleme
    def upscale_preview(self, obj):
        if obj.upscaled_image:
            return format_html('<img src="{}" style="max-height: 150px; border:1px solid blue;" />', obj.upscaled_image.url)
        return "-"
    upscale_preview.short_description = "2. Büyütülmüş"

    # 3. No-BG Önizleme (Arkası şeffaf olduğu belli olsun diye desenli)
    def nobg_preview(self, obj):
        if obj.no_bg_image:
            # Şeffaflık belli olsun diye CSS ile dama tahtası deseni
            checkerboard = "background-image: linear-gradient(45deg, #ccc 25%, transparent 25%), linear-gradient(-45deg, #ccc 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #ccc 75%), linear-gradient(-45deg, transparent 75%, #ccc 75%); background-size: 10px 10px;"
            return format_html('<img src="{}" style="max-height: 150px; border:1px solid green; {}" />', obj.no_bg_image.url, checkerboard)
        return "Henüz İşlenmedi"
    nobg_preview.short_description = "3. Şeffaf (No-BG)"

class SeoOptimizationInline(admin.StackedInline):
    model = SeoOptimization
    can_delete = False
    verbose_name_plural = 'SEO Optimizasyon Verileri'

# --- 2. Ana Ürün Listesi ---
@admin.register(EtsyProduct)
class EtsyProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'title_short', 'crop_preview_small', 'variation_count', 'created_at')
    list_display_links = ('id', 'title_short')
    search_fields = ('title', 'tags')
    readonly_fields = ('crop_preview_large', 'image_preview_large')
    
    inlines = [DesignVariationInline, SeoOptimizationInline]
    
    def title_short(self, obj):
        return obj.title[:50] + "..." if obj.title else "-"
    title_short.short_description = "Başlık"

    def crop_preview_small(self, obj):
        if obj.cropped_image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.cropped_image.url)
        return "-"
    crop_preview_small.short_description = "Kırpılan (Crop)"

    def crop_preview_large(self, obj):
        if obj.cropped_image:
            return format_html('<img src="{}" style="max-height: 300px;" />', obj.cropped_image.url)
        return "Kırpılmış görsel yok"
    crop_preview_large.short_description = "Kırpılan Görsel"

    def image_preview_large(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-height: 300px;" />', obj.image_url)
        return "-"
    image_preview_large.short_description = "Orijinal Etsy Görseli"
    
    def variation_count(self, obj):
        return obj.variations.count()
    variation_count.short_description = "Tasarım Sayısı"


# --- 3. Tasarım Varyasyonları Listesi (Genel Bakış) ---
@admin.register(DesignVariation)
class DesignVariationAdmin(admin.ModelAdmin):
    # Burada 3 resim sütununu yan yana ekliyoruz
    list_display = ('id', 'product_link', 'img_gen', 'img_up', 'img_nobg', 'ai_model_name', 'status', 'created_at')
    list_filter = ('ai_model_name', 'status')

    def product_link(self, obj):
        return obj.product.title[:30]
    product_link.short_description = "Ürün"

    # Sütun 1: Ham
    def img_gen(self, obj):
        if obj.generated_image:
            return format_html('<img src="{}" style="height: 60px;" />', obj.generated_image.url)
        return "-"
    img_gen.short_description = "Ham"

    # Sütun 2: Upscale
    def img_up(self, obj):
        if obj.upscaled_image:
            return format_html('<img src="{}" style="height: 60px; border: 1px solid blue;" />', obj.upscaled_image.url)
        return "-"
    img_up.short_description = "Upscale"

    # Sütun 3: No-BG
    def img_nobg(self, obj):
        if obj.no_bg_image:
            checkerboard = "background-image: linear-gradient(45deg, #ccc 25%, transparent 25%), linear-gradient(-45deg, #ccc 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #ccc 75%), linear-gradient(-45deg, transparent 75%, #ccc 75%); background-size: 10px 10px;"
            return format_html('<img src="{}" style="height: 60px; border: 1px solid green; {}" />', obj.no_bg_image.url, checkerboard)
        return "-"
    img_nobg.short_description = "No-BG"


#1. API Key kutusunu şifre alanına çeviren özel form
class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = '__all__'
        widgets = {
            # render_value=True sayesinde var olan şifre silinmez, noktalar halinde görünür
            'replicate_api_key': forms.PasswordInput(render_value=True),
        }

# 2. Admin panelini bu yeni forma bağlamak
@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    form = UserSettingsForm # Özel formumuzu buraya tanımlıyoruz
    
    list_display = ('user', 'masked_api_key', 'has_pipeline')
    
    def has_pipeline(self, obj):
        return bool(obj.pipeline_config)
    has_pipeline.boolean = True
    has_pipeline.short_description = "AI Konfig. Var mı?"

    def masked_api_key(self, obj):
        key = obj.replicate_api_key
        if key and len(key) > 12:
            return f"{key[:5]}...{key[-4:]}"
        return "Key Yok"
    masked_api_key.short_description = "Replicate API Key"