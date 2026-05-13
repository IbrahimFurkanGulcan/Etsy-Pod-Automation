# 🚀 Etsy AI Design & POD Automation (SaaS)

Etsy'de çok satan (Best-Seller) Print-on-Demand (POD) ürünlerini analiz ederek, üzerlerindeki tasarımları tespit eden ve yapay zeka (AI) destekli üretim modelleriyle saniyeler içinde benzersiz yeni varyasyonlar, profesyonel mockuplar ve SEO uyumlu metinler üreten hepsi bir arada otomasyon aracı.

Çift yönlü (Dual) Pipeline mimarisi sayesinde ister yapay zekanın sıfırdan ürettiği tasarımları, isterseniz kendi kütüphanenizdeki mevcut görselleri saniyeler içinde satışa hazır hale getirebilirsiniz.

---

# 🌟 NEDEN BU PROJE?

Etsy'de tişört/sweatshirt alanında mağaza açanların en büyük sıkıntısı çok fazla rakip arasından mağazalarını ön plana çıkarmak ve algoritmaya oturtmaktır. Bunun ana yöntemlerinden biri de yeterli sayıda günlük listing yüklemektir. Tasarım arştırması yapmak, bulunan tasarımın benzerini yapay zekaya tek tek ürettirmek veya belirli platformlardan benzerlerini bulmak baştan yapmak, mockuplamak seo için tag-title araştırmak yeterli sayıda listing oluşturmaya çalışırken çok fazla zaman alır.

Bu proje ile tşört katagorisinde iki farklı pipeline hizmeti sunarak özellikle yeni açılan mağazaların algoritmaya girebilmesi için zaman alan listing hazırlama işini hızlandırıyoruz.

Bu proje, Grounding DINO kullanarak tasarımı önce rakip kıyafetten izole eder (kırpar), ardından AI modellerini sadece bu saf tasarım üzerinden besleyerek doğrudan baskıya hazır (arka planı silinmiş) sonuçlar verir.

Analizden üretime, mockuptan SEO'ya kadar tüm POD süreçlerini tek bir merkezde toplar.

---

# ✨ SİSTEM MİMARİSİ VE ÖZELLİKLER

## 🔄 Dual-Pipeline Mimarisi

### Pipeline 1 — AI Generative & Scraper

- Etsy URL'si üzerinden Playwright ile rakip ürün analizi yapar.
- Görüntülenme, favori, başlık gibi verileri toplar.
- Ürün üzerindeki tasarımı izole eder.
- Seçilen AI modelleri (Flux, SD vb.) ile yeni varyasyonlar üretir.
- Üretilen tasarımların arka planları otomatik olarak silinir.
- Seçilen şablonlara göre otomatik mockuplama yapar.
- Orijinal tasarımda kullanılan tag-title ı referans alarak seo üretir.
- Tüm üretimi transparan tasarım-seo -texti ve mockuplanmış görseller klasörü içeren bir klasör şeklinde indirir.

### Pipeline 2 — Batch Processing & Mockup Orchestration

- Manuel olarak tasarım yüklenmesine olanak sağlar.
- Tasarım kütüphanesindeki şeffaf PNG'leri veya P1’den transfer edilen görselleri toplu işler.
- Seçilen mockup şablonlarıyla eşleştirir.
- Tek tıkla yüzlerce profesyonel mockup üretir.
- Transparak görselleri vision-ai ile analiz eder.
- Vision-ai analiz çıktısını referans alarak seo üretir.
- Tüm üretimi transparan tasarım-seo -texti ve mockuplanmış görseller klasörü içeren bir klasör şeklinde indirir.

---

# 🗂️ GELİŞMİŞ MODÜL YÖNETİMİ

## 🎨 Tasarım Kütüphanesi (Asset Library)

- Üretilen veya manuel yüklenen tüm tasarımların merkezi depolama alanı.
- Tasarımlar tek tıkla pipeline'lara yönlendirilebilir.

## 🖼️ Mockup Şablon Merkezi

- Boş mockup görsellerinizi sisteme yükleyip yönetebilirsiniz.
- Dinamik şablon havuzu desteği sunar.

## 🕘 Geçmiş Analizler (History)

- Daha önce analiz edilen Etsy linkleri ve yapılan üretimler saklanır.
- Daha önce manuel olarak yüklenen tasarımlardan yapılan üretimler saklanır.
- Rakip verileri ve üretilen tasarımlar tek tıkla geri çağrılabilir.

## ⚙️ Dinamik Ayarlar (Config)

Arayüz üzerinden:

- Replicate API Key
- Varsayılan sistem promptları
- Aktif AI modelleri

kod yazmadan yönetilebilir.

---

# 🧠 YAPAY ZEKA DESTEKLİ İŞLEMLER

## ✂️ Akıllı Arka Plan Silme

bria-rmbg modeli sayesinde tüm tasarımlar otomatik olarak temizlenir ve şeffaf PNG formatına dönüştürülür.

## 🏷️ AI SEO Motoru

GPT-4o destekli SEO sistemi:

- Rakip analizlerini işler
- Yüksek aranma hacimli başlıklar üretir
- SEO uyumlu İngilizce etiketler oluşturur

---

# 📥 TEK TIKLA EXPORT

Üretilen:

- Şeffaf tasarımlar
- Mockuplar
- SEO metinleri

otomatik klasörlenmiş ZIP arşivi olarak indirilebilir.

---

# 🎥 SİSTEM NASIL ÇALIŞIYOR?

## 1️⃣ Akıllı Tasarım Üretimi ve İzolasyon (Pipeline 1)

- Grounding DINO ile rakip tasarım tespiti
- Tasarımın kırpılması
- AI modelleriyle yeni varyasyon üretimi

## 2️⃣ Akıllı Transfer ve Arka Plan Silme

- Yapay zeka çıktılarının arka planları otomatik silinir
- Görseller toplu üretim hattına aktarılır

## 3️⃣ Toplu Mockup ve SEO Üretimi (Pipeline 1-2)

- Tasarımlar seçilen şablonlara yerleştirilir
- SEO verileri otomatik oluşturulur
- Sonuçlar ZIP olarak dışa aktarılır

---

# 🛠️ KULLANILAN TEKNOLOJİLER

## Backend

- Python
- Django

## Frontend

- Vanilla JS
- Fetch API
- Tailwind CSS
- HTML5

## Yapay Zeka Entegrasyonları

- OpenAI (GPT-4o Vision & SEO)
- Replicate
- Grounding DINO
- Flux
- Seadream 4.5
- Nanobanana

## Veri Yönetimi

- SQLite
- MD5 Hash tabanlı dosya eşleştirme

## Scraping

- Playwright

---

# 🚀 KURULUM VE ÇALIŞTIRMA (GETTING STARTED)

Python 3.10 veya üzeri gereklidir.

> Kurulum sırasında **"Add Python to PATH"** seçeneğinin işaretli olduğundan emin olun.

---

## ⚡ Yöntem 1 — Akıllı Başlatıcı (Windows Kullanıcıları İçin)

Klasör içerisindeki:

```bash
Etsy_AI_Baslat.bat
```

dosyasına çift tıklayın.

### 💡 Otomatik Olarak Yapılan İşlemler

- Virtual environment oluşturma
- Gereksinimlerin kurulması
- Playwright kurulumu
- Veritabanı hazırlığı
- Sunucunun başlatılması
- Tarayıcı açılması

Sistem otomatik olarak:

```txt
http://127.0.0.1:8000
```

adresinde çalışacaktır.

---

## 🧑‍💻 Yöntem 2 — Manuel Kurulum

### 1️⃣ Repoyu Klonlayın

```bash
git clone https://github.com/IbrahimFurkanGulcan/Etsy-Pod-Automation.git
cd Etsy-Pod-Automation
```

### 2️⃣ Sanal Ortam Oluşturun

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```


---

### 3️⃣ Gereksinimleri Kurun

```bash
pip install -r requirements.txt

```

---

### 4️⃣ Çevresel Değişkenleri Ayarlayın

`.env.example` dosyasını `.env` olarak yeniden adlandırın.

```env
SECRET_KEY=your_django_secret_key_here
```

> AI API anahtarları arayüzdeki Ayarlar panelinden yönetilmektedir.

---

### 5️⃣ Veritabanını Hazırlayın

```bash
python manage.py makemigrations
python manage.py migrate
```

---

### 6️⃣ Sunucuyu Başlatın

```bash
python manage.py runserver
```

Tarayıcıdan:

```txt
http://127.0.0.1:8000
```

adresine giderek sistemi kullanabilirsiniz.

---

# 🗺️ ROADMAP & GELECEK PLANLARI

- [ ] Etsy API entegrasyonu
- [ ] Çoklu AI sağlayıcı desteği (RunPod, Fal.ai vb.)
- [ ] Etsy Auto-Publish (Draft yükleme) otomasyonu

---

# 🤝 KATKIDA BULUNMA

Pull request’ler her zaman kabul edilir.

Büyük değişikliklerden önce lütfen bir **Issue** açarak tartışma başlatın.

---

# ⭐ DESTEK

Projeyi faydalı bulduysanız GitHub üzerinden yıldız vermeyi unutmayın.

---

# 👨‍💻 GELİŞTİRİCİ

**İbrahim Furkan Gülcan**