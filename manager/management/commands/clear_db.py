from django.core.management.base import BaseCommand
from manager.models import EtsyProduct

class Command(BaseCommand):
    help = 'Tüm ürünleri veritabanından siler'

    def handle(self, *args, **kwargs):
        count = EtsyProduct.objects.count()
        EtsyProduct.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'🧹 Temizlik tamamlandı! {count} adet ürün silindi.'))