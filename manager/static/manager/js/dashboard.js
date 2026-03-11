        // Mevcut İşlemdeki Ürün State'i (Sayfalar arası veri taşımak için)
let currentActiveProduct = null;


        // --- SAYFA GEÇİŞLERİ VE GÖRÜNÜM KONTROLLERİ ---
const pageAnalyze = document.getElementById('page-analyze');
const pageGenerate = document.getElementById('page-generate');

// goToGeneratePage artık opsiyonel bir 'force' parametresi alıyor
async function goToGeneratePage(force = false) {
    if(!currentActiveProduct || !currentActiveProduct.id) {
        alert("Önce geçerli bir ürün analizi yapmalısınız.");
        return;
    }

    pageAnalyze.classList.add('hidden');
    pageGenerate.classList.remove('hidden');
    window.scrollTo(0,0);
    
    document.getElementById('processed-section').classList.add('hidden');
    document.getElementById('seo-section').classList.add('hidden');
    
    const container = document.getElementById('generated-images-container');
    
    // Mesajı işleme göre güncelleyelim
    const loadingMsg = force ? "Yeni tasarımlar üretiliyor (API)..." : "Tasarımlar hazırlanıyor...";
    container.innerHTML = `<div class="col-span-3 text-center py-10 text-indigo-500"><i class="fa-solid fa-spinner fa-spin text-3xl mb-3"></i><p>${loadingMsg}</p></div>`;

    try {
        const response = await fetch('/generate-designs/', {
            method: 'POST',
            body: JSON.stringify({ 
                product_id: currentActiveProduct.id,
                force_recreate: force // Backend'e bu bilgiyi gönderiyoruz
            }),
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.status === "success") {
            renderGeneratedImages(data.images);
            
            // Eğer veritabanından geldiyse kullanıcıya "Yeniden Üret" butonunu gösterelim
            // (HTML'de bu ID ile bir butonun olduğunu varsayıyorum)
            const regenBtn = document.getElementById('regenerate-button');
            if(regenBtn) {
                regenBtn.classList.remove('hidden');
                regenBtn.onclick = () => goToGeneratePage(true); // Tıklanırsa force=true ile çalışır
            }
        } else {
            container.innerHTML = `<div class="col-span-3 text-center py-10 text-red-500">Hata: ${data.message}</div>`;
        }
    } catch (err) {
        container.innerHTML = `<div class="col-span-3 text-center py-10 text-red-500">Bağlantı hatası: ${err.message}</div>`;
    }
}

function goToAnalyzePage() {
    // Sadece görünümleri değiştiriyoruz
    pageGenerate.classList.add('hidden');
    pageAnalyze.classList.remove('hidden');
    
    // Sayfanın en üstüne kaydır
    window.scrollTo(0,0);
    
    // DİKKAT: Artık currentActiveProduct = null; YAPMIYORUZ!
    // DİKKAT: analyze-results alanını gizlemiyoruz!
    // DİKKAT: etsy-url inputunu temizlemiyoruz!
}

        // --- 1. AŞAMA: ANALİZ VE DB SORGUSU ---
async function analyzeProduct() {
    const urlInput = document.getElementById('etsy-url').value.trim();
    const errorMsg = document.getElementById('error-message');
    const resultsDiv = document.getElementById('analyze-results');
    
    // Görünürlüğü ayarla
    errorMsg.classList.add('hidden');
    resultsDiv.classList.add('hidden');
    document.getElementById('loading-analyze').classList.remove('hidden');

    try {
        // Django View'a istek at
        const response = await fetch('/scrape-action/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // CSRF Token Django için hayati, eğer hata alırsan bunu kontrol ederiz
            },
            body: JSON.stringify({ url: urlInput })
        });

        const data = await response.json();

        if (data.status === "success") {
            // Gelen veriyi "Global State"e kaydet (İleriki adımlar için önemli)
            currentActiveProduct = data; 
            
            // Senin yazdığın render fonksiyonuna veriyi gönder
            renderAnalysisResults(data);
            
            // Yükleniyor'u gizle, sonuçları göster
            document.getElementById('loading-analyze').classList.add('hidden');
            resultsDiv.classList.remove('hidden');
        } else {
            throw new Error(data.message);
        }

    } catch (err) {
        document.getElementById('loading-analyze').classList.add('hidden');
        showError("Hata oluştu: " + err.message);
    }
}

        function showError(msg) {
            document.getElementById('error-text').innerText = msg;
            document.getElementById('error-message').classList.remove('hidden');
        }

        // Analiz Sonuçlarını Dinamik HTML'e Çevirme
        function renderAnalysisResults(data) {
    document.getElementById('res-image').src = data.image_url; // image_url olarak güncelledik
    document.getElementById('res-title').innerText = data.title;
    document.getElementById('res-desc').innerText = data.description;
    
    document.getElementById('res-stats').innerHTML = `
        <span class="bg-green-100 text-green-800 px-3 py-1 rounded-full font-bold text-lg">${data.price}</span>
        <span class="flex items-center text-red-500"><i class="fa-solid fa-heart mr-1"></i> ${data.favorited} Favori</span>
        <span class="flex items-center text-blue-500"><i class="fa-solid fa-eye mr-1"></i> ${data.views} Görüntülenme</span>
    `;

    // Tagleri listele
    const tagsHtml = data.tags.map(tag => 
        `<span class="bg-gray-100 border border-gray-200 text-gray-600 px-2 py-1 rounded text-xs">${tag}</span>`
    ).join('');
    document.getElementById('res-tags').innerHTML = tagsHtml;
}

        
        // --- 2. AŞAMA: DB'DEN GELEN GÖRSELLERİ RENDER ETME ---
function renderGeneratedImages(imagesData) {
            const container = document.getElementById('generated-images-container');
            container.innerHTML = ''; 

            imagesData.forEach((item, index) => {
                const cardHTML = `
                    <div class="border rounded-lg p-3 relative group hover:border-indigo-400 transition">
                        <div class="absolute top-4 left-4 z-10 bg-white rounded-sm p-1 shadow">
                            <input type="checkbox" class="gen-checkbox w-5 h-5 text-indigo-600 rounded cursor-pointer" id="gen-img-${index}" data-id="${item.id}" value="${item.src}">
                        </div>
                        <img src="${item.src}" class="w-full h-48 object-contain bg-gray-50 rounded cursor-pointer hover:opacity-90 transition-opacity" onclick="openModal(this.src)">
                        <label for="gen-img-${index}" class="block text-center mt-2 font-medium cursor-pointer text-sm text-gray-600">${item.label}</label>
                    </div>
                `;
                container.innerHTML += cardHTML;
            });
        }

        // --- 3. AŞAMA: SEÇİLİ GÖRSELLERİ İŞLEME ---
async function processSelectedImages() {
            const checkboxes = document.querySelectorAll('.gen-checkbox');
            let selectedIds = [];

            // Checkboxlardan GERÇEK DB ID'sini alıyoruz ve sayıya çeviriyoruz
            checkboxes.forEach((cb) => {
                if(cb.checked) {
                    const realId = parseInt(cb.dataset.id);
                    // Sadece geçerli bir sayıysa listeye ekle
                    if (!isNaN(realId)) {
                        selectedIds.push(realId);
                    }
                }
            });

            if(selectedIds.length === 0) {
                alert("Lütfen işlemek için en az 1 görsel seçin.");
                return;
            }

            document.getElementById('processed-section').classList.add('hidden');
            document.getElementById('seo-section').classList.add('hidden');
            document.getElementById('loading-process').classList.remove('hidden');

            try {
                const response = await fetch('/process-selected/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        product_id: currentActiveProduct.id,
                        selected_ids: selectedIds 
                    })
                });

                const data = await response.json();

                document.getElementById('loading-process').classList.add('hidden');

                if (data.status === "success") {
                    const container = document.getElementById('processed-images-container');
                    container.innerHTML = ''; 

                    data.images.forEach((item) => {
                        const cardHTML = `
                            <div class="border-2 border-green-100 rounded-lg p-3 relative group bg-green-50/30">
                                <div class="absolute top-4 left-4 z-10 bg-white rounded-sm p-1 shadow">
                                    <input type="checkbox" class="proc-checkbox w-5 h-5 text-emerald-600 rounded cursor-pointer" data-id="${item.id}" checked>
                                </div>
                                <div class="absolute top-4 right-4 z-10 bg-green-500 text-white text-xs px-2 py-1 rounded shadow">
                                    Arka Plan Silindi
                                </div>
                                <img src="${item.src}" class="w-full h-48 object-contain rounded zoomable cursor-pointer" onclick="openModal(this.src)">
                                <label class="block text-center mt-2 font-medium text-sm text-green-700">İşlenmiş Varyasyon ${item.id}</label>
                            </div>
                        `;
                        container.innerHTML += cardHTML;
                    });

                    document.getElementById('processed-section').classList.remove('hidden');
                    document.getElementById('processed-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
                } else {
                    alert("Hata: " + data.message);
                }
            } catch (err) {
                document.getElementById('loading-process').classList.add('hidden');
                alert("Bağlantı hatası: " + err.message);
            }
        }

                // --- 4. AŞAMA: TAG & TITLE ÜRETİMİ ---
// Fonksiyona varsayılan olarak force=false parametresi ekledik
async function generateTagAndTitle(force = false) {
    const checkboxes = document.querySelectorAll('.proc-checkbox');
    let hasSelection = false;
    checkboxes.forEach(cb => { if(cb.checked) hasSelection = true; });

    if(!hasSelection) {
        alert("SEO üretimi için en az 1 işlenmiş görsel seçili olmalıdır.");
        return;
    }

    document.getElementById('seo-section').classList.add('hidden');
    document.getElementById('loading-tags').classList.remove('hidden');

    // Eğer yeniden üretim yapılıyorsa kullanıcıya farklı bir mesaj göster
    const loadingText = document.querySelector('#loading-tags p');
    if (loadingText) {
        loadingText.innerText = force ? "Yapay Zeka yeni başlıklar düşünüyor..." : "SEO verileri hazırlanıyor...";
    }

    try {
        const response = await fetch('/generate-seo/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                product_id: currentActiveProduct.id,
                force_recreate: force // Backend'e bu bilgiyi gönderiyoruz
            })
        });

        const data = await response.json();
        document.getElementById('loading-tags').classList.add('hidden');

        if (data.status === "success") {
            // Verileri ekrana bas
            document.getElementById('output-title').value = data.title || "";
            document.getElementById('output-tags').value = data.tags || "";
            
            document.getElementById('seo-section').classList.remove('hidden');
            document.getElementById('seo-section').scrollIntoView({ behavior: 'smooth', block: 'start' });

            // Yeniden Üret Butonunu Aktifleştir
            const regenSeoBtn = document.getElementById('regen-seo-btn');
            if (regenSeoBtn) {
                regenSeoBtn.classList.remove('hidden');
                // Butona tıklandığında force=true ile aynı fonksiyonu tekrar çağır
                regenSeoBtn.onclick = () => generateTagAndTitle(true);
            }

        } else {
            alert("Backend Hatası: " + data.message);
        }
    } catch (err) {
        document.getElementById('loading-tags').classList.add('hidden');
        alert("Bağlantı hatası: " + err.message);
    }
}

// --- EXPORT (ZİP OLARAK İNDİRME) ---
async function exportData() {
    if (!currentActiveProduct || !currentActiveProduct.id) {
        alert("Dışa aktarılacak aktif bir ürün bulunamadı.");
        return;
    }

    // Kullanıcıya bir şeyler olduğunu göstermek için butonu güncelleyelim
    // (HTML'deki export butonunun ID'si 'export-btn' ise, değilse kendine göre uyarla)
    const btn = document.querySelector('button[onclick="exportData()"]'); 
    const originalText = btn ? btn.innerHTML : "Export Project";
    if (btn) {
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Paketleniyor...';
        btn.disabled = true;
    }

    try {
        const response = await fetch('/export-project/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: currentActiveProduct.id })
        });

        if (!response.ok) {
            // Eğer backend'den bir JSON hata mesajı döndüyse onu yakala
            const errorData = await response.json().catch(() => ({ message: "Bilinmeyen bir hata oluştu." }));
            throw new Error(errorData.message || "İndirme başarısız oldu.");
        }

        // Gelen ZIP verisini Blob (Dosya Yumağı) olarak al
        const blob = await response.blob();
        
        // Bu yumağı bilgisayara indirecek geçici bir URL oluştur
        const downloadUrl = window.URL.createObjectURL(blob);
        
        // Görünmez bir link <a> oluştur, tıkla ve sil (Klasik JS indirme taktiği)
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `Etsy_Project_${currentActiveProduct.id}.zip`;
        document.body.appendChild(a);
        a.click();
        
        // Temizlik
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);

        alert("Export Başarılı! Dosyalarınız ZIP olarak indirildi.");

    } catch (err) {
        alert("Export Hatası: " + err.message);
    } finally {
        // Butonu eski haline getir
        if (btn) {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }
}



// ==========================================
// MODAL (RESİM BÜYÜTME) FONKSİYONLARI
// ==========================================

function openModal(src) {
    // HTML'deki modalı ve içindeki resim kutusunu buluyoruz
    const modal = document.getElementById('image-modal');
    const modalImg = document.getElementById('modal-image');
    
    if (modal && modalImg) {
        modalImg.src = src; // Tıklanan resmin linkini aktar
        
        // Tailwind sınıflarıyla görünür yap
        modal.classList.remove('hidden');
        
        // Yumuşak açılış animasyonu (opacity-0 -> opacity-100)
        setTimeout(() => {
            modal.classList.remove('opacity-0');
            modal.classList.add('opacity-100');
        }, 10);

        document.body.style.overflow = 'hidden'; // Arka planın kaymasını durdur
    }
}

function closeModal() {
    const modal = document.getElementById('image-modal');
    if (modal) {
        // Yumuşak kapanış animasyonu
        modal.classList.remove('opacity-100');
        modal.classList.add('opacity-0');
        
        // Animasyon bitince (300ms) tamamen gizle
        setTimeout(() => {
            modal.classList.add('hidden');
        }, 300);

        document.body.style.overflow = 'auto'; // Kaymayı tekrar aç
    }
}

// ESC tuşuna basınca kapatma özelliği ekleyelim (Kullanıcı dostu)
document.addEventListener('keydown', function(e) {
    if (e.key === "Escape") closeModal();
});