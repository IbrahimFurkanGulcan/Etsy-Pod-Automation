import re
import time
from playwright.sync_api import sync_playwright

# Modüler Yapı İçe Aktarmaları
from apps.etsy.models import EtsyProduct
from apps.common.services.db_helpers import DatabaseService

class EtsyScraperService:
    """
    Etsy ürün verilerini DB'den getirme veya web'den kazıma servisi.
    Tüm iş mantığı (Business Logic) buradadır.
    """

    @staticmethod
    def clean_text(text):
        if not text: return None
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @classmethod
    def get_or_scrape_product(cls, url, user, force_rescrape=False): # PARAMETRE EKLENDİ
        url = url.strip()
        product = None
        
        # 1. ZORUNLU KAZIMA İSTENMEDİYSE DB'DE ARA
        if not force_rescrape:
            match = re.search(r'listing/(\d+)', url)
            if match:
                listing_id = match.group(1)
                product = DatabaseService.find_first_by_filter(EtsyProduct, url__contains=f"listing/{listing_id}", user=user)
            else:
                product = DatabaseService.find_first_by_filter(EtsyProduct, url=url, user=user)

            if product:
                print(f"⚡ BAŞARILI: {product.id} ID'li ürün veritabanından çekildi!")
                return product

        # 2. ÜRÜN YOKSA VEYA 'ZORLA GÜNCELLE' DENİLDİYSE SCRAPER ÇALIŞIR
        print("🐌 DB Atlandı. Scraper çalıştırılıyor...")
        product = cls._execute_playwright_scrape(url, user)

        if product:
            product.user = user
            product.save()
            
        return product
        
    @classmethod
    def _execute_playwright_scrape(cls, raw_url, user):
        """
        Sadece Playwright ile kazıma yapar ve EtsyProduct olarak kaydeder.
        Dışarıdan doğrudan çağrılmaması için private (_) olarak tanımlanmıştır.
        """
        if "?" in raw_url:
            url = raw_url.split("?")[0]
        else:
            url = raw_url
        url = url.strip()
        if not url.startswith("http"):
            url = "https://" + url
            
        print(f"🌍 URL: {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled', '--window-position=-32000,-32000']
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            try:
                page.goto(url, timeout=90000)
                
                # Taglerin yüklenmesi için sayfa kaydırma
                print("⏳ Sayfa kaydırılıyor...")
                for i in range(5):
                    page.mouse.wheel(0, 1000)
                    time.sleep(1)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3) 
                
                print("🕵️ Tagler taranıyor...")
                tags_data = page.evaluate("""() => {
                    let validTags = [];
                    let logs = [];

                    const textContainer = document.querySelector('div[data-appears-component-name="TextTags"]');
                    if (textContainer) {
                        const links = textContainer.querySelectorAll('a');
                        links.forEach(a => { if(a.innerText.length > 2) validTags.push(a.innerText.trim()); });
                    }

                    const visualContainer = document.querySelector('div[data-appears-component-name="VisualTags"]');
                    if (visualContainer) {
                        const titles = visualContainer.querySelectorAll('p.visual-search-tags-bubbles__title');
                        titles.forEach(p => { if(p.innerText.length > 2) validTags.push(p.innerText.trim()); });
                    }

                    if (validTags.length === 0) {
                        const buttons = document.querySelectorAll('a.wt-action-group__item');
                        buttons.forEach(a => {
                            const href = a.getAttribute('href') || '';
                            if (href.includes('/market/') || href.includes('/search?q=')) {
                                validTags.push(a.innerText.trim());
                            }
                        });
                    }
                    return {tags: validTags, logs: logs};
                }""")
                
                html_content = page.content()

            except Exception as e:
                print(f"❌ Hata: {e}")
                browser.close()
                return None
                
            browser.close()

        # Verileri Filtreleme
        tags = set()
        raw_tags = tags_data['tags'] if tags_data else []
        bad_words = ["shipping", "quality", "service", "arrive", "gift", "policies", "returns", "help", "shop"]
        
        for t_text in raw_tags:
            t_clean = cls.clean_text(t_text)
            if not t_clean: continue
            
            lower_t = t_clean.lower()
            if any(char.isdigit() for char in t_clean): continue
            if any(bad in lower_t for bad in bad_words): continue
            if len(t_clean) < 3: continue
            tags.add(t_clean)

        tags_string = ", ".join(list(tags))

        # Diğer Verileri Çıkarma
        title = None
        title_match = re.search(r'<h1[^>]*data-buy-box-listing-title="true"[^>]*>([\s\S]*?)<\/h1>', html_content)
        if title_match: title = cls.clean_text(title_match.group(1))
        
        if not title: 
            meta = re.search(r'<meta property="og:title" content="([^"]+)"', html_content)
            if meta: title = cls.clean_text(meta.group(1)).replace("| Etsy", "")

        price = None
        price_match = re.search(r'<p class="wt-text-title-larger[^>]*>([\s\S]*?)<\/p>', html_content)
        if price_match: price = cls.clean_text(price_match.group(1)).replace("Now", "").replace("Price:", "").strip()

        description = None
        desc_match = re.search(r'<p data-product-details-description-text-content=""[^>]*>([\s\S]*?)<\/p>', html_content)
        if desc_match: description = cls.clean_text(desc_match.group(1).replace("<br>", "\n"))

        image_url = None
        zoom_match = re.search(r'data-src-zoom-image="([^"]+)"', html_content)
        if zoom_match: image_url = zoom_match.group(1)
        elif re.search(r'data-carousel-first-image="" src="([^"]+)"', html_content):
            image_url = re.search(r'data-carousel-first-image="" src="([^"]+)"', html_content).group(1)

        item_review_count = "0"
        html_rev = re.search(r'Reviews for this item\s*\((\d+)\)', html_content, re.IGNORECASE)
        if html_rev: item_review_count = html_rev.group(1)

        shop_review_count = "0"
        shop_rev = re.search(r'>([\d,]+)\s*shop reviews<', html_content)
        if shop_rev: shop_review_count = shop_rev.group(1).replace(",", "")

        views = "0"
        v_match = re.search(r'(\d+)\s*people have this in their', html_content)
        if v_match: views = v_match.group(1)
        
        favorites = "0"
        f_match = re.search(r'Favorites\s*\((\d+)\)', html_content)
        if not f_match: f_match = re.search(r'has ([\d,]+) favorites', html_content)
        if f_match: favorites = f_match.group(1).replace(",", "")
        
        # Veritabanına Kaydetme
        product, created = DatabaseService.update_or_create_with_log(
            model=EtsyProduct,
            defaults={
                'title': title,
                'price': price,
                'description': description,
                'image_url': image_url,
                'tags': tags_string,
                'favorites_count': favorites,
                'views': views,
                'item_review_count': item_review_count,
                'shop_review_count': shop_review_count,
            },
            url=url, # Arama kriteri kwargs olarak dışarıda kalır
            user=user
        )
        return product