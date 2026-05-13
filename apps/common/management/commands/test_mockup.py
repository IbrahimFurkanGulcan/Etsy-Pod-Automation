# manager/management/commands/test_mockup.py

import os
from django.core.management.base import BaseCommand
from manager.models import MockupGroup
from manager.mockup_processor import process_single_mockup
from django.conf import settings

class Command(BaseCommand):
    help = "'test' grubundaki TÜM mockupları ve belirtilen tasarımı kullanarak Sandviç Modeli algoritmasını test eder."

    def handle(self, *args, **kwargs):
        self.stdout.write("🔍 Veritabanından 'test' grubu aranıyor...")

        # 1. 'test' adındaki grubu ve içindeki TÜM ayarlanmış mockupları bul
        try:
            test_group = MockupGroup.objects.get(name='test')
            
            # DİKKAT: .last() sildik, alanı çizilmiş tüm resimleri bir liste (QuerySet) olarak alıyoruz
            mockups = test_group.items.filter(placement_data__isnull=False).exclude(placement_data={})
            
        except MockupGroup.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ HATA: 'test' adında bir Mockup Koleksiyonu bulunamadı!"))
            return

        if not mockups.exists():
            self.stdout.write(self.style.ERROR("❌ HATA: 'test' grubunda koordinatı belirlenmiş hiçbir resim yok!"))
            return

        # 2. Tasarım yolunu belirle
        design_path = r"D:\EtsyAIProject\media\designs\transparent\nobg_4_9.png"

        if not os.path.exists(design_path):
            self.stdout.write(self.style.ERROR(f"❌ HATA: Tasarım dosyası bulunamadı:\n{design_path}"))
            return

        self.stdout.write(self.style.SUCCESS(f"✅ 'test' grubunda {mockups.count()} adet işlenebilir mockup bulundu."))
        
        # Çıktı klasörünü ayarla
        output_dir = os.path.join(settings.MEDIA_ROOT if hasattr(settings, 'MEDIA_ROOT') else 'media', 'test_output')
        os.makedirs(output_dir, exist_ok=True)

        success_count = 0
        
        # 3. TÜM MOCKUPLAR İÇİN DÖNGÜYÜ BAŞLAT
        for index, mockup in enumerate(mockups, 1):
            self.stdout.write(self.style.WARNING(f"\n⚙️ [{index}/{mockups.count()}] İşleniyor: {mockup.name} ..."))
            
            mockup_path = mockup.mockup_image.path
            coords = mockup.placement_data
            
            # Her bir çıktıya ID'sini veriyoruz ki üst üste binmesinler
            output_path = os.path.join(output_dir, f"db_test_result_{mockup.id}.png")

            try:
                # Görüntü işleme motorunu çağır
                process_single_mockup(
                    mockup_path=mockup_path, 
                    design_path=design_path, 
                    coords=coords, 
                    output_path=output_path
                )
                self.stdout.write(self.style.SUCCESS(f"  └─ 🎉 Başarılı! Çıktı: {output_path}"))
                success_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  └─ ❌ HATA ({mockup.name}): {e}"))

        # Final Raporu
        self.stdout.write(self.style.SUCCESS(f"\n✅ TEST TAMAMLANDI! {success_count}/{mockups.count()} görsel başarıyla işlendi."))