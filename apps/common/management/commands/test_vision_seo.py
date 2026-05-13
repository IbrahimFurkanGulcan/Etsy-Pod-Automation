import os
import time
from dotenv import load_dotenv
from django.core.management.base import BaseCommand

# Modeller
from apps.products.models import ManualUpload
from apps.ai.models import SeoOptimization

# Servisler ve Konfigürasyonlar
from apps.ai.services.generations.image_analysis import VisionAnalysisService
from apps.ai.services.generations.seo import SeoEngineService
from apps.ai.services.config.system_prompts import DEFAULT_SYSTEM_PROMPTS

# Çevre değişkenlerini yükle
load_dotenv()

class Command(BaseCommand):
    help = 'Pipeline 2 (Manuel Yükleme) için Vision Analizi ve ardından SEO (Title & Tag) üretimini uçtan uca test eder.'

    def add_arguments(self, parser):
        parser.add_argument('--upload_id', type=int, help='Analiz edilecek manuel yüklemenin (ManualUpload) ID numarası')
        parser.add_argument('--vision_model', type=str, default='gpt-4o-vision', help='Görsel analiz için kullanılacak model')
        parser.add_argument('--seo_model', type=str, default='gpt-4o', help='SEO üretimi için kullanılacak model')

    def handle(self, *args, **options):
        upload_id = options['upload_id']
        vision_model = options['vision_model']
        seo_model = options['seo_model']

        # API Key kontrolü (OpenAI veya Replicate hangisi varsa)
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("REPLICATE_API_TOKEN")

        if not upload_id:
            self.stdout.write(self.style.ERROR("❌ Hata: --upload_id parametresini girmelisiniz!"))
            return

        if not api_key:
            self.stdout.write(self.style.ERROR("❌ Hata: .env dosyasında API Key bulunamadı!"))
            return

        # 1. VERİTABANINDAN YÜKLENEN GÖRSELİ ÇEK
        try:
            upload = ManualUpload.objects.get(id=upload_id)
        except ManualUpload.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Hata: {upload_id} ID'li ManualUpload kaydı bulunamadı."))
            return

        self.stdout.write(self.style.SUCCESS(f"📦 Dosya Bulundu: {upload.original_filename} (ID: {upload.id})"))
        
        # ==========================================================
        # AŞAMA 1: VİZYON ANALİZİ
        # ==========================================================
        self.stdout.write(self.style.WARNING(f"\n👁️ AŞAMA 1: Vision Motoru Başlatılıyor... ({vision_model})"))
        start_time = time.time()

        vision_result = VisionAnalysisService.analyze_design(
            manual_upload=upload,
            api_key=api_key,
            model_id=vision_model,
            force_recreate=False # <--- BURAYI FALSE YAPTIK!
        )

        if not vision_result.get('success'):
            self.stdout.write(self.style.ERROR(f"❌ Vision Analizi Başarısız: {vision_result.get('error')}"))
            return

        self.stdout.write(self.style.SUCCESS(f"✅ Vision Analizi Tamamlandı! (Süre: {time.time() - start_time:.2f}s)"))
        self.stdout.write(f"📝 Kısmi Analiz Çıktısı: {vision_result['analysis'][:150]}...\n")

        # ==========================================================
        # AŞAMA 2: SEO ÜRETİMİ (Vision Çıktısını Kullanarak)
        # ==========================================================
        self.stdout.write(self.style.WARNING(f"🧠 AŞAMA 2: SEO Motoru Başlatılıyor... ({seo_model})"))
        start_seo_time = time.time()

        # Promptları konfigürasyondan çek (Model isimlerinin sonuna eklediğimiz anahtarlar ile)
        title_prompt = DEFAULT_SYSTEM_PROMPTS.get(f"{seo_model}_title", DEFAULT_SYSTEM_PROMPTS.get("gpt-4o_title"))
        tags_prompt = DEFAULT_SYSTEM_PROMPTS.get(f"{seo_model}_tag", DEFAULT_SYSTEM_PROMPTS.get("gpt-4o_tag"))

        seo_result = SeoEngineService.generate_seo_for_design(
            model_id=seo_model,
            api_key=api_key,
            title_prompt=title_prompt,
            tags_prompt=tags_prompt,
            niche="Graphic T-Shirt",
            manual_upload=upload # DİKKAT: Pipeline 2 kullandığımız için design_variation değil, manual_upload veriyoruz!
        )

        if not seo_result.get('success'):
            self.stdout.write(self.style.ERROR(f"❌ SEO Üretimi Başarısız: {seo_result.get('error')}"))
            return

        # ==========================================================
        # 3. VERİTABANI KONTROLÜ VE ÖZET
        # ==========================================================
        self.stdout.write(self.style.SUCCESS(f"\n✅ Uçtan Uca Zincir Tamamlandı! (Toplam Süre: {time.time() - start_time:.2f}s)"))
        
        try:
            seo_record = SeoOptimization.objects.get(manual_upload=upload)
            self.stdout.write(self.style.SUCCESS("\n📊 --- VERİTABANI KAYIT KONTROLÜ ---"))
            self.stdout.write(f"🆔 SEO Kayıt ID: {seo_record.id}")
            self.stdout.write(f"👁️ Analiz Metni: Kaydedildi ({len(seo_record.vision_analysis)} karakter)")
            self.stdout.write(f"📝 Üretilen Title: {seo_record.generated_title}")
            self.stdout.write(f"🏷️ Üretilen Tags: {seo_record.generated_tags}")
            
        except SeoOptimization.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Hata: Veritabanında SeoOptimization kaydı bulunamadı!"))

        self.stdout.write(self.style.SUCCESS("\n🚀 FİNAL TESTİ BİTTİ!"))