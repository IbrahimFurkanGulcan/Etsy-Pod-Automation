# 🎨 ETSY POD AI DESIGN AUTOMATOR 🚀

Etsy'de çok satan (Best-Seller) Print-on-Demand (POD) ürünlerini analiz ederek, üzerlerindeki tasarımları tespit eden ve yapay zeka (AI) destekli üretim modelleriyle saniyeler içinde benzersiz yeni varyasyonlar, SEO uyumlu başlıklar ve etiketler üreten hepsi bir arada otomasyon aracı.

---

## 🌟 NEDEN BU PROJE?
AI ile tişört veya kupa tasarımı üretirken en büyük sorun, hangi tasarımın satacağından emin olamamaktır. Bu proje,  **Grounding DINO** kullanarak tasarımı önce kıyafetten izole eder (kırpar), ardından AI modellerini sadece bu saf tasarım üzerinden besleyerek doğrudan baskıya hazır (arka planı silinmiş) sonuçlar verir. Ürün analizi ile de hangi tasarımın satacağı konusunda daha net bir fikre sahip olursunuz.

---

<img width="2542" height="1295" alt="Ekran görüntüsü 2026-03-19 005413" src="https://github.com/user-attachments/assets/13464c0a-e0e9-4bca-8a75-c15edf11556d" />

<img width="2557" height="1390" alt="Ekran görüntüsü 2026-03-19 005430" src="https://github.com/user-attachments/assets/0357d6db-2f7a-4f40-be7e-b06b04297ee4" />



## ⚙️ İŞ AKIŞI VE ÖZELLİKLER

* **🔍 1. Akıllı Analiz (Playwright):** Etsy ürün URL'si girilir. Ürünün görseli, başlığı, görüntülenme, favori ve yorum sayıları anında çekilir. *(Not: Mevcut sistemde etiketler, "Explore more related searches" alanından referans olarak alınmaktadır.)*

  <img width="2545" height="1401" alt="Ekran görüntüsü 2026-03-19 005529" src="https://github.com/user-attachments/assets/8f1778ba-cb60-4ed1-8cd7-3c43ef8795a5" />


* **✂️ 2. Tasarım İzolasyonu (Grounding DINO):**
  Ürün üzerindeki asıl tasarım (grafik/yazı) yapay zeka ile tespit edilir ve tişörtten/kıyafetten kusursuzca kırpılır. AI'ın "tişört içinde tişört" çizme halüsinasyonu kesin olarak engellenir.

  <img width="1520" height="1532" alt="Başlıksız-1" src="https://github.com/user-attachments/assets/adb9b1cf-6ba4-44b6-a9c3-5c61197bd606" />


* **🧠 3. AI Varyasyon Üretimi (Replicate API):**
  Kullanıcının seçtiği AI modelleri (örn: Flux, Stable Diffusion vb.) ve özel promptlar kullanılarak kırpılan tasarımın benzersiz yeni varyasyonları ve geliştirilmiş halleri üretilir.

  <img width="2559" height="1272" alt="Ekran görüntüsü 2026-03-19 005542" src="https://github.com/user-attachments/assets/2a76cbe4-9b12-446f-b3be-4f54689789a1" />


* **✨ 4. Görüntü İşleme (Upscale & BG Removal):**
  Üretilen tasarımların arka planları (Background Removal) otomatik olarak silinir. Düşük çözünürlüklü çıktılar için Upscale (Netleştirme) desteği sunulur. *(İpucu: En iyi sonuç için Upscale işlemi arka plan silinmeden ÖNCE yapılmalıdır).*

  <img width="2490" height="718" alt="Ekran görüntüsü 2026-03-19 005603" src="https://github.com/user-attachments/assets/b548ee29-0eac-4b07-b01d-89f28f68f01d" />


* **📈 5. AI SEO Üretimi:**
  Analiz edilen ürünün verileri GPT/LLM modelleriyle harmanlanarak ürüne özel, yüksek aranma hacimli yeni bir Title (Başlık) ve Tags (Etiketler) üretilir.

  <img width="2559" height="688" alt="Ekran görüntüsü 2026-03-19 005618" src="https://github.com/user-attachments/assets/53f12018-e008-45c6-bac6-3abbcc76f615" />


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
