from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.etsy.services.scraper import EtsyScraperService
from apps.etsy.models import EtsyProduct

class Command(BaseCommand):
    help = 'Gerçek bir Etsy URL üzerinden scraper servisini test eder.'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='Test edilecek Etsy ürün URL’si')

    def handle(self, *args, **options):
        url = options['url']
        
        # 1. Test için bir kullanıcı al (Superuser oluşturduğunu varsayıyorum)
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            self.stdout.write(self.style.ERROR("Sistemde superuser bulunamadı! Lütfen önce createsuperuser yapın."))
            return

        self.stdout.write(self.style.SUCCESS(f"🚀 Test başlatılıyor: {url}"))

        # 2. Servisi Çalıştır
        try:
            product = EtsyScraperService.get_or_scrape_product(url, user)
            
            if product:
                self.stdout.write(self.style.SUCCESS(f"✅ Başarılı! Ürün ID: {product.id}"))
                self.stdout.write(f"Başlık: {product.title}")
                self.stdout.write(f"Fiyat: {product.price}")
                self.stdout.write(f"Tag Sayısı: {len(product.tags.split(',')) if product.tags else 0}")
                
                # 3. DB Kontrolü (Doğrulama)
                exists = EtsyProduct.objects.filter(id=product.id).exists()
                if exists:
                    self.stdout.write(self.style.SUCCESS("📂 Veritabanı doğrulaması: Kayıt DB'de mevcut."))
            else:
                self.stdout.write(self.style.ERROR("❌ Ürün kazınamadı (None döndü)."))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"💥 Kritik Hata: {str(e)}"))