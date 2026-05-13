import os
import time
from dotenv import load_dotenv
from django.core.management.base import BaseCommand
from apps.ai.models import DesignVariation
from apps.ai.services.upscale import UpscaleService
from apps.ai.services.background_remove import BackgroundRemovalService

# Çevre değişkenlerini zorla yükle (.env)
load_dotenv()

class Command(BaseCommand):
    help = 'Post-Processing (Upscale ve Arka Plan Silme) adımlarını dinamik pipeline ile test eder.'

    def handle(self, *args, **options):
        api_key = os.environ.get("REPLICATE_API_TOKEN")

        if not api_key:
            self.stdout.write(self.style.ERROR("❌ Hata: REPLICATE_API_TOKEN bulunamadı!"))
            return

        # 1. VERİTABANINDAN EN SON ÜRETİLEN GÖRSELİ BUL
        variation = DesignVariation.objects.exclude(generated_image__isnull=True).exclude(generated_image__exact='').last()

        if not variation:
            self.stdout.write(self.style.ERROR("❌ Hata: Veritabanında işlenecek hiçbir AI üretimi bulunamadı!"))
            return

        self.stdout.write(self.style.SUCCESS(f"📦 İşlenecek Varyasyon Bulundu: ID {variation.id} (Model: {variation.ai_model_name})"))
        self.stdout.write(self.style.WARNING(f"🖼️ Kaynak Resim: {variation.generated_image.path}\n"))

        # ==========================================================
        # 2. DİNAMİK PİPELINE SİMÜLASYONU (Senin istediğin o harika yapı)
        # ==========================================================
        mock_pipeline_config = [
            {"step": "upscale", "model": "recraft-crisp"},
            {"step": "bg_removal", "model": "bria-rmbg"}
        ]

        self.stdout.write(self.style.WARNING(f"⏳ Dinamik Pipeline Başlatılıyor..."))
        start_time = time.time()

        success = True
        
        # Dizilimdeki sıraya göre servisleri dinamik olarak tetikle
        for step in mock_pipeline_config:
            if not success:
                self.stdout.write(self.style.ERROR(f"⚠️ Önceki adım başarısız olduğu için {step['step']} adımı iptal edildi."))
                break
                
            if step['step'] == 'upscale':
                success = UpscaleService.process(variation, step['model'], api_key)
            elif step['step'] == 'bg_removal':
                success = BackgroundRemovalService.process(variation, step['model'], api_key)

        # 3. SONUÇLARI İNCELE VE DOĞRULA
        self.stdout.write(self.style.SUCCESS(f"\n✅ İşlem Tamamlandı! (Toplam Süre: {time.time() - start_time:.2f}s)"))
        
        # Veritabanındaki en güncel halini alalım
        variation.refresh_from_db()

        if success:
            self.stdout.write(self.style.SUCCESS(f"🎉 Varyasyon [ID: {variation.id}] başarıyla işlendi!"))
            if variation.upscaled_image and variation.upscaled_image.name:
                self.stdout.write(f"   🔍 Upscaled Kayıtlı: {variation.upscaled_image.path}")
            if variation.no_bg_image and variation.no_bg_image.name:
                self.stdout.write(f"   ✂️ Transparan Kayıtlı: {variation.no_bg_image.path}")
                
            self.stdout.write(self.style.SUCCESS(f"   👉 Nihai Statü: {variation.status}"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Varyasyon işlenirken hata oluştu! Statü: {variation.status}"))

        self.stdout.write(self.style.SUCCESS("\n🚀 FİNAL TESTİ BİTTİ!"))