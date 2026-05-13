import os
from io import BytesIO
from django.core.files.base import ContentFile
from apps.etsy.models import EtsyProduct
from apps.common.services.file_helper import FileService

class CropService:
    @staticmethod
    def crop_and_save_product_design(product_id, crop_box=None):
        print(f"\n✂️ KIRPMA İŞLEMİ (ID: {product_id})")
        
        # --- KURAL 1: Koordinat Yoksa Kesinlikle Çalışma ---
        if not crop_box:
            print("❌ Koordinat bulunamadı! Varsayılan kırpma iptal edildi.")
            return None

        try:
            product = EtsyProduct.objects.get(id=product_id)
        except EtsyProduct.DoesNotExist:
            return None

        if product.cropped_image and product.cropped_image.name:
            if os.path.exists(product.cropped_image.path):
                print(f"✅ Görsel diskte mevcut, tekrar kırpılmayacak: {product.cropped_image.name}")
                return product.cropped_image

        if not product.image_url: 
            return None

        img = FileService.download_image_as_pil(product.image_url)
        if not img: 
            return None

        # --- KURAL 2: Doğrudan Gelen Koordinatları Kullan (Matematik Yok) ---
        x1, y1, x2, y2 = crop_box
        
        # GÜVENLİK: Pillow için oranların yönü ters ise düzelt
        if x2 < x1: x1, x2 = x2, x1
        if y2 < y1: y1, y2 = y2, y1
        
        final_box = (x1, y1, x2, y2)

        # Kırp
        cropped_img = img.crop(final_box)
        
        # Veritabanına (FileField) Kaydet
        img_io = BytesIO()
        cropped_img.save(img_io, format='PNG')
        
        file_name = f"crop_{product.id}.png"
        product.cropped_image.save(file_name, ContentFile(img_io.getvalue()), save=True)
        
        print(f"💾 Kırpılan resim veritabanına kaydedildi: {product.cropped_image.name}")
        return product.cropped_image