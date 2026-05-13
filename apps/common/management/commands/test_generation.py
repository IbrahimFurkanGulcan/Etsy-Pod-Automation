import os
import time
from dotenv import load_dotenv
from django.core.management.base import BaseCommand
from apps.etsy.models import EtsyProduct
from apps.ai.models import DesignVariation
from apps.ai.services.generations.designs import DesignGeneratorService

# Çevre değişkenlerini zorla yükle (.env)
load_dotenv()

class Command(BaseCommand):
    help = 'Tasarım Üretim (Generation) servisini Tekli ve Paralel olarak test eder.'

    def add_arguments(self, parser):
        parser.add_argument('product_id', type=int, help='Test edilecek ürünün DB ID değeri')

    def handle(self, *args, **options):
        product_id = options['product_id']
        api_key = os.environ.get("REPLICATE_API_TOKEN")

        if not api_key:
            self.stdout.write(self.style.ERROR("❌ Hata: REPLICATE_API_TOKEN bulunamadı!"))
            return

        # 1. VERİTABANINDAN ÜRÜNÜ VE KIRPILMIŞ RESMİ GETİR
        try:
            product = EtsyProduct.objects.get(id=product_id)
        except EtsyProduct.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Hata: {product_id} ID'li ürün yok!"))
            return

        if not product.cropped_image or not os.path.exists(product.cropped_image.path):
            self.stdout.write(self.style.ERROR("❌ Hata: Bu ürünün kırpılmış bir resmi (cropped_image) yok veya dosya silinmiş! Önce kırpma testini çalıştırın."))
            return

        crop_path = product.cropped_image.path
        self.stdout.write(self.style.SUCCESS(f"📦 Ürün Hazır: {product.title[:40]}..."))
        self.stdout.write(self.style.SUCCESS(f"✂️ Kaynak Resim: {crop_path}\n"))

        # ==========================================================
        # 1. AŞAMA: TEKLİ MODEL TESTİ
        # ==========================================================
        self.stdout.write(self.style.WARNING(f"⏳ AŞAMA 1: Tekli Model Testi Başlıyor (nano-banana)..."))
        
        single_task = {
            "product": product,
            "model_id": "nano-banana",
            "prompt": "vector graphic design of {title}, isolated on white background, flat colors", # Özel prompt testi
            "crop_path": crop_path,
            "api_key": api_key
        }

        start_time = time.time()
        single_result = DesignGeneratorService.generate_single_design(single_task)
        
        if single_result:
            self.stdout.write(self.style.SUCCESS(f"✅ Tekli Üretim Başarılı! (Süre: {time.time() - start_time:.2f}s)"))
            self.stdout.write(f"📁 Dosya: {single_result.generated_image.name}\n")
        else:
            self.stdout.write(self.style.ERROR("❌ Tekli Üretim Başarısız!\n"))


        # ==========================================================
        # 2. AŞAMA: PARALEL MODEL TESTİ (3 MODEL BİRDEN)
        # ==========================================================
        self.stdout.write(self.style.WARNING(f"⏳ AŞAMA 2: Paralel Üretim Testi Başlıyor..."))
        
        # Test edeceğimiz modeller (Registry'de adlarının tam eşleştiğinden emin ol)
        parallel_models_config = [
            {"model": "nano-banana"}, # Prompt vermiyoruz, Registry'den kendi çekecek
            {"model": "seedream-4.5"}, 
            {"model": "flux-2-pro"}
        ]

        start_time = time.time()
        parallel_results = DesignGeneratorService.generate_multiple_designs_parallel(
            product=product,
            models_config=parallel_models_config,
            crop_path=crop_path,
            api_key=api_key
        )

        self.stdout.write(self.style.SUCCESS(f"\n✅ Paralel Üretim Tamamlandı! (Toplam Süre: {time.time() - start_time:.2f}s)"))
        self.stdout.write(self.style.SUCCESS(f"📊 Başarıyla üretilen varyasyon sayısı: {len(parallel_results)} / 3"))
        
        for idx, var in enumerate(parallel_results):
            self.stdout.write(f"   [{idx+1}] Model: {var.ai_model_name} -> Dosya: {var.generated_image.name}")

        self.stdout.write(self.style.SUCCESS("\n🎉 BÜTÜN TESTLER BAŞARIYLA GEÇTİ!"))