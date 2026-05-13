from django.core.management.base import BaseCommand
from manager.detect_crop import crop_and_save_product_design
from manager.models import EtsyProduct
import time

class Command(BaseCommand):
    help = 'Etsy ürünleri için AI tasarım süreçlerini çalıştırır.'

    def add_arguments(self, parser):
        # Tek bir ürün için ID verme seçeneği
        parser.add_argument('--id', type=int, help='Sadece belirli bir IDye sahip ürünü işle')
        
        # Tüm ürünleri işleme seçeneği
        parser.add_argument('--all', action='store_true', help='Veritabanındaki TÜM ürünleri sırayla işle')

    def handle(self, *args, **kwargs):
        target_id = kwargs['id']
        process_all = kwargs['all']

        if target_id:
            # Sadece tek bir ürün
            self.stdout.write(self.style.WARNING(f"🎯 Hedef: ID {target_id} işleniyor..."))
            crop_and_save_product_design(target_id)
            
        elif process_all:
            # Tüm ürünler (DİKKAT: API Kredisi harcar)
            products = EtsyProduct.objects.all().order_by('-id') # En son eklenenden geriye doğru
            count = products.count()
            
            if count == 0:
                self.stdout.write(self.style.ERROR("❌ Veritabanında hiç ürün yok!"))
                return

            self.stdout.write(self.style.SUCCESS(f"🚀 Toplu İşlem Başlatılıyor: {count} adet ürün var."))
            
            for index, product in enumerate(products, 1):
                self.stdout.write("\n" + "-"*40)
                self.stdout.write(f"📦 Ürün [{index}/{count}]: (ID: {product.id}) {product.title[:30]}...")
                
                # Zaten tasarımı varsa atlayabiliriz (İsteğe bağlı, şu an her türlü yapıyor)
                # if product.variations.exists(): print("Zaten var, geçiliyor..."); continue
                
                crop_and_save_product_design(product.id)
                
                # API'yi boğmamak için kısa bir mola
                if index < count:
                    self.stdout.write("💤 2 saniye bekleniyor...")
                    time.sleep(2)
                    
            self.stdout.write(self.style.SUCCESS("\n✅ TÜM ÜRÜNLER İŞLENDİ!"))

        else:
            # Hiçbir şey denmezse varsayılan: SON ÜRÜN
            last_product = EtsyProduct.objects.last()
            if last_product:
                self.stdout.write(self.style.WARNING(f"⚠️ Parametre verilmedi, varsayılan olarak SON ÜRÜN (ID: {last_product.id}) işleniyor..."))
                crop_and_save_product_design(last_product.id)
            else:
                self.stdout.write(self.style.ERROR("❌ Veritabanı boş."))