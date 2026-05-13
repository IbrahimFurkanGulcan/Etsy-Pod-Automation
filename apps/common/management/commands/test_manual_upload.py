import os
import time
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.products.services.manual_upload import ManualUploadService

class Command(BaseCommand):
    help = 'Yerel bir klasördeki resimleri sisteme manuel yükleme (ManualUpload) olarak ekler.'

    def add_arguments(self, parser):
        parser.add_argument('--dir_path', type=str, help='Yüklenecek resimlerin bulunduğu klasörün tam yolu')

    def handle(self, *args, **options):
        dir_path = options['dir_path']

        if not dir_path:
            self.stdout.write(self.style.ERROR("❌ Hata: --dir_path parametresini girmelisiniz!"))
            return

        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            self.stdout.write(self.style.ERROR(f"❌ Hata: Belirtilen klasör bulunamadı: {dir_path}"))
            return

        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR("❌ Hata: Sistemde kayıtlı hiçbir kullanıcı yok."))
            return

        self.stdout.write(self.style.SUCCESS(f"👨‍💻 Kullanıcı: {user.username}"))
        self.stdout.write(self.style.WARNING(f"📂 Klasör Taranıyor: {dir_path}"))

        # 1. KLASÖRDEKİ RESİMLERİ BUL VE UPLOADED_FILE OBJELERİNE ÇEVİR
        valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
        files_to_upload = []

        # Klasördeki dosyaları oku
        for filename in os.listdir(dir_path):
            if filename.lower().endswith(valid_extensions):
                file_path = os.path.join(dir_path, filename)
                
                # Dosyanın içeriğini (byte'larını) oku
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                    
                # Django'nun arayüzden geliyormuş gibi anlaması için SimpleUploadedFile kullanıyoruz
                uploaded_file = SimpleUploadedFile(
                    name=filename,
                    content=file_content,
                    content_type=f"image/{filename.split('.')[-1].lower()}"
                )
                files_to_upload.append(uploaded_file)

        if not files_to_upload:
            self.stdout.write(self.style.ERROR("❌ Hata: Klasörde uygun formatta (.png, .jpg, .webp) resim bulunamadı."))
            return

        self.stdout.write(self.style.SUCCESS(f"📦 {len(files_to_upload)} adet resim bulundu. Yükleme başlıyor...\n"))

        # ==========================================================
        # 2. SERVİSİ TETİKLE
        # ==========================================================
        start_time = time.time()
        
        result = ManualUploadService.process_uploads(
            user=user,
            files=files_to_upload,
            group_name="Terminal Toplu Yükleme Seti"
        )

        # ==========================================================
        # 3. SONUÇLARI İNCELE
        # ==========================================================
        if result["success"]:
            self.stdout.write(self.style.SUCCESS(f"✅ Yükleme Tamamlandı! (Süre: {time.time() - start_time:.2f}s)"))
            self.stdout.write(self.style.WARNING(f"\n📊 ÖZET:"))
            self.stdout.write(f"   📁 Grup ID: {result['group_id']}")
            self.stdout.write(f"   🆕 Yeni Yüklenen: {result['saved_count']} adet")
            self.stdout.write(f"   ♻️ Cache'den Gelen: {result['cached_count']} adet\n")

            self.stdout.write(self.style.SUCCESS("🔍 Detaylı Dosya Listesi:"))
            for item in result['items']:
                status = "♻️ CACHED" if item['cached'] else "🆕 YENİ"
                self.stdout.write(f"   - [{status}] ID: {item['id']} | Dosya: {item['name']}")
        else:
            self.stdout.write(self.style.ERROR(f"❌ Yükleme Hatası: {result.get('error')}"))

        self.stdout.write(self.style.SUCCESS("\n🚀 TEST BİTTİ!"))