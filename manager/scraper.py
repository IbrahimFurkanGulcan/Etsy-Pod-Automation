import re
import time
from playwright.sync_api import sync_playwright
from .models import EtsyProduct

def clean_text(text):
    if not text: return None
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def scrape_etsy_product(raw_url):
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
            args=[
                '--disable-blink-features=AutomationControlled',
                '--window-position=-32000,-32000'
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        try:
            page.goto(url, timeout=90000)
            
            print("⏳ Sayfa kaydırılıyor (Taglerin yüklenmesi için)...")
            # Kademeli kaydırma (Daha insansı, lazy load'u tetikler)
            for i in range(5):
                page.mouse.wheel(0, 1000)
                time.sleep(1)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3) 
            
            print("🕵️ Tagler taranıyor (Multi-Target Modu)...")

            # --- MULTI-TARGET TAG BULUCU ---
            tags_data = page.evaluate("""() => {
                let validTags = [];
                let logs = [];

                // YÖNTEM 1: TextTags (Senin HTML'indeki metin linkleri)
                const textContainer = document.querySelector('div[data-appears-component-name="TextTags"]');
                if (textContainer) {
                    logs.push("✅ TextTags alanı bulundu.");
                    const links = textContainer.querySelectorAll('a');
                    links.forEach(a => {
                        if(a.innerText.length > 2) validTags.push(a.innerText.trim());
                    });
                } else {
                    logs.push("❌ TextTags alanı bulunamadı.");
                }

                // YÖNTEM 2: VisualTags (Resimli yuvarlak tagler)
                const visualContainer = document.querySelector('div[data-appears-component-name="VisualTags"]');
                if (visualContainer) {
                    logs.push("✅ VisualTags alanı bulundu.");
                    // Görsel taglerin metni genelde p etiketindedir
                    const titles = visualContainer.querySelectorAll('p.visual-search-tags-bubbles__title');
                    titles.forEach(p => {
                        if(p.innerText.length > 2) validTags.push(p.innerText.trim());
                    });
                } else {
                    logs.push("❌ VisualTags alanı bulunamadı.");
                }

                // YÖNTEM 3: Genel Link Taraması (Eğer yukarıdakiler boşsa)
                if (validTags.length === 0) {
                    logs.push("⚠️ Özel alanlar boş, genel tarama yapılıyor...");
                    // wt-action-group__item sınıfına sahip VE market/search linki olanlar
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
            
            # Logları yazdır
            print("-" * 30)
            for log in tags_data['logs']:
                print(f"Browser Log: {log}")
            print(f"👀 TOPLAM BULUNAN HAM TAG: {len(tags_data['tags'])}")
            print("-" * 30)
            
            html_content = page.content()

        except Exception as e:
            print(f"❌ Hata: {e}")
            browser.close()
            return None
            
        browser.close()

    print("✅ Veriler filtreleniyor...")

    # --- TAG FİLTRELEME VE TEMİZLİK ---
    tags = set()
    raw_tags = tags_data['tags'] if tags_data else []
    
    # Yasaklı kelimeler (Yorum filtrelerini engellemek için)
    bad_words = ["shipping", "quality", "service", "arrive", "gift", "policies", "returns", "help", "shop"]
    
    for t_text in raw_tags:
        t_clean = clean_text(t_text)
        if not t_clean: continue
        
        # Filtreler
        lower_t = t_clean.lower()
        
        # 1. İçinde sayı varsa at (örn: "Quality (9)")
        if any(char.isdigit() for char in t_clean):
            continue
            
        # 2. Yasaklı kelime varsa at
        if any(bad in lower_t for bad in bad_words):
             continue
             
        # 3. Çok kısaysa at
        if len(t_clean) < 3:
            continue

        tags.add(t_clean) # Orijinal halini koru (Büyük/Küçük harf)

    tags_string = ", ".join(list(tags))
    print(f"🎯 FİNAL TAGLER ({len(tags)} adet): {tags_string}")

    # --- DİĞER VERİLER ---
    title = None
    title_match = re.search(r'<h1[^>]*data-buy-box-listing-title="true"[^>]*>([\s\S]*?)<\/h1>', html_content)
    if title_match: title = clean_text(title_match.group(1))
    
    if not title: # Yedek Title
        meta = re.search(r'<meta property="og:title" content="([^"]+)"', html_content)
        if meta: title = clean_text(meta.group(1)).replace("| Etsy", "")

    price = None
    price_match = re.search(r'<p class="wt-text-title-larger[^>]*>([\s\S]*?)<\/p>', html_content)
    if price_match:
        price = clean_text(price_match.group(1)).replace("Now", "").replace("Price:", "").strip()

    description = None
    desc_match = re.search(r'<p data-product-details-description-text-content=""[^>]*>([\s\S]*?)<\/p>', html_content)
    if desc_match: description = clean_text(desc_match.group(1).replace("<br>", "\n"))

    image_url = None
    zoom_match = re.search(r'data-src-zoom-image="([^"]+)"', html_content)
    if zoom_match: image_url = zoom_match.group(1)
    elif re.search(r'data-carousel-first-image="" src="([^"]+)"', html_content):
        image_url = re.search(r'data-carousel-first-image="" src="([^"]+)"', html_content).group(1)

    # Reviews (Sayı olanı bul)
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

    print(f"💾 Kayıt: {title[:30] if title else 'Başlık Yok'}...")
    
    product, created = EtsyProduct.objects.update_or_create(
        url=url,
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
        }
    )
    return product