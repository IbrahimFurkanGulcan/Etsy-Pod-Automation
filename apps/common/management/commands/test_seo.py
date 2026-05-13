import os
import time
from dotenv import load_dotenv
from django.core.management.base import BaseCommand

from apps.ai.models import DesignVariation, SeoOptimization
from apps.ai.services.generations.seo import SeoEngineService

# Çevre değişkenlerini zorla yükle
load_dotenv()

class Command(BaseCommand):
    help = 'Etsy listelemesinden alınan referanslarla AI SEO (Title & Tag) üretimini test eder.'

    def add_arguments(self, parser):
        parser.add_argument('--design_id', type=int, help='SEO üretilecek Tasarımın (DesignVariation) ID numarası')
        parser.add_argument('--model_id', type=str, default='meta-llama-3-70b', help='Model Registry içindeki Metin (LLM) modeli adı')

    def handle(self, *args, **options):
        design_id = options['design_id']
        model_id = options['model_id']

        # Not: Eğer OpenAI (GPT) kullanıyorsan OPENAI_API_KEY, Replicate LLaMA kullanıyorsan REPLICATE_API_TOKEN çekebilirsin.
        # Biz test için ikisinden birini bulmaya çalışalım.
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("REPLICATE_API_TOKEN")

        if not design_id:
            self.stdout.write(self.style.ERROR("❌ Hata: --design_id parametresini girmelisiniz!"))
            return

        if not api_key:
            self.stdout.write(self.style.ERROR("❌ Hata: .env dosyasında API Key (OPENAI_API_KEY veya REPLICATE_API_TOKEN) bulunamadı!"))
            return

        # 1. VERİTABANINDAN TASARIMI VE ÜRÜNÜ ÇEK
        try:
            design = DesignVariation.objects.select_related('product').get(id=design_id)
            product = design.product
        except DesignVariation.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Hata: {design_id} ID'li tasarım bulunamadı."))
            return

        self.stdout.write(self.style.SUCCESS(f"📦 Ürün Bulundu: {product.title[:50]}..."))
        self.stdout.write(self.style.SUCCESS(f"🎨 Tasarım Bulundu: ID {design.id}"))
        self.stdout.write(self.style.WARNING(f"🧠 Kullanılacak LLM Modeli: {model_id}\n"))

        # ==========================================================
        # 2. SİSTEM PROMPTLARI (Arayüzden/Kullanıcı Ayarlarından Geliyormuş Gibi)
        # ==========================================================
        title_system_prompt = (
            "You are an expert Etsy SEO copywriter. Your goal is to rewrite the provided "
            "title to make it highly clickable and optimized for Etsy search algorithms. "
            "IMPORTANT: You MUST return ONLY a valid JSON object. Do not add any conversational text. "
            "Format: {\"new_title\": \"Your optimized title here\"}"
        )

        tags_system_prompt = (
            "You are an expert Etsy SEO specialist. Your goal is to extract and generate highly "
            "relevant, long-tail tags based on the provided niche and reference text. "
            "IMPORTANT: You MUST return ONLY a valid JSON object. Do not add any conversational text. "
            "Format: {\"new_tags\": \"tag1, tag2, tag 3, tag 4\"} "
            "Rules: Generate exactly {needed_count} tags."
        )

        # ==========================================================
        # 3. SEO MOTORUNU TETİKLE
        # ==========================================================
        self.stdout.write(self.style.WARNING("⏳ AI SEO Motoru Başlatılıyor..."))
        start_time = time.time()

        result = SeoEngineService.generate_seo_for_design(
            design_variation=design,
            model_id=model_id,
            api_key=api_key,
            title_prompt=title_system_prompt,
            tags_prompt=tags_system_prompt,
            niche="Graphic T-Shirt" # Test için hardcode
        )

        # ==========================================================
        # 4. SONUÇLARI DOĞRULA
        # ==========================================================
        if result.get('success'):
            self.stdout.write(self.style.SUCCESS(f"\n✅ İşlem Tamamlandı! (Toplam Süre: {time.time() - start_time:.2f}s)"))
            
            # Veritabanından (SeoOptimization tablosundan) güncel kaydı çekelim
            try:
                seo_record = SeoOptimization.objects.get(design_variation=design)
                self.stdout.write(self.style.SUCCESS("\n📊 --- VERİTABANI KAYIT KONTROLÜ ---"))
                self.stdout.write(f"📝 Yeni Title: {seo_record.generated_title}")
                self.stdout.write(f"🏷️ Yeni Tags: {seo_record.generated_tags}")
                self.stdout.write(f"🆔 SEO Kayıt ID: {seo_record.id}")
            except SeoOptimization.DoesNotExist:
                self.stdout.write(self.style.ERROR("❌ Hata: İşlem başarılı döndü ama veritabanında SeoOptimization kaydı bulunamadı!"))
                
        else:
            self.stdout.write(self.style.ERROR(f"\n❌ SEO Üretim Hatası: {result.get('error')}"))

        self.stdout.write(self.style.SUCCESS("\n🚀 FİNAL TESTİ BİTTİ!"))