# 🎨 ETSY POD AI DESIGN AUTOMATOR 🚀

Etsy'de çok satan (Best-Seller) Print-on-Demand (POD) ürünlerini analiz ederek, üzerlerindeki tasarımları tespit eden ve yapay zeka (AI) destekli üretim modelleriyle saniyeler içinde benzersiz yeni varyasyonlar, SEO uyumlu başlıklar ve etiketler üreten hepsi bir arada otomasyon aracı.

---

## 🌟 NEDEN BU PROJE?
AI ile tişört veya kupa tasarımı üretirken en büyük sorun, hangi tasarımın satacağından emin olamamaktır. Bu proje,  **Grounding DINO** kullanarak tasarımı önce kıyafetten izole eder (kırpar), ardından AI modellerini sadece bu saf tasarım üzerinden besleyerek doğrudan baskıya hazır (arka planı silinmiş) sonuçlar verir. Ürün analizi ile de hangi tasarımın satacağı konusunda daha net bir fikre sahip olursunuz.

---

## ⚙️ İŞ AKIŞI VE ÖZELLİKLER

* **🔍 1. Akıllı Analiz (Playwright):** Etsy ürün URL'si girilir. Ürünün görseli, başlığı, görüntülenme, favori ve yorum sayıları anında çekilir. *(Not: Mevcut sistemde etiketler, "Explore more related searches" alanından referans olarak alınmaktadır.)*

* **✂️ 2. Tasarım İzolasyonu (Grounding DINO):**
  Ürün üzerindeki asıl tasarım (grafik/yazı) yapay zeka ile tespit edilir ve tişörtten/kıyafetten kusursuzca kırpılır. AI'ın "tişört içinde tişört" çizme halüsinasyonu kesin olarak engellenir.

* **🧠 3. AI Varyasyon Üretimi (Replicate API):**
  Kullanıcının seçtiği AI modelleri (örn: Flux, Stable Diffusion vb.) ve özel promptlar kullanılarak kırpılan tasarımın benzersiz yeni varyasyonları ve geliştirilmiş halleri üretilir.

* **✨ 4. Görüntü İşleme (Upscale & BG Removal):**
  Üretilen tasarımların arka planları (Background Removal) otomatik olarak silinir. Düşük çözünürlüklü çıktılar için Upscale (Netleştirme) desteği sunulur. *(İpucu: En iyi sonuç için Upscale işlemi arka plan silinmeden ÖNCE yapılmalıdır).*

* **📈 5. AI SEO Üretimi:**
  Analiz edilen ürünün verileri GPT/LLM modelleriyle harmanlanarak ürüne özel, yüksek aranma hacimli yeni bir Title (Başlık) ve Tags (Etiketler) üretilir.

* **📥 6. Export (Dışa Aktarım):**
  Üretilen PNG tasarımlar ve SEO metinleri tek tıkla projenize indirilir.

---

## 🚀 KURULUM VE KULLANIM (GETTING STARTED)

Bu proje, kodlama bilmeyen kullanıcıların bile tek tıkla çalıştırabilmesi için **Akıllı Başlatıcı (.bat)** ile donatılmıştır.

### Gereksinimler
Sisteminizde **Python 3.10 veya üzeri** bir sürümün yüklü olması yeterlidir. *(Kurulum sırasında "Add Python to PATH" seçeneğinin işaretli olduğundan emin olun).*

### Kurulum Adımları
1. Bu repoyu bilgisayarınıza indirin (`Code` -> `Download ZIP`).
2. ZIP dosyasını klasöre çıkartın.
3. Klasörün içindeki **`Etsy_AI_Baslat.bat`** dosyasına çift tıklayın.

> **💡 Sihir Burada Başlıyor:** `.bat` dosyası sizin için otomatik olarak sanal ortam (venv) oluşturacak, tüm gerekli Python kütüphanelerini indirecek, Playwright tarayıcı motorunu kuracak ve veritabanını hazırlayıp projeyi tarayıcınızda (`http://127.0.0.1:8000`) açacaktır. Sonraki girişleriniz saniyeler sürer!

### Nasıl Kullanılır?
1. Tarayıcıda açılan uygulamaya kayıt olun veya giriş yapın.
2. Üst menüden **Ayarlar (Config)** sayfasına gidin.
3. **Replicate API Key** bilginizi girin ve kullanmak istediğiniz AI modellerini/promptları seçip kaydedin.
4. **Dashboard'a** dönün, bir Etsy URL'si yapıştırın ve arkanıza yaslanın!

---

## 🗺️ YOL HARİTASI (ROADMAP & GELECEK PLANLARI)

Bu proje aktif olarak geliştirilmektedir. Gelecek güncellemelerde planlanan modüller:

- [ ] **Etsy API Entegrasyonu:** Web scraping yerine doğrudan Etsy API ile orijinal ürün etiketlerinin %100 doğrulukla çekilmesi.
- [ ] **Modüler SEO Kontrolü:** Title ve Tag üretim süreçlerinin birbirinden ayrılması, daha spesifik prompt ve model seçme özgürlüğü.
- [ ] **Çoklu API Sağlayıcıları:** Replicate API'ye ek olarak RunPod, Fal.ai, OpenAI gibi farklı yapay zeka sağlayıcılarının sisteme entegre edilmesi.
- [ ] **👕 Otomatik Mockup Giydirme (Phase 2):** Üretilen şeffaf tasarımların, belirlenen boş mockup görsellerine (Photoshop API vb. ile) otomatik ve gerçekçi açılarla yerleştirilmesi.
- [ ] **🛒 Etsy Auto-Publish Otomasyonu (Phase 3):** Tasarımın, mockupların ve SEO verilerinin tek tıkla **Etsy Draft (Taslaklar)** bölümüne API üzerinden otomatik olarak yüklenmesi.

---

## 🤝 KATKIDA BULUNMA (CONTRIBUTING)
Pull request'ler her zaman kabul edilir! Büyük değişiklikler yapmadan önce, neyi değiştirmek istediğinizi tartışmak için lütfen bir "Issue" açın. Yıldız (Star) vermeyi unutmayın! ⭐
