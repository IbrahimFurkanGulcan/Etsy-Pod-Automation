from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import patch

from apps.etsy.models import EtsyProduct
from apps.etsy.services.scraper import EtsyScraperService

class EtsyScraperServiceTest(TestCase):
    
    def setUp(self):
        """Test başlamadan önce çalışır. Test kullanıcımızı hazırlıyoruz."""
        self.user = User.objects.create_user(username='testuser', password='password123')
        
        # Test için veritabanına sahte (dummy) bir ürün ekliyoruz
        self.dummy_product = EtsyProduct.objects.create(
            user=self.user,
            url="https://www.etsy.com/listing/123456789/test-product",
            title="Test Tişört",
            price="15.00"
        )

    def test_clean_text(self):
        """Metin temizleme (clean_text) fonksiyonu doğru çalışıyor mu?"""
        dirty_html = "<h1>Bu bir   <strong>test</strong>    başlığıdır.</h1>"
        cleaned = EtsyScraperService.clean_text(dirty_html)
        self.assertEqual(cleaned, "Bu bir test başlığıdır.")

    def test_get_product_from_db_by_id(self):
        """
        Akıllı Arama Testi: 
        URL girildiğinde ID'yi bulup doğrudan veritabanından çekiyor mu?
        (Scraper HİÇ çalışmamalı)
        """
        test_url = "https://www.etsy.com/listing/123456789/baska-bir-link-uzantisi"
        
        # Servisi çağır
        product = EtsyScraperService.get_or_scrape_product(test_url, self.user)
        
        # Dönen ürünün bizim dummy ürün olduğundan emin ol
        self.assertIsNotNone(product)
        self.assertEqual(product.title, "Test Tişört")
        self.assertEqual(product.id, self.dummy_product.id)

    @patch('apps.etsy.services.scraper.EtsyScraperService._execute_playwright_scrape')
    def test_scrape_new_product(self, mock_playwright):
        """
        Yeni Ürün Testi:
        Veritabanında olmayan bir URL girildiğinde Scraper tetikleniyor mu?
        """
        # Playwright'ın gerçekte çalışmasını engelliyoruz (Mockluyoruz)
        # Ve sanki çalışmış da bize sahte bir ürün dönmüş gibi davranmasını söylüyoruz.
        mock_new_product = EtsyProduct(url="https://www.etsy.com/listing/999/yeni", title="Yeni Kazınmış", user=self.user)
        mock_playwright.return_value = mock_new_product

        new_url = "https://www.etsy.com/listing/999/yeni"
        
        product = EtsyScraperService.get_or_scrape_product(new_url, self.user)
        
        # 1. Playwright fonksiyonu gerçekten çağrılmış mı?
        mock_playwright.assert_called_once_with(new_url)
        
        # 2. Ürün doğru dönmüş mü ve kullanıcıya zimmetlenmiş mi?
        self.assertIsNotNone(product)
        self.assertEqual(product.title, "Yeni Kazınmış")
        self.assertEqual(product.user, self.user)