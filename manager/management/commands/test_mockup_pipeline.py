import os
import time
import base64
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.ai.models import DesignVariation
from apps.image_processor.models import MockupGroup, MockupItem

from apps.image_processor.services.mockup_template import MockupTemplateService
from apps.image_processor.services.mockup_processor import MockupEngineService

class Command(BaseCommand):
    help = 'Şablon yükleme ve Mockup Motorunu test eder.'

    def add_arguments(self, parser):
        parser.add_argument('--design_id', type=int, help='Giydirilecek Tasarımın (DesignVariation) ID numarası')
        parser.add_argument('--image_path', type=str, help='Şablon olarak kullanılacak boş tişört/ürün resminin yolu')

    def handle(self, *args, **options):
        design_id = options['design_id']
        image_path = options['image_path']

        if not design_id or not image_path:
            self.stdout.write(self.style.ERROR("❌ Hata: --design_id ve --image_path parametrelerini girmelisiniz!"))
            return

        user = User.objects.first() 
        if not user:
            self.stdout.write(self.style.ERROR("❌ Hata: Sistemde kayıtlı hiçbir kullanıcı yok."))
            return

        # ==========================================================
        # 1. KATI KONTROL: SADECE ARKA PLANI SİLİNMİŞ TASARIM KABUL ET
        # ==========================================================
        try:
            design = DesignVariation.objects.get(id=design_id)
            
            # Senin dediğin gibi, no_bg_image yoksa işlemi direkt reddediyoruz
            if not design.no_bg_image or not design.no_bg_image.name:
                self.stdout.write(self.style.ERROR(f"❌ Hata: {design_id} numaralı tasarımın arka planı silinmemiş (no_bg_image boş)!"))
                return
                
            self.stdout.write(self.style.SUCCESS(f"✅ Kullanılacak Tasarım: ✂️ {design.no_bg_image.name}"))
            
        except DesignVariation.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Hata: {design_id} ID'li tasarım bulunamadı."))
            return

        if not os.path.exists(image_path):
            self.stdout.write(self.style.ERROR(f"❌ Hata: Şablon resmi bulunamadı: {image_path}"))
            return

        self.stdout.write(self.style.SUCCESS(f"👨‍💻 Kullanıcı: {user.username}"))
        
        # ==========================================================
        # AŞAMA 1: ŞABLONU SİSTEME YÜKLEME (Base64 ve Sahte Koordinat)
        # ==========================================================
        self.stdout.write(self.style.WARNING("\n⏳ AŞAMA 1: Şablon Veritabanına Kaydediliyor..."))
        
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        ext = image_path.split('.')[-1].lower()
        if ext == 'jpg': ext = 'jpeg'
        base64_url = f"data:image/{ext};base64,{encoded_string}"

        dummy_coordinates = {
            "left": 300, 
            "top": 250, 
            "width": 400, 
            "height": 500, 
            "scaleX": 1.0, 
            "scaleY": 1.0, 
            "angle": 0, 
            "canvas_scale": 1.0,
            "is_circle": False
        }

        mockups_data = [{
            "id": "mockup_test123", 
            # DÜZELTİLDİ: Türkçe karakter sorunu çıkaran uydurma ismi İngilizce ve güvenli hale getirdim
            "name": "Test_Mockup_Template", 
            "url": base64_url,
            "coordinates": dummy_coordinates
        }]

        template_result = MockupTemplateService.save_collection(
            user=user, 
            mockups_data=mockups_data, 
            group_name="Terminal Test Koleksiyonu"
        )
        
        group_id = template_result['group_id']
        group = MockupGroup.objects.get(id=group_id)
        saved_item = group.items.last() 
        
        self.stdout.write(self.style.SUCCESS(f"✅ Şablon Kaydedildi! (Grup ID: {group_id}, Şablon ID: {saved_item.id})"))

        # ==========================================================
        # AŞAMA 2: TASARIMI ŞABLONA GİYDİRME
        # ==========================================================
        self.stdout.write(self.style.WARNING("\n⏳ AŞAMA 2: Tasarım Şablona Giydiriliyor..."))
        
        start_time = time.time()
        
        engine_results = MockupEngineService.generate_batch_parallel(
            design_ids=[design.id],
            mockup_item_ids=[saved_item.id],
            force_recreate=True 
        )

        for res in engine_results:
            if res.get('success'):
                self.stdout.write(self.style.SUCCESS(f"\n🎉 MOCKUP BAŞARIYLA ÜRETİLDİ! (Süre: {time.time() - start_time:.2f}s)"))
                self.stdout.write(self.style.SUCCESS(f"🔗 Sonuç URL: {res['url']}"))
            else:
                self.stdout.write(self.style.ERROR(f"\n❌ Mockup Üretim Hatası: {res.get('error')}"))

        self.stdout.write(self.style.SUCCESS("\n🚀 BÜTÜN TESTLER TAMAMLANDI!"))