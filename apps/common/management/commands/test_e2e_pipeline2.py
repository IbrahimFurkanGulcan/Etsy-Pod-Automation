import os
import time
import base64
from dotenv import load_dotenv
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

# Modeller
from apps.products.models import ManualUpload

# Servisler
from apps.image_processor.services.mockup_template import MockupTemplateService
from apps.ai.services.generations.image_analysis import VisionAnalysisService
from apps.ai.services.generations.seo import SeoEngineService
from apps.ai.services.config.system_prompts import DEFAULT_SYSTEM_PROMPTS
from apps.image_processor.services.mockup_processor import MockupEngineService
from apps.common.services.export import ProjectExportService

load_dotenv()

class Command(BaseCommand):
    help = 'Pipeline 2 (Manual Upload): Şablon Yükleme -> Vision AI -> SEO -> Mockup -> Export Uçtan Uca Testi'

    def add_arguments(self, parser):
        parser.add_argument('--upload_id', type=int, help='Analiz ve mockup yapılacak ManualUpload ID')
        parser.add_argument('--mockup_dir', type=str, help='İçinde şablon (.jpg/.png) bulunan klasörün yolu')

    def handle(self, *args, **options):
        upload_id = options['upload_id']
        mockup_dir = options['mockup_dir']
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("REPLICATE_API_TOKEN")

        if not upload_id or not mockup_dir:
            self.stdout.write(self.style.ERROR("❌ Hata: --upload_id ve --mockup_dir parametreleri zorunludur!"))
            return

        user = User.objects.first()
        upload = ManualUpload.objects.get(id=upload_id)

        self.stdout.write(self.style.SUCCESS(f"🚀 UÇTAN UCA TEST BAŞLIYOR (User: {user.username})"))
        self.stdout.write(self.style.SUCCESS("-" * 50))

        # ==========================================================
        # 1. ŞABLONLARI YÜKLEME (Klasörden okuyup MockupTemplateService'e verme)
        # ==========================================================
        self.stdout.write(self.style.WARNING("⏳ ADIM 1: Şablonlar Klasörden Okunup DB'ye Kaydediliyor..."))
        
        mockups_data = []
        valid_exts = ('.png', '.jpg', '.jpeg')
        
        for idx, filename in enumerate(os.listdir(mockup_dir)):
            if filename.lower().endswith(valid_exts):
                file_path = os.path.join(mockup_dir, filename)
                with open(file_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                
                ext = filename.split('.')[-1].lower()
                ext = 'jpeg' if ext == 'jpg' else ext
                base64_url = f"data:image/{ext};base64,{encoded_string}"

                # Test için sahte bir göğüs baskısı koordinatı
                mock_coords = {
                    "left": 250, "top": 200, "width": 300, "height": 400, 
                    "scaleX": 1.0, "scaleY": 1.0, "angle": 0, "canvas_scale": 1.0
                }

                mockups_data.append({
                    "id": f"mockup_test_{idx}", 
                    "name": f"Template_{filename}", 
                    "url": base64_url, 
                    "coordinates": mock_coords
                })

        if not mockups_data:
            self.stdout.write(self.style.ERROR("❌ Şablon klasöründe resim bulunamadı."))
            return

        # Template servisini çağır
        template_res = MockupTemplateService.save_collection(user=user, mockups_data=mockups_data, group_name="E2E Test Şablonları")
        group_id = template_res['group_id']
        
        # Eklenen şablonların ID'lerini bul
        from apps.image_processor.models import MockupGroup
        mockup_group = MockupGroup.objects.get(id=group_id)
        mockup_item_ids = list(mockup_group.items.values_list('id', flat=True))
        
        self.stdout.write(self.style.SUCCESS(f"✅ {len(mockup_item_ids)} Şablon DB'ye Kaydedildi (Grup ID: {group_id})\n"))

        # ==========================================================
        # 2. VISION AI VE SEO ÜRETİMİ
        # ==========================================================
        self.stdout.write(self.style.WARNING("⏳ ADIM 2: Vision AI ve SEO Analizi Başlıyor..."))
        
        vision_res = VisionAnalysisService.analyze_design(manual_upload=upload, api_key=api_key, force_recreate=True)
        if not vision_res.get('success'):
            self.stdout.write(self.style.ERROR("❌ Vision AI Hatası!"))
            return
            
        seo_res = SeoEngineService.generate_seo_for_design(
            model_id='gpt-4o', api_key=api_key,
            title_prompt=DEFAULT_SYSTEM_PROMPTS.get("gpt-4o_title"),
            tags_prompt=DEFAULT_SYSTEM_PROMPTS.get("gpt-4o_tag"),
            manual_upload=upload
        )
        self.stdout.write(self.style.SUCCESS(f"✅ SEO Üretildi (Title: {seo_res.get('title')[:30]}...)\n"))

        # ==========================================================
        # 3. MOCKUP MOTORUNU ÇALIŞTIRMA (Tasarımı Şablonlara Giydir)
        # ==========================================================
        self.stdout.write(self.style.WARNING("⏳ ADIM 3: Mockup Motoru ile Görüntüler Giydiriliyor..."))
        
        start_m_time = time.time()
        # Yeni yazdığımız Upload paralel motorunu çağırıyoruz
        m_results = MockupEngineService.generate_upload_batch_parallel(
            upload_ids=[upload.id], 
            mockup_item_ids=mockup_item_ids, 
            force_recreate=True
        )
        self.stdout.write(self.style.SUCCESS(f"✅ Mockuplar Üretildi ({time.time() - start_m_time:.2f}s)\n"))

        # ==========================================================
        # 4. EXPORT SERVİSİ İLE ZIP OLUŞTURMA VE DİSKE KAYDETME
        # ==========================================================
        self.stdout.write(self.style.WARNING("⏳ ADIM 4: Veriler ZIP Formatında Paketleniyor..."))
        
        export_res = ProjectExportService.export_pipeline2_batch(user=user, upload_ids=[upload.id])
        
        if not export_res["success"]:
            self.stdout.write(self.style.ERROR(f"❌ Export Hatası: {export_res['error']}"))
            return

        # RAM'deki ZIP dosyasını fiziksel olarak proje ana dizinine kaydet
        http_response = export_res["response"]
        zip_filename = http_response['Content-Disposition'].split('filename=')[1].strip('"')
        export_path = os.path.join(settings.BASE_DIR, zip_filename)

        with open(export_path, 'wb') as f:
            f.write(http_response.content)

        self.stdout.write(self.style.SUCCESS(f"🎉 ZİNCİR TAMAMLANDI!"))
        self.stdout.write(self.style.SUCCESS(f"📦 İndirilen ZIP Dosyası: {export_path}"))