from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.etsy.services.scraper import EtsyScraperService
from apps.ai.services.detect import DetectService
from apps.image_processor.services.crop import CropService
from apps.etsy.models import EtsyProduct
from apps.common.services.file_helper import FileService
from dotenv import load_dotenv
import time
import os

load_dotenv()

class Command(BaseCommand):
    help = 'Veritabanındaki mevcut bir ürün üzerinden AI Tespit ve Kırpma pipeline testini çalıştırır.'

    def add_arguments(self, parser):
        parser.add_argument('product_id', type=int, help='Test edilecek ürünün veritabanı ID değeri')

    def handle(self, *args, **options):
        product_id = options['product_id']

        # 1. VERİTABANINDAN ÜRÜNÜ GETİR
        try:
            product = EtsyProduct.objects.get(id=product_id)
            self.stdout.write(self.style.SUCCESS(f"📦 Ürün Bulundu: {product.title[:50]}..."))
        except EtsyProduct.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Hata: {product_id} ID'li ürün veritabanında yok!"))
            return

        if not product.image_url:
            self.stdout.write(self.style.ERROR("❌ Hata: Ürünün image_url alanı boş!"))
            return

        # 2. RESİM BOYUTLARINI AL (AI tespiti için boyutlar gereklidir)
        self.stdout.write(self.style.WARNING("⏳ Resim analiz ediliyor..."))
        img = FileService.download_image_as_pil(product.image_url)
        if not img:
            self.stdout.write(self.style.ERROR("❌ Hata: Resim indirilemedi!"))
            return

        # 3. AI TESPİT (Vision Service)
        api_key = os.environ.get("REPLICATE_API_TOKEN")
        self.stdout.write(self.style.WARNING("🤖 AI (DINO) tespiti başlatılıyor..."))
        
        coords = DetectService.detect_design_coordinates(
            image_url=product.image_url,
            api_key=api_key,
            image_width=img.width,
            image_height=img.height
        )

        if coords:
            self.stdout.write(self.style.SUCCESS(f"✅ AI Tespiti Başarılı: {coords}"))
        else:
            self.stdout.write(self.style.WARNING("⚠️ AI bir şey bulamadı, varsayılan değerler kullanılacak."))

        # 4. KIRP VE KAYDET (Crop Service)
        self.stdout.write(self.style.WARNING("✂️ Kırpma ve veritabanına kayıt işlemi başlıyor..."))
        cropped_image = CropService.crop_and_save_product_design(product.id, crop_box=coords)

        if cropped_image:
            self.stdout.write(self.style.SUCCESS(f"🎉 İşlem Tamamlandı!"))
            self.stdout.write(f"📁 Dosya: {cropped_image.name}")
            product.refresh_from_db()
            self.stdout.write(f"📍 Yol: {product.cropped_image.path}")
        else:
            self.stdout.write(self.style.ERROR("❌ Kırpma servisi başarısız oldu!"))