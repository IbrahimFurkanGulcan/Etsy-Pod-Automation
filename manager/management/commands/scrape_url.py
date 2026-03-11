from django.core.management.base import BaseCommand
from manager.scraper import scrape_etsy_product

class Command(BaseCommand):
    help = 'Belirtilen Etsy URLini analiz eder'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='Analiz edilecek Etsy URL')

    def handle(self, *args, **kwargs):
        url = kwargs['url']
        self.stdout.write(f"Scraping başlıyor: {url}")
        
        try:
            product = scrape_etsy_product(url)
            if product:
                self.stdout.write(self.style.SUCCESS(f"BAŞARILI! Ürün ID: {product.id}"))
                self.stdout.write(f"Başlık: {product.title}")
                self.stdout.write(f"Fiyat: {product.price}")
                self.stdout.write(f"Tagler: {product.tags[:100]}...") # İlk 100 karakter
            else:
                self.stdout.write(self.style.ERROR("Veri çekilemedi."))
        except Exception as e:
             self.stdout.write(self.style.ERROR(f"Hata oluştu: {e}"))