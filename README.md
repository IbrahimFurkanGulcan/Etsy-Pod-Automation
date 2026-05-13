# 🚀 Etsy AI Design & POD Automation (SaaS)

Etsy'de çok satan (Best-Seller) Print-on-Demand (POD) ürünlerini analiz ederek, üzerlerindeki tasarımları tespit eden ve yapay zeka (AI) destekli üretim modelleriyle saniyeler içinde benzersiz yeni varyasyonlar, profesyonel mockuplar ve SEO uyumlu metinler üreten hepsi bir arada otomasyon aracı.

Çift yönlü (Dual) Pipeline mimarisi sayesinde ister yapay zekanın sıfırdan ürettiği tasarımları, isterseniz kendi kütüphanenizdeki mevcut görselleri saniyeler içinde satışa hazır hale getirebilirsiniz.

---
<img width="2522" height="1386" alt="Image" src="https://github.com/user-attachments/assets/49854887-9ab6-4b93-885e-c33d56a18fd7" />

# 🌟 NEDEN BU PROJE?

Etsy'de tişört/sweatshirt alanında mağaza açanların en büyük sıkıntısı çok fazla rakip arasından mağazalarını ön plana çıkarmak ve algoritmaya oturtmaktır. Bunun ana yöntemlerinden biri de yeterli sayıda günlük listing yüklemektir. Tasarım arştırması yapmak, bulunan tasarımın benzerini yapay zekaya tek tek ürettirmek veya belirli platformlardan benzerlerini bulmak baştan yapmak, mockuplamak seo için tag-title araştırmak yeterli sayıda listing oluşturmaya çalışırken çok fazla zaman alır.

Bu proje ile tşört katagorisinde iki farklı pipeline hizmeti sunarak özellikle yeni açılan mağazaların algoritmaya girebilmesi için zaman alan listing hazırlama işini hızlandırıyoruz.

Bu proje, Grounding DINO kullanarak tasarımı önce rakip kıyafetten izole eder (kırpar), ardından AI modellerini sadece bu saf tasarım üzerinden besleyerek doğrudan baskıya hazır (arka planı silinmiş) sonuçlar verir.

Analizden üretime, mockuptan SEO'ya kadar tüm POD süreçlerini tek bir merkezde toplar.

---

# ✨ SİSTEM MİMARİSİ VE ÖZELLİKLER

## 🔄 Dual-Pipeline Mimarisi

<img width="2556" height="1395" alt="Image" src="https://github.com/user-attachments/assets/71e28c98-8414-4122-b449-593b4f5f8cc6" />

### Pipeline 1 — AI Generative & Scraper

- Etsy URL'si üzerinden Playwright ile rakip ürün analizi yapar.
- Görüntülenme, favori, başlık gibi verileri toplar.
<img width="2549" height="1384" alt="Image" src="https://github.com/user-attachments/assets/a05df9b3-ea1d-4156-9757-85916d232fc0" />
- Ürün üzerindeki tasarımı izole eder.
- Seçilen AI modelleri (Flux, Seadream vb.) ile yeni varyasyonlar üretir.
<img width="2532" height="1389" alt="Image" src="https://github.com/user-attachments/assets/cc1ff52b-609e-46c3-bffe-c9abbe239af4" />
- Üretilen tasarımların arka planları otomatik olarak silinir.
- Seçilen şablonlara göre otomatik mockuplama yapar.
<img width="2540" height="1390" alt="Image" src="https://github.com/user-attachments/assets/1af8d4e2-2f9e-4b6a-9b21-bd37677ed160" />
- Orijinal tasarımda kullanılan tag-title ı referans alarak seo üretir.
<img width="2527" height="1388" alt="Image" src="https://github.com/user-attachments/assets/e9502ca5-d1d9-45cb-8993-349bb6380f67" />
- Tüm üretimi transparan tasarım-seo -texti ve mockuplanmış görseller klasörü içeren bir klasör şeklinde indirir.


### Pipeline 2 — Batch Processing & Mockup Orchestration

- Manuel olarak tasarım yüklenmesine olanak sağlar.
<img width="2537" height="1380" alt="Image" src="https://github.com/user-attachments/assets/6b8f6121-8fa3-4dcd-bd3a-3770c6094774" />
- Tasarım kütüphanesindeki şeffaf PNG'leri veya P1’den transfer edilen görselleri toplu işler.
- Seçilen mockup şablonlarıyla eşleştirir.
<img width="2416" height="1331" alt="Image" src="https://github.com/user-attachments/assets/5342615c-3f0e-40e0-bd5d-5068d737eb4c" />
- Tek tıkla onlarca profesyonel mockup üretir.
- Transparak görselleri vision-ai ile analiz eder.
- Vision-ai analiz çıktısını referans alarak seo üretir.
<img width="2526" height="1368" alt="Image" src="https://github.com/user-attachments/assets/98c67a4e-ba9f-472f-8668-9fa024749aa3" />
- Tüm üretimi transparan tasarım-seo -texti ve mockuplanmış görseller klasörü içeren bir klasör şeklinde indirir.

---

# 🗂️ GELİŞMİŞ MODÜL YÖNETİMİ

## 🎨 Tasarım Kütüphanesi (Asset Library)

- Üretilen veya manuel yüklenen tüm tasarımların merkezi depolama alanı.
<img width="2500" height="1379" alt="Image" src="https://github.com/user-attachments/assets/9da56894-8b00-427e-a5b8-bc240a015a3f" />
- Tasarımlar tek tıkla pipeline'lara yönlendirilebilir.
<img width="2559" height="1389" alt="Image" src="https://github.com/user-attachments/assets/67a0d8cd-c4a0-47c5-9019-3df6e05b4905" />

## 🖼️ Mockup Şablon Merkezi

- Boş mockup görsellerinizi sisteme yükleyip yönetebilirsiniz.
- Dinamik şablon havuzu desteği sunar.
<img width="2513" height="1347" alt="Image" src="https://github.com/user-attachments/assets/262758a7-74b2-4368-9861-53635bf6791e" />
<img width="2538" height="1384" alt="Image" src="https://github.com/user-attachments/assets/ef26a1c0-6901-438e-9c5d-20ecb495673f" />
<img width="2003" height="1373" alt="Image" src="https://github.com/user-attachments/assets/928e3f22-b543-4c7e-bfad-89df7e838220" />

## 🕘 Geçmiş Analizler (History)

- Daha önce analiz edilen Etsy linkleri ve yapılan üretimler saklanır.
- Daha önce manuel olarak yüklenen tasarımlardan yapılan üretimler saklanır.
- Rakip verileri ve üretilen tasarımlar tek tıkla geri çağrılabilir.
<img width="2524" height="1383" alt="Image" src="https://github.com/user-attachments/assets/704d3803-5039-48ee-8dfe-206fb954fb3b" />

## ⚙️ Dinamik Ayarlar (Config)

Arayüz üzerinden:

- Replicate API Key
- Varsayılan sistem promptları
- Aktif AI modelleri

kod yazmadan yönetilebilir.
<img width="1963" height="1379" alt="Image" src="https://github.com/user-attachments/assets/ac39152f-52ac-404b-87a8-cf5819aa3423" />
<img width="1955" height="1380" alt="Image" src="https://github.com/user-attachments/assets/516cee08-b470-4eb7-85fc-fb5d75516ec4" />

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
<img width="829" height="523" alt="Image" src="https://github.com/user-attachments/assets/b795eae9-8fba-4617-a9c2-0778874ff292" />
<img width="2034" height="1263" alt="Image" src="https://github.com/user-attachments/assets/cfa52f1a-deae-4b52-996e-85eb299e7576" />
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
