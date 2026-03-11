from django.core.management.base import BaseCommand
from manager.models import EtsyProduct
from manager.seo_service import generate_seo_for_product

class Command(BaseCommand):
    help = 'Etsy ürünleri için GPT-4o kullanarak SEO verisi (Başlık, Etiket, Keyword) üretir.'

    def add_arguments(self, parser):
        # Spesifik bir ID veya tüm ürünler için çalıştırma seçenekleri ekliyoruz
        parser.add_argument('--all', action='store_true', help='SEO kaydı olmayan tüm ürünler için çalıştırır.')
        parser.add_argument('--id', type=int, help='Sadece belirli bir ürün ID\'si için çalıştırır.')

    def handle(self, *args, **kwargs):
        run_all = kwargs['all']
        target_id = kwargs['id']

        # Hangi ürünlerin işleneceğini seç
        if target_id:
            products = EtsyProduct.objects.filter(id=target_id)
        elif run_all:
            # SEO kaydı olmayan tüm ürünleri bul
            products = EtsyProduct.objects.filter(seo_optimization__isnull=True)
        else:
            # Sadece en son eklenen ürünü al (Hızlı test için)
            last_product = EtsyProduct.objects.last()
            products = [last_product] if last_product else []

        if not products:
            self.stdout.write(self.style.WARNING("❌ İşlem yapılacak ürün bulunamadı."))
            return

        for product in products:
            self.stdout.write(self.style.SUCCESS(f"\n🚀 SEO Üretimi Başlıyor: [ID: {product.id}] {product.title[:40]}..."))
            
            # Motoru (seo_service.py) çalıştır
            seo_record = generate_seo_for_product(product.id, niche="Graphic T-Shirt")
            
            if seo_record:
                self.stdout.write(self.style.SUCCESS(f"✅ SEO Başarıyla Üretildi!"))
                self.stdout.write(f"🔥 Başlık: {seo_record.generated_title}")
                self.stdout.write(f"🏷️ Etiketler: {seo_record.generated_tags}")
            else:
                self.stdout.write(self.style.ERROR(f"❌ SEO üretimi başarısız oldu: [ID: {product.id}]"))