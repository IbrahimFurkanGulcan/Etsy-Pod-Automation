// Sayfa yüklendiğinde hafızadaki verileri geri getir
document.addEventListener('DOMContentLoaded', () => {
    restoreFromStorage();
});

// ==========================================
// GELİŞMİŞ HAFIZA YÖNETİMİ (STATE PERSISTENCE)
// ==========================================

// 1. Her başarılı işlemde tüm durumu kaydet
function saveAppState(pageId, extraData = {}) {
    localStorage.setItem('current_page', pageId);
    if (extraData.urls) localStorage.setItem('last_etsy_urls', JSON.stringify(extraData.urls));
    if (extraData.analysis) localStorage.setItem('last_analysis_results', JSON.stringify(extraData.analysis));
    if (extraData.generated) localStorage.setItem('last_generated_results', JSON.stringify(extraData.generated));

    localStorage.setItem('mockup_mapping', JSON.stringify(mockupMapping));
    localStorage.setItem('mockup_results_cache', JSON.stringify(generatedMockupsCache));

    if (extraData.seoResults) {
        localStorage.setItem('seo_results_cache', JSON.stringify(extraData.seoResults));
    }
}


// 2. Sayfa açıldığında durumu geri yükle
function restoreFromStorage() {
    const currentPage = localStorage.getItem('current_page') || 'page-analyze';
    const savedUrls = JSON.parse(localStorage.getItem('last_etsy_urls'));
    const savedAnalysis = JSON.parse(localStorage.getItem('last_analysis_results'));
    const savedGenerated = JSON.parse(localStorage.getItem('last_generated_results'));
    const savedMapping = JSON.parse(localStorage.getItem('mockup_mapping'));
    const savedMockupResults = JSON.parse(localStorage.getItem('mockup_results_cache'));
    const savedSeoResults = JSON.parse(localStorage.getItem('seo_results_cache')); // Yeni

    // 1. Önce her şeyi gizle
    ['page-analyze', 'page-generate', 'page-mockup', 'page-seo'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    });

    // 2. Temel verileri (URL ve Analiz) geri yükle
    if (savedUrls) {
        const urlContainer = document.getElementById('url-inputs-container');
        if (urlContainer) {
            urlContainer.innerHTML = '';
            savedUrls.forEach((url, index) => addUrlField(url, index === 0));
        }
    }
    if (savedAnalysis) renderAnalysisResults(savedAnalysis);

    // 3. Sayfa geçişini ve içerik üretimini yap
    if (currentPage === 'page-analyze') {
        document.getElementById('page-analyze').classList.remove('hidden');
    } 
    else if (currentPage === 'page-generate') {
        if (savedGenerated) renderBulkGeneratedImages(savedGenerated);
        document.getElementById('page-generate').classList.remove('hidden');
    } 
    else if (currentPage === 'page-mockup' || currentPage === 'page-seo') {
        if (savedGenerated) {
            const transparentImages = [];
            for (const prodId in savedGenerated) {
                savedGenerated[prodId].forEach(img => {
                    if (img.is_processed === true && img.no_bg_src) transparentImages.push(img);
                });
            }

            if (transparentImages.length > 0) {
                renderMockupDesigns(transparentImages);
                fetchMockupTemplates().then(() => {
                    if (savedMapping) mockupMapping = savedMapping;
                    if (savedMockupResults) generatedMockupsCache = savedMockupResults;

                    Object.keys(mockupMapping).forEach(id => updateRowTemplatesUI(id));
                    Object.entries(generatedMockupsCache).forEach(([id, urls]) => renderGeneratedMockupsUI(id, urls));
                    
                    if (currentPage === 'page-mockup') {
                        document.getElementById('page-mockup').classList.remove('hidden');
                        showSEOButton(); 
                    } else if (currentPage === 'page-seo') {
                        document.getElementById('page-seo').classList.remove('hidden');
                        goToSEOPage(); // Sayfayı çiz
                        
                        // YENİ: Daha önce üretilmiş SEO metinlerini kutulara geri doldur
                        if (savedSeoResults) {
                            for (const [d_id, res] of Object.entries(savedSeoResults)) {
                                const tInput = document.getElementById(`seo-title-${d_id}`);
                                const gInput = document.getElementById(`seo-tags-${d_id}`);
                                if (tInput && res.title) tInput.value = res.title;
                                if (gInput && res.tags) gInput.value = res.tags;
                                
                                // Export butonunu görünür yap
                                document.getElementById('export-container')?.classList.remove('hidden');
                            }
                        }
                    }
                });
            }
        }
    }
}

function addUrlField(urlValue = "", isFirst = false) {
    const container = document.getElementById('url-inputs-container');
    const newDiv = document.createElement('div');
    newDiv.className = "relative flex items-center gap-2 mt-3 fade-in";
    
    const buttonHtml = isFirst 
        ? `<button type="button" onclick="addUrlField()" class="bg-indigo-50 hover:bg-indigo-100 text-indigo-600 font-bold w-12 h-12 rounded-lg transition flex items-center justify-center flex-shrink-0"><i class="fa-solid fa-plus text-lg"></i></button>`
        : `<button type="button" onclick="this.parentElement.remove()" class="bg-red-50 hover:bg-red-100 text-red-500 font-bold w-12 h-12 rounded-lg transition flex items-center justify-center flex-shrink-0"><i class="fa-solid fa-minus text-lg"></i></button>`;

    newDiv.innerHTML = `
        <div class="relative flex-grow">
            <span class="absolute inset-y-0 left-0 flex items-center pl-4 text-slate-400"><i class="fa-brands fa-etsy text-xl"></i></span>
            <input type="url" value="${urlValue}" placeholder="https://www.etsy.com/listing/..." 
                class="etsy-url-input block w-full pl-12 pr-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 outline-none transition-shadow text-sm">
        </div>
        ${buttonHtml}`;
    container.appendChild(newDiv);
}

// --- 1. AŞAMA: ANALİZ VE DB SORGUSU ---
async function analyzeProduct() {
    const inputs = document.querySelectorAll('.etsy-url-input');
    const urlArray = Array.from(inputs).map(input => input.value.trim()).filter(val => val !== "");
    
    const errorMsg = document.getElementById('error-message');
    const resultsContainer = document.getElementById('analyze-results-container'); // Yeni container id'si
    const loadingDiv = document.getElementById('loading-analyze');
    const loadingText = document.querySelector('#loading-analyze p');
    
    errorMsg.classList.add('hidden');
    if(resultsContainer) resultsContainer.classList.add('hidden');
    
    if (urlArray.length === 0) {
        showError("Lütfen en az bir tane geçerli URL girin.");
        return;
    }

    // 1. Adım: Veritabanı kontrolü mesajı
    if (loadingText) loadingText.innerHTML = `<span class="font-bold text-slate-700">Adım 1:</span> Veritabanı kontrol ediliyor...`;
    loadingDiv.classList.remove('hidden');

    // Zamanlayıcı (1.5 saniye içinde cevap gelmezse Scraper uyarısı ver)
    const scrapeTimeout = setTimeout(() => {
        if (loadingText) loadingText.innerHTML = `<span class="font-bold text-orange-600">Adım 2:</span> Veritabanında bulunmayanlar için Scraper çalıştırılıyor (10-15 sn)...`;
    }, 1500); 

    try {
        const response = await fetch('/etsy/api/analyze/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') || '' 
            },
            body: JSON.stringify({ urls: urlArray, force_rescrape: false }) 
        });

        const data = await response.json();
        
        // İşlem bitti, zamanlayıcıyı durdur
        clearTimeout(scrapeTimeout);

        if (data.status === "success") {

            // DOĞRU SATIR:
            saveAppState('page-analyze', { urls: urlArray, analysis: data.results });
            
            if (loadingText) loadingText.innerHTML = `<span class="font-bold text-emerald-600">Başarılı:</span> Veriler ekrana getiriliyor...`;
            
            setTimeout(() => {
                renderAnalysisResults(data.results); // Çoklu render fonksiyonuna gönder
                loadingDiv.classList.add('hidden');
                if(resultsContainer) resultsContainer.classList.remove('hidden');
            }, 500);

        } else {
            throw new Error(data.message);
        }

    } catch (err) {
        clearTimeout(scrapeTimeout);
        loadingDiv.classList.add('hidden');
        showError("Hata oluştu: " + err.message);
    }
}

function clearSession() {
    if(confirm("Tüm girişleri ve analiz sonuçlarını silmek istediğinize emin misiniz?")) {
        localStorage.removeItem('last_etsy_urls');
        localStorage.removeItem('last_analysis_results');
        // Sayfayı yenileyerek her şeyi ilk haline döndür
        window.location.reload();
    }
}

// ==========================================
// ARAYÜZE VERİLERİ BASAN FONKSİYON (TOPLU SEÇİM DESTEKLİ)
// ==========================================
function renderAnalysisResults(resultsArray) {
    analyzedProductsCache = resultsArray; 
    const container = document.getElementById('analyze-results-container');
    container.innerHTML = ''; 

    resultsArray.forEach((data, index) => {
        const tagsHtml = data.tags && data.tags.length > 0 
            ? data.tags.map(tag => `<span class="bg-slate-100 border border-slate-200 text-slate-600 px-2 py-1 rounded-md text-xs font-medium">${tag}</span>`).join('')
            : '<span class="text-slate-400 text-sm">Etiket bulunamadı.</span>';

        const cardHtml = `
        <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col md:flex-row gap-8 mt-4 relative">
            
            <!-- ONAY KUTUSU (TOPLU SEÇİM İÇİN) -->
            <div class="absolute top-4 left-4 z-10">
                <input type="checkbox" class="product-select-checkbox w-6 h-6 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer" 
                    data-id="${data.id}" checked>
            </div>

            <div class="md:w-1/3 flex flex-col items-center group pt-4 md:pt-0">
                <div class="relative w-full rounded-xl overflow-hidden border border-slate-200 cursor-pointer shadow-sm hover:shadow-md transition" onclick="openModal('${data.image_url}')">
                    <img src="${data.image_url}" class="w-full h-64 object-cover group-hover:scale-105 transition-transform duration-500">
                </div>
            </div>

            <div class="md:w-2/3 space-y-4">
                <div class="flex flex-col xl:flex-row xl:items-start justify-between gap-4">
                    <h2 class="text-xl font-bold text-slate-800 leading-tight flex-1 ml-4 md:ml-0">${data.title || 'İsimsiz Ürün'}</h2>
                    
                    <button onclick="forceRescrape('${data.url}')" class="shrink-0 text-xs font-bold bg-amber-50 text-amber-600 hover:bg-amber-100 px-3 py-1.5 rounded-lg transition flex items-center gap-2 border border-amber-200 h-fit">
                        <i class="fa-solid fa-rotate"></i> Yeniden Kazı (Güncelle)
                    </button>
                </div>
                
                <div class="flex items-center gap-4 text-sm flex-wrap pb-3 border-b border-slate-100">
                    <span class="bg-emerald-100 text-emerald-800 px-3 py-1 rounded-lg font-bold">${data.price || '-'}</span>
                    <span class="flex items-center text-red-500 font-medium"><i class="fa-solid fa-heart mr-1.5"></i> ${data.favorited || 0}</span>
                    <span class="flex items-center text-blue-500 font-medium"><i class="fa-solid fa-eye mr-1.5"></i> ${data.views || 0}</span>
                </div>
                
                <div>
                    <h3 class="font-bold text-slate-700 mb-1 text-sm"><i class="fa-solid fa-align-left text-slate-400 mr-1"></i> Açıklama</h3>
                    <div class="text-slate-600 text-xs h-24 overflow-y-auto pr-3 bg-slate-50 p-3 rounded-lg border border-slate-100">${data.description || ''}</div>
                </div>

                <div>
                    <h3 class="font-bold text-slate-700 mb-1 text-sm"><i class="fa-solid fa-tags text-slate-400 mr-1"></i> Etiketler</h3>
                    <div class="flex flex-wrap gap-2">${tagsHtml}</div>
                </div>

                <div class="pt-4 border-t border-slate-100 flex justify-end">
                    <button onclick="startGenerateForProduct(${index})" 
                        class="bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold py-2 px-6 rounded-lg transition text-sm flex items-center gap-2">
                        <i class="fa-solid fa-wand-magic-sparkles"></i> Sadece Bu Ürünü Üret
                    </button>
                </div>
            </div>
        </div>`;
        container.insertAdjacentHTML('beforeend', cardHtml);
    });

    // TÜM KARTLARIN ALTINA TOPLU İŞLEM BUTONU EKLE
    if (resultsArray.length > 0) {
        const bulkBtnHtml = `
            <div class="mt-12 flex justify-center pb-10">
                <button onclick="startBulkGeneration()" 
                    class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 px-12 rounded-xl transition shadow-lg flex items-center gap-3 text-lg transform hover:-translate-y-1">
                    <i class="fa-solid fa-layer-group"></i> Seçilen Ürünleri Topluca AI Üretimine Gönder
                </button>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', bulkBtnHtml);
    }
}

// ==========================================
// SADECE SEÇİLİ (TEK) ÜRÜN İÇİN AI ÜRETİMİ
// ==========================================
async function startGenerateForProduct(index) {
    const product = analyzedProductsCache[index];
    if (!product || !product.id) {
        showError("Ürün ID'si bulunamadı.");
        return;
    }

    // UI'ı Üretim (Generate) sayfasına geçir
    document.getElementById('page-analyze').classList.add('hidden');
    document.getElementById('page-generate').classList.remove('hidden');
    
    const container = document.getElementById('generated-images-container');
    container.innerHTML = `<div class="col-span-full text-center py-10">
        <i class="fa-solid fa-wand-magic-sparkles fa-spin text-4xl text-indigo-500 mb-4"></i>
        <p class="text-slate-500 font-medium">Sistem kontrol ediliyor...<br><span class="text-xs text-slate-400">Daha önce üretildiyse hafızadan getirilecek, yoksa sıfırdan çizilecek.</span></p>
    </div>`;

    try {
        const response = await fetch('/ai/api/generate/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') || '' },
            // SADECE BU ÜRÜNÜN ID'SİNİ DİZİ (ARRAY) OLARAK GÖNDERİYORUZ
            body: JSON.stringify({ product_ids: [product.id] }) 
        });

        const data = await response.json();

        if (data.status === "success") {
            renderBulkGeneratedImages(data.data); // Aynı render fonksiyonunu kullanabiliriz
        } else {
            showError("Üretim Hatası: " + data.message);
        }
    } catch (err) {
        showError("Bağlantı hatası: " + err.message);
    }
}

// SADECE BİR URL'Yİ DB'Yİ ATLAYARAK YENİDEN KAZIR
async function forceRescrape(url) {
    const loadingDiv = document.getElementById('loading-analyze');
    const loadingText = document.querySelector('#loading-analyze p');
    
    if (loadingText) loadingText.innerHTML = `<span class="font-bold text-amber-600">Güncelleme:</span> Eski veri siliniyor, sayfa baştan kazınıyor (10-15 sn)...`;
    loadingDiv.classList.remove('hidden');

    try {
        const response = await fetch('/etsy/api/analyze/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') || '' },
            // Sadece ilgili URL'yi ve zorla kazıma komutunu gönderiyoruz
            body: JSON.stringify({ urls: [url], force_rescrape: true }) 
        });

        const data = await response.json();
        if (data.status === "success") {
            // Başarıyla güncellendiğinde, arayüzü tazelemek için ana fonksiyonu tekrar tetikliyoruz
            // (Zaten DB'de güncellediğimiz için bu sefer saniyeler içinde yeni veriyi ekrana çizecek)
            document.getElementById('loading-analyze').classList.add('hidden');
            analyzeProduct(); 
        } else {
            throw new Error(data.message);
        }
    } catch(err) {
        loadingDiv.classList.add('hidden');
        showError("Güncelleme Hatası: " + err.message);
    }
}

function showError(msg) {
    document.getElementById('error-text').innerText = msg;
    document.getElementById('error-message').classList.remove('hidden');
}


// Güvenlik (CSRF) İçin Yardımcı Fonksiyon (Yoksa js dosyanın en altına ekle)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
} 

// ==========================================
//  TOPLU AI ÜRETİMİNE GEÇİŞ
// ==========================================

async function startBulkGeneration() {
    // 1. Seçili Checkbox'ları bul
    const selectedCheckboxes = document.querySelectorAll('.product-select-checkbox:checked');
    const productIds = Array.from(selectedCheckboxes).map(cb => cb.dataset.id);

    if (productIds.length === 0) {
        alert("Lütfen en az bir ürün seçin.");
        return;
    }

    // UI Değişimi
    document.getElementById('page-analyze').classList.add('hidden');
    document.getElementById('page-generate').classList.remove('hidden');
    
    const container = document.getElementById('generated-images-container');
    container.innerHTML = `<div class="col-span-full text-center py-10">
        <i class="fa-solid fa-robot fa-spin text-4xl text-indigo-500 mb-4"></i>
        <p class="text-slate-500">Seçilen ${productIds.length} ürün için tasarımlar hazırlanıyor...</p>
    </div>`;

    try {
        const response = await fetch('/ai/api/generate/', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json', 
                'X-CSRFToken': getCookie('csrftoken') || '' 
            },
            
            body: JSON.stringify({ product_ids: productIds }) 
        });

        const data = await response.json();

        if (data.status === "success") {
            renderBulkGeneratedImages(data.data);
        } else {
            showError(data.message);
        }
    } catch (err) {
        showError("Bağlantı hatası: " + err.message);
    }
}

/// ==========================================
// MOCKUP AŞAMASI YÖNETİMİ
// ==========================================

// 1. AI Üretim Ekranında "İşlendi" Durumunu Otomatik Göster
function renderBulkGeneratedImages(groupedData) {
    localStorage.setItem('last_generated_results', JSON.stringify(groupedData));
    const container = document.getElementById('generated-images-container');
    container.innerHTML = ''; 
    
    let hasAnyProcessed = false;

    for (const [productId, images] of Object.entries(groupedData)) {
        let groupHtml = `<div class="col-span-full mt-6 border-b pb-2"><h3 class="font-bold text-slate-700 uppercase text-xs tracking-wider">Ürün: ${productId}</h3></div>`;
        
        images.forEach(img => {
            // Backend'den gelen 'is_processed' flag'ine bak
            const isProcessed = img.is_processed === true;
            if (isProcessed) hasAnyProcessed = true;
            
            groupHtml += `
                <div class="bg-white border ${isProcessed ? 'border-emerald-500 ring-2 ring-emerald-50' : 'border-slate-200'} rounded-xl p-3 relative group shadow-sm transition-all">
                    <input type="checkbox" class="gen-checkbox absolute top-4 left-4 w-5 h-5 z-10" data-id="${img.id}">
                    <img src="${img.src}" onclick="openModal('${img.src}')" class="w-full h-48 object-contain rounded-lg cursor-zoom-in">
                    <div class="mt-2 flex justify-between items-center">
                        <span class="text-[10px] font-bold text-slate-400 uppercase">${img.model}</span>
                        ${isProcessed ? '<span class="text-[10px] text-emerald-600 bg-emerald-50 px-2 py-1 rounded font-bold flex items-center gap-1"><i class="fa-solid fa-check"></i> İŞLENDİ</span>' : ''}
                    </div>
                </div>`;
        });
        container.insertAdjacentHTML('beforeend', groupHtml);
    }
    
    // İşlenmiş görsel varsa Mockup butonunu görünür yap
    const mockupBtn = document.getElementById('btn-go-to-mockup');
    if (mockupBtn) {
        if (hasAnyProcessed) mockupBtn.classList.remove('hidden');
        else mockupBtn.classList.add('hidden');
    }
}



// ==========================================
// EKRANLAR ARASI GEÇİŞ YÖNETİMİ
// ==========================================
function goToAnalyzePage() {
    document.getElementById('page-generate').classList.add('hidden');
    document.getElementById('page-analyze').classList.remove('hidden');
    saveAppState('page-analyze'); // Sayfa durumunu analiz olarak kaydet
}

// ==========================================
// SEÇİLİ GÖRSELLERİ İŞLEME (UPSCALE & BG REMOVAL)
// ==========================================

async function processSelectedImages() {
    const selectedCheckboxes = document.querySelectorAll('.gen-checkbox:checked');
    const selectedIds = Array.from(selectedCheckboxes).map(cb => cb.dataset.id);

    if (selectedIds.length === 0) { alert("Lütfen işlenecek varyasyon seçin."); return; }

    const processOrder = document.getElementById('process-order').value;
    const btn = document.getElementById('btn-process-images');
    const originalBtnHtml = btn.innerHTML;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> İşleniyor...`;
    btn.disabled = true;

    try {
        const response = await fetch('/ai/api/process-selected/', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') || '' },
            body: JSON.stringify({ selected_ids: selectedIds, process_order: processOrder }) 
        });
        const data = await response.json();

        if (data.status === "success") {
            // KRİTİK: Hafızadaki listeyi güncelle ki Mockup sayfasına gitsin
            let savedGenerated = JSON.parse(localStorage.getItem('last_generated_results'));
            
            data.images.forEach(processedImg => {
                // Ekranda güncelle
                const checkbox = document.querySelector(`.gen-checkbox[data-id="${processedImg.id}"]`);
                if (checkbox) {
                    const card = checkbox.parentElement;
                    card.classList.add('border-emerald-500', 'ring-2', 'ring-emerald-50');
                    const imgElement = checkbox.nextElementSibling;
                    imgElement.src = processedImg.src; // Arkaplansız resim
                    imgElement.nextElementSibling.innerHTML += `<span class="text-[10px] text-emerald-600 bg-emerald-50 px-2 py-1 rounded font-bold flex items-center gap-1"><i class="fa-solid fa-check"></i> İŞLENDİ</span>`;
                }

                // Cache'de güncelle
                for (const prodId in savedGenerated) {
                    let targetImg = savedGenerated[prodId].find(i => String(i.id) === String(processedImg.id));
                    if (targetImg) {
                        targetImg.is_processed = true;
                        targetImg.src = processedImg.src;
                        targetImg.no_bg_src = processedImg.src;
                    }
                }
            });
            
            // Güncellenmiş cache'i tekrar kaydet ve Mockup butonunu aç
            localStorage.setItem('last_generated_results', JSON.stringify(savedGenerated));
            document.getElementById('btn-go-to-mockup').classList.remove('hidden');

        } else { alert("Hata: " + data.message); }
    } catch (err) { alert("Bağlantı hatası: " + err.message); } 
    finally { btn.innerHTML = originalBtnHtml; btn.disabled = false; }
}


function addMockupStepButton() {
    const existingBtn = document.getElementById('btn-go-to-mockup');
    if (existingBtn) existingBtn.remove();

    const container = document.querySelector('#page-generate .flex.justify-between');
    const mockupBtn = `<button id="btn-go-to-mockup" onclick="goToMockupStage()" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2.5 px-8 rounded-lg shadow-lg transition flex items-center gap-2 transform hover:scale-105">
        İleri: Mockup Hazırla <i class="fa-solid fa-chevron-right"></i>
    </button>`;
    container.insertAdjacentHTML('beforeend', mockupBtn);
}

// 2. MOCKUP SAYFASINA GEÇİŞ VE RENDER
async function goToMockupStage() {
    document.getElementById('page-generate').classList.add('hidden');
    document.getElementById('page-mockup').classList.remove('hidden');
    saveAppState('page-mockup');

    const seoContainer = document.getElementById('seo-button-container');
    if(seoContainer) seoContainer.classList.add('hidden');

    const savedGenerated = JSON.parse(localStorage.getItem('last_generated_results'));
    const transparentImages = [];
    
    // Filtreleme mantığı artık URL ismine değil 'is_processed' flag'ine bakıyor
    for (const prodId in savedGenerated) {
        savedGenerated[prodId].forEach(img => {
            if (img.is_processed === true && img.no_bg_src) {
                transparentImages.push(img);
            }
        });
    }

    renderMockupDesigns(transparentImages);
    fetchMockupTemplates();
}



// ==========================================
// ESNEK MOCKUP EŞLEŞTİRME (SATIR MANTIĞI)
// ==========================================

function goToGeneratePage() {
    document.getElementById('page-mockup').classList.add('hidden');
    document.getElementById('page-analyze').classList.add('hidden');
    document.getElementById('page-generate').classList.remove('hidden');
    saveAppState('page-generate');
}

let mockupMapping = {}; 
let allTemplates = []; 
let activeMockupDesignId = null;

// 1. TÜMÜNÜ SEÇ / TEMİZLE
function toggleAllMockupDesigns(masterCheckbox) {
    const isChecked = masterCheckbox.checked;
    const checkboxes = document.querySelectorAll('.mockup-design-checkbox');
    
    checkboxes.forEach(cb => {
        cb.checked = isChecked;
        const strId = cb.dataset.id;
        const row = document.getElementById(`design-row-${strId}`);
        if (isChecked) {
            row.classList.add('border-indigo-600', 'bg-indigo-50');
        } else {
            row.classList.remove('border-indigo-600', 'bg-indigo-50');
        }
    });
    updateTemplateGridUI();
}

function setActiveDesign(designId) {
    activeMockupDesignId = String(designId);

    // Tüm satırların mavi vurgusunu kaldır (Eski seçimleri sıfırla)
    document.querySelectorAll('.design-row').forEach(row => {
        row.classList.remove('border-2', 'border-indigo-500', 'bg-indigo-50');
    });

    // Sadece üzerine son tıklananı/aktif olanı mavi yap
    const activeRow = document.getElementById(`design-row-${activeMockupDesignId}`);
    if (activeRow) {
        activeRow.classList.add('border-2', 'border-indigo-500', 'bg-indigo-50');
    }
}

function handleRowClick(strId) {
    const cb = document.getElementById(`checkbox-${strId}`);
    cb.checked = !cb.checked; // Tıklayınca kutuyu işaretle/kaldır
    handleCheckboxClick(strId);
    checkMasterCheckbox();
}

function handleCheckboxClick(strId) {
    const cb = document.getElementById(`checkbox-${strId}`);
    if (cb.checked) {
        // Diğer satırların mavisini sil, sadece bunu mavi yap (tikleri elleme)
        document.querySelectorAll('.design-row').forEach(row => row.classList.remove('border-indigo-600', 'bg-indigo-50'));
        const row = document.getElementById(`design-row-${strId}`);
        if (row) row.classList.add('border-indigo-600', 'bg-indigo-50');
    } else {
        // Tiki kaldırırsa mavisini de kaldır
        const row = document.getElementById(`design-row-${strId}`);
        if (row) row.classList.remove('border-indigo-600', 'bg-indigo-50');
    }
    updateTemplateGridUI();
}

// Checkbox elle işaretlendiğinde çalışır
function checkMasterCheckbox() {
    const allBoxes = document.querySelectorAll('.mockup-design-checkbox').length;
    const checkedBoxes = document.querySelectorAll('.mockup-design-checkbox:checked').length;
    const masterBox = document.getElementById('select-all-mockup-designs');
    
    if (masterBox) {
        // Eğer işaretli kutu sayısı toplamdan azsa "Tümünü Seç" tikini kaldır.
        // AMA hepsi elle seçildiyse "Tümünü Seç"i otomatik İŞARETLEME!
        if (checkedBoxes < allBoxes) {
            masterBox.checked = false;
        }
    }
}

function updateRowStyle(checkbox) {
    const row = checkbox.closest('.design-row');
    if (checkbox.checked) {
        row.classList.add('bg-indigo-50/50', 'border-indigo-300');
    } else {
        row.classList.remove('bg-indigo-50/50', 'border-indigo-300');
    }
}

// 2. TASARIMLARI SATIR SATIR (ROW) EKRANA BAS
function renderMockupDesigns(images) {
    const list = document.getElementById('mockup-designs-list');
    list.innerHTML = images.length === 0 ? '<p class="text-slate-400 text-sm italic">Henüz işlenmiş tasarım yok.</p>' : '';
    
    mockupMapping = {}; 
    activeMockupDesignId = null; // Sayfa açıldığında sıfırla
    const masterBox = document.getElementById('select-all-mockup-designs');
    if (masterBox) masterBox.checked = false;

    images.forEach((img) => {
        const strId = String(img.id); 
        mockupMapping[strId] = []; // Her tasarım için şablon sepeti

        // DİKKAT: onclick olayından "cb.checked = !cb.checked" SİLİNDİ.
        // Artık satıra tıklamak SADECE o satırı mavi yapar (setActiveDesign).
        const itemHtml = `
            <div id="design-row-${strId}" class="design-row flex flex-col md:flex-row gap-4 p-3 border border-slate-200 rounded-xl transition items-start md:items-center cursor-pointer hover:border-indigo-200" onclick="setActiveDesign('${strId}')">
                
                <div class="flex items-center gap-4 w-full md:w-1/4 md:border-r border-slate-200 pr-4">
                    <input type="checkbox" class="mockup-design-checkbox w-6 h-6 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer shadow-sm" 
                        data-id="${strId}" onclick="event.stopPropagation()" onchange="checkMasterCheckbox();">
                    
                    <img src="${img.src}" onclick="event.stopPropagation(); openModal('${img.src}')" class="w-16 h-16 object-contain rounded bg-white border border-slate-100 cursor-zoom-in">
                    
                    <div class="text-xs font-bold text-slate-500">ID: ${strId}</div>
                </div>
                
                <div class="flex-1 flex flex-wrap gap-2 items-center min-h-[4rem]" id="selected-templates-for-${strId}">
                    <p class="text-xs text-slate-400 italic">Şablon seçilmedi. Satıra tıklayıp yukarıdan şablon ekleyin.</p>
                </div>
            </div>`;
        list.insertAdjacentHTML('beforeend', itemHtml);
    });

    // İlk tasarımı otomatik aktif (mavi) yap
    if (images.length > 0) {
        setActiveDesign(String(images[0].id));
    }
}


// 3. ŞABLONA TIKLANDIĞINDA ÇALIŞACAK MANTIK

function toggleTemplateSelect(templateId) {
    templateId = String(templateId); 
    
    // 1. "Tümünü Seç" kutusu işaretli mi kontrol et
    const masterBox = document.getElementById('select-all-mockup-designs');
    const isSelectAllChecked = masterBox && masterBox.checked;

    let targetDesignIds = [];

    if (isSelectAllChecked) {
        // Eğer "Tümünü Seç" aktifse, ekrandaki TÜM tasarımlara uygula
        targetDesignIds = Object.keys(mockupMapping);
    } else {
        // Tümünü seç aktif değilse, SADECE üzerine son tıklanan (Mavi olan) satıra uygula
        if (!activeMockupDesignId) { 
            alert("Lütfen önce şablon eklemek istediğiniz tasarımın satırına tıklayın."); 
            return; 
        }
        targetDesignIds = [activeMockupDesignId];
    }

    // Belirlenen hedeflere şablonu ekle veya çıkar
    targetDesignIds.forEach(designId => {
        const templates = mockupMapping[designId];
        const index = templates.indexOf(templateId);
        
        if (index === -1) {
            templates.push(templateId); // Ekle
            const cb = document.querySelector(`.mockup-design-checkbox[data-id="${activeMockupDesignId}"]`);
            if (cb && !cb.checked) {
                cb.checked = true; // Kutucuğu işaretle
            
                // Eğer varsa UI güncelleme fonksiyonlarını tetikle ki görsellik bozulmasın
                if (typeof updateRowStyle === 'function') updateRowStyle(cb); 
                if (typeof checkMasterCheckbox === 'function') checkMasterCheckbox(); 
            }
        } else {
            templates.splice(index, 1); // Zaten varsa Çıkar
        }
        
        // Senin çalışan ÇİZİM fonksiyonunu (updateRowTemplatesUI) çağırır!
        updateRowTemplatesUI(designId);
    });
}

// 4. SATIRIN İÇİNDEKİ ŞABLONLARI ÇİZ
function updateRowTemplatesUI(designId) {
    const container = document.getElementById(`selected-templates-for-${designId}`);
    const selectedIds = mockupMapping[designId];
    
    if (selectedIds.length === 0) {
        container.innerHTML = `<p class="text-xs text-slate-400 italic">Şablon seçilmedi. Kutuyu işaretleyip yukarıdan şablona tıklayın.</p>`;
        return;
    }

    container.innerHTML = '';
    selectedIds.forEach(tplId => {
        const tplData = allTemplates.find(t => String(t.id) === tplId);
        if (tplData) {
            const badgeHtml = `
            <div class="relative group cursor-pointer" title="Şablonu Kaldır" onclick="event.stopPropagation(); removeTemplateFromDesign('${designId}', '${tplId}')">
                <img src="${tplData.image_url}" class="w-16 h-16 object-cover rounded-lg border-2 border-indigo-500 shadow-sm">
                <div class="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-[10px] shadow opacity-0 group-hover:opacity-100 transition"><i class="fa-solid fa-xmark"></i></div>
            </div>`;
            container.insertAdjacentHTML('beforeend', badgeHtml);
        }
    });
}
// 5. ŞABLONU SATIRDAN KALDIRMA (ÇARPIYA BASINCA)
function removeTemplateFromDesign(designId, templateId) {
    const templates = mockupMapping[designId];
    const index = templates.indexOf(templateId);
    if (index > -1) {
        templates.splice(index, 1);
        updateRowTemplatesUI(designId);
    }
}

// 6. ŞABLONLARI VERİTABANINDAN ÇEK
async function fetchMockupTemplates() {
    const grid = document.getElementById('mockup-templates-grid');
    grid.innerHTML = '<div class="col-span-full text-center py-10"><i class="fa-solid fa-spinner fa-spin text-3xl text-indigo-500 mb-3"></i></div>';
    allTemplates = []; // Hafızayı sıfırla

    try {
        const response = await fetch('/image_processor/api/get-templates/');
        if (!response.ok) throw new Error(`Sunucu Hatası: ${response.status}`);
        const data = await response.json();
        
        if (!data.templates || data.templates.length === 0) {
            grid.innerHTML = `<div class="col-span-full text-center py-6 bg-slate-50 rounded-xl border-2 border-dashed border-slate-300"><p class="text-slate-500 font-bold">Mockup Şablonu Yok</p></div>`;
            return;
        }

        grid.innerHTML = '';
        allTemplates = data.templates; // Gelen şablonları global hafızaya kaydet

        allTemplates.forEach(tpl => {
            const strTplId = String(tpl.id);
            const tplHtml = `
                <div class="relative cursor-pointer group hover:-translate-y-1 transition transform" onclick="toggleTemplateSelect('${strTplId}')">
                    <div class="border-2 border-slate-200 rounded-xl overflow-hidden shadow-sm group-hover:border-indigo-400">
                        <img src="${tpl.image_url}" class="w-full h-24 object-cover bg-white">
                        <div class="absolute bottom-0 w-full bg-slate-900/70 text-white text-[10px] p-1.5 text-center font-bold truncate backdrop-blur-sm">${tpl.title}</div>
                    </div>
                </div>`;
            grid.insertAdjacentHTML('beforeend', tplHtml);
        });
        
    } catch (err) {
        console.error("Şablon Hatası:", err);
        grid.innerHTML = `<p class="text-red-500 text-sm">Şablonlar yüklenemedi: ${err.message}</p>`;
    }
}

// ==========================================
// MOCKUP ÜRETİMİ VE GALERİ (CAROUSEL) YÖNETİMİ
// ==========================================

// Gelen API sonuçlarını hafızada tutarız ki modal açılınca resimler arasında gezilebilsin
let generatedMockupsCache = {};

async function startMockupGeneration(force = false) {
    const payload = {};
    let totalMockups = 0;
    
    const checkedBoxes = document.querySelectorAll('.mockup-design-checkbox:checked');
    if (checkedBoxes.length === 0) { alert("Lütfen üretime gönderilecek tasarımları işaretleyin."); return; }

    checkedBoxes.forEach(cb => {
        const designId = String(cb.dataset.id);
        const templates = mockupMapping[designId];
        if (templates && templates.length > 0) {
            payload[designId] = templates;
            totalMockups += templates.length;
        }
    });

    const btn = document.querySelector('button[onclick="startMockupGeneration()"]');
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Üretiliyor...`;
    btn.disabled = true;

    try {
        const response = await fetch('/image_processor/api/generate-mockups/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') || '' },
            body: JSON.stringify({ mapping: payload, force_recreate: force })
        });
        
        const data = await response.json();
        
        if (data.status === "success") {
            generatedMockupsCache = data.results; 
            // urls yerine groupsData geliyor
            for (const [designId, groupsData] of Object.entries(data.results)) {
                renderGeneratedMockupsUI(designId, groupsData);
            }
            
            saveAppState('page-mockup');
            showSEOButton(); 
        }
    } catch (err) {
        alert("Bağlantı hatası: " + err.message);
    } finally {
        btn.innerHTML = `<i class="fa-solid fa-play"></i> Mockupları Üret`;
        btn.disabled = false;
    }
}



// ÜRETİLEN GÖRSELLERİ SATIR İÇİNDE "TEK BİR KAPAK" OLARAK GÖSTERİR
function renderGeneratedMockupsUI(designId, groupsData) {
    if (!groupsData || Object.keys(groupsData).length === 0) return;
    
    const container = document.getElementById(`selected-templates-for-${designId}`);
    if (!container) return;
    
    // Albümde (Carousel) açılabilmesi için tüm resimleri önbelleğe al
    if (!generatedMockupsCache[designId]) generatedMockupsCache[designId] = {};
    generatedMockupsCache[designId] = groupsData;
    
    let htmlContent = `<div class="flex flex-wrap items-center gap-4 animate-fade-in w-full">`;
    let totalProcessed = 0;

    // Her bir şablon grubu için ayrı bir kapak fotoğrafı basıyoruz
    for (const [groupId, urls] of Object.entries(groupsData)) {
        if (!urls || urls.length === 0) continue;
        totalProcessed += urls.length;
        
        const coverUrl = urls[0]; // Sadece o şablonun ilk resmi kapak olur
        
        htmlContent += `
        <div class="relative group cursor-pointer border-2 border-emerald-500 rounded-lg p-1 bg-white w-24 h-24 flex-shrink-0 shadow-md" 
             onclick="event.stopPropagation(); openMockupCarousel('${designId}', '${groupId}', 0)">
             
            <div class="absolute -top-2 -right-2 bg-emerald-600 text-white text-[11px] font-bold px-2 py-0.5 rounded-full z-20 shadow border border-white">
                ${urls.length} Görsel
            </div>
            
            <img src="${coverUrl}" class="w-full h-full object-cover rounded shadow-sm group-hover:opacity-75 transition duration-300">
            
            <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition z-20">
                <i class="fa-solid fa-images text-emerald-600 text-3xl drop-shadow-lg"></i>
            </div>
        </div>`;
    }
    
    htmlContent += `
        <div class="text-xs text-emerald-700 font-bold bg-emerald-50 px-4 py-2.5 rounded-lg border border-emerald-100 ml-auto flex items-center gap-2">
            <i class="fa-solid fa-circle-check text-lg"></i> Toplam ${totalProcessed} Hazır
        </div>
    </div>`;
    
    container.innerHTML = htmlContent;
}

// ==========================================
// GALERİ (CAROUSEL) YÖNETİMİ
// ==========================================
let currentCarouselImages = [];
let currentCarouselIndex = 0;

// Tekli resim açma (Eski Modalın Yedeği)
function openModal(src) {
    currentCarouselImages = [src];
    currentCarouselIndex = 0;
    updateModalUI();
    showModal();
}

// Çoklu Mockup Galerisi Açma
function openMockupCarousel(designId, groupId, startIndex = 0) {
    if (!generatedMockupsCache[designId] || !generatedMockupsCache[designId][groupId] || generatedMockupsCache[designId][groupId].length === 0) return;
    
    currentCarouselImages = generatedMockupsCache[designId][groupId];
    currentCarouselIndex = startIndex;
    
    updateModalUI();
    showModal();
}

function changeCarousel(direction) {
    currentCarouselIndex += direction;
    // Başa veya sona sarma (Sonsuz Döngü)
    if (currentCarouselIndex < 0) currentCarouselIndex = currentCarouselImages.length - 1;
    if (currentCarouselIndex >= currentCarouselImages.length) currentCarouselIndex = 0;
    
    updateModalUI();
}

function updateModalUI() {
    const img = document.getElementById('modal-image');
    const prevBtn = document.getElementById('modal-prev-btn');
    const nextBtn = document.getElementById('modal-next-btn');
    const counter = document.getElementById('modal-counter');

    img.src = currentCarouselImages[currentCarouselIndex];

    if (currentCarouselImages.length > 1) {
        prevBtn.classList.remove('hidden');
        nextBtn.classList.remove('hidden');
        counter.classList.remove('hidden');
        counter.innerText = `${currentCarouselIndex + 1} / ${currentCarouselImages.length}`;
    } else {
        prevBtn.classList.add('hidden');
        nextBtn.classList.add('hidden');
        counter.classList.add('hidden');
    }
}

function showModal() {
    const modal = document.getElementById('image-modal');
    modal.classList.remove('hidden');
    setTimeout(() => modal.classList.add('opacity-100'), 10);
}

function closeModal() {
    const modal = document.getElementById('image-modal');
    modal.classList.remove('opacity-100');
    setTimeout(() => modal.classList.add('hidden'), 300);
}

// SEO Butonunu dinamik olarak ekle veya göster
function showSEOButton() {
    const seoContainer = document.getElementById('seo-button-container');
    if (seoContainer) {
        seoContainer.classList.remove('hidden');
    }
}

// ==========================================
// 4. AŞAMA: SEO ÜRETİMİ (SATIR BAZLI)
// ==========================================

// A. SEO Sayfasına Geçiş Yapan Güvenli Fonksiyon
function goToSEOPage() {
    const pageMockup = document.getElementById('page-mockup');
    const pageSeo = document.getElementById('page-seo');
    const container = document.getElementById('seo-rows-container');
    saveAppState('page-seo');

    if (!pageSeo || !container) {
        alert("HATA: HTML şablonunuzda 'page-seo' veya 'seo-rows-container' bulunamadı! HTML kodunuzu kontrol edin.");
        return;
    }

    if (pageMockup) pageMockup.classList.add('hidden');
    pageSeo.classList.remove('hidden');
    saveAppState('page-seo'); // Hafızaya SEO sayfasında olduğumuzu kaydeder
    
    container.innerHTML = '';

    for (const [designId, groupsData] of Object.entries(generatedMockupsCache)) {
        if (!groupsData || Object.keys(groupsData).length === 0) continue;
        
        let mockupsHtml = `<div class="flex flex-wrap gap-3 w-full justify-center md:justify-start">`;
        for (const [groupId, urls] of Object.entries(groupsData)) {
            if (!urls || urls.length === 0) continue;
            const coverUrl = urls[0]; 
            
            mockupsHtml += `
            <div class="w-20 h-20 flex-shrink-0 cursor-pointer relative group bg-white border border-slate-200 rounded-lg p-1 shadow-sm" onclick="openMockupCarousel('${designId}', '${groupId}', 0)">
                <div class="absolute -top-2 -right-2 bg-emerald-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full z-20 shadow">${urls.length}</div>
                <img src="${coverUrl}" class="w-full h-full object-cover rounded group-hover:opacity-75 transition">
                <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition z-20"><i class="fa-solid fa-search-plus text-emerald-600 text-xl drop-shadow-md"></i></div>
            </div>`;
        }
        mockupsHtml += `</div>`;

        const rowHtml = `
        <div class="flex flex-col md:flex-row gap-6 p-4 border border-slate-200 rounded-xl bg-slate-50 items-center seo-row shadow-sm" data-id="${designId}">
            
            <div class="w-full md:w-auto flex flex-col items-center gap-1 border-b md:border-b-0 md:border-r border-slate-200 pb-4 md:pb-0 md:pr-4">
                ${mockupsHtml}
                <div class="text-[10px] text-center mt-2 font-bold text-slate-500 bg-slate-200 px-2 py-1 rounded">Tasarım ID: ${designId}</div>
            </div>

            <div class="w-full md:w-40 flex-shrink-0 flex flex-col justify-center space-y-1.5 border-b md:border-b-0 md:border-r border-slate-200 pb-4 md:pb-0 md:pr-4">
                <label class="text-[11px] font-bold text-slate-400 uppercase mb-1">Ne Üretilsin?</label>
                <label class="flex items-center gap-2 text-xs font-semibold cursor-pointer hover:text-indigo-600"><input type="radio" name="seo_target_${designId}" value="both" checked class="text-indigo-600 focus:ring-indigo-500"> İkisi Birden</label>
                <label class="flex items-center gap-2 text-xs font-semibold cursor-pointer hover:text-indigo-600"><input type="radio" name="seo_target_${designId}" value="title" class="text-indigo-600 focus:ring-indigo-500"> Sadece Title</label>
                <label class="flex items-center gap-2 text-xs font-semibold cursor-pointer hover:text-indigo-600"><input type="radio" name="seo_target_${designId}" value="tags" class="text-indigo-600 focus:ring-indigo-500"> Sadece Tag</label>
                <label class="flex items-center gap-2 text-xs font-semibold cursor-pointer hover:text-red-500 text-slate-400 mt-1 pt-1 border-t border-slate-200"><input type="radio" name="seo_target_${designId}" value="none" class="text-red-500 focus:ring-red-500"> Pasif</label>
            </div>

            <div class="flex-grow w-full space-y-3 relative">
                <div id="seo-loading-${designId}" class="hidden absolute inset-0 bg-white/60 backdrop-blur-sm z-10 flex items-center justify-center rounded-lg"><i class="fa-solid fa-circle-notch fa-spin text-3xl text-emerald-500"></i></div>
                <div>
                    <label class="block text-[11px] font-bold text-slate-500 mb-1 uppercase">Generated Title</label>
                    <input type="text" id="seo-title-${designId}" class="w-full p-2.5 text-sm border border-slate-300 rounded-lg bg-white text-slate-800 font-bold focus:ring-emerald-500 focus:border-emerald-500" placeholder="Henüz üretilmedi...">
                </div>
                <div>
                    <label class="block text-[11px] font-bold text-slate-500 mb-1 uppercase">Generated Tags</label>
                    <textarea id="seo-tags-${designId}" rows="2" class="w-full p-2.5 text-sm border border-slate-300 rounded-lg bg-white text-slate-600 focus:ring-emerald-500 focus:border-emerald-500" placeholder="Henüz üretilmedi..."></textarea>
                </div>
            </div>
        </div>`;
        
        container.insertAdjacentHTML('beforeend', rowHtml);
    }

    checkExistingSEO();
}

async function checkExistingSEO() {
    const tasks = [];
    const rows = document.querySelectorAll('.seo-row');
    
    // Ekrandaki tüm tasarım ID'lerini topla
    rows.forEach(row => {
        tasks.push({ design_id: row.dataset.id, target: 'both' });
    });

    if (tasks.length === 0) return;

    try {
        // Mevcut generate-seo-batch API'sini "sessizce" çağırıyoruz
        const response = await fetch('/ai/api/generate-seo-batch/', { 
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') || ''
            },
            body: JSON.stringify({ tasks: tasks, niche: 'Jewelry' })
        });
        
        const data = await response.json();

        if (data.status === "success" && Object.keys(data.results).length > 0) {
            // Eğer veritabanında kayıtlı veri varsa kutuları doldur
            for (const [d_id, res] of Object.entries(data.results)) {
                if (res.title) document.getElementById(`seo-title-${d_id}`).value = res.title;
                if (res.tags) document.getElementById(`seo-tags-${d_id}`).value = res.tags;
                
                const row = document.querySelector(`.seo-row[data-id="${d_id}"]`);
                if (row) row.classList.add('border-emerald-500', 'bg-emerald-50');
            }
            // EN ÖNEMLİSİ: Veri bulunduğu için İndir butonunu görünür yap
            document.getElementById('export-container')?.classList.remove('hidden');
            
            // Local hafızayı da güncelle
            saveAppState('page-seo', { seoResults: data.results });
        }
    } catch (err) {
        console.warn("Otomatik SEO kontrolü yapılamadı:", err);
    }
}

// Tüm Radyo Butonlarını Tek Seferde Değiştirir
function setGlobalSeoTarget(targetValue) {
    const rows = document.querySelectorAll('.seo-row');
    rows.forEach(row => {
        const designId = row.dataset.id;
        const radio = document.querySelector(`input[name="seo_target_${designId}"][value="${targetValue}"]`);
        if (radio) radio.checked = true;
    });
}

async function startBatchSEO() {
    const tasks = [];
    const rows = document.querySelectorAll('.seo-row');
    
    rows.forEach(row => {
    const d_id = row.dataset.id;
    // DÜZELTME: Name kısmına 'seo_' ön ekini ekledik
    const targetRadio = document.querySelector(`input[name="seo_target_${d_id}"]:checked`);
    
    if (targetRadio) {
        const target = targetRadio.value;
        if (target !== 'none') {
            tasks.push({ design_id: d_id, target: target });
            const loader = document.getElementById(`seo-loading-${d_id}`);
            if (loader) loader.classList.remove('hidden');
        }
    }
    });

    if (tasks.length === 0) {
        return alert("Lütfen en az bir üretim seçeneği işaretleyin!");
    }

    const btn = document.getElementById('btn-start-seo');
    const originalText = btn.innerHTML;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Üretiliyor...`;
    btn.disabled = true;

    try {
        const response = await fetch('/ai/api/generate-seo-batch/', { 
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') || ''
            },
            body: JSON.stringify({ tasks: tasks, niche: 'Graphic T-Shirt' })
        });
        
        // Önce veriyi text olarak alalım
        const rawText = await response.text(); 
        
        // 1. EĞER SUNUCU HATA DÖNDÜRDÜYSE (404, 500 vb.)
        if (!response.ok) {
            console.error("🚨 SUNUCUDAN GELEN HATA SAYFASI:", rawText);
            alert(`HATA KODU: ${response.status}\nLütfen terminale (Django'nun çalıştığı siyah ekran) veya F12 Console sekmesine bakın.`);
            btn.disabled = false; 
            btn.innerHTML = originalText;
            document.querySelectorAll('[id^="seo-loading-"]').forEach(el => el.classList.add('hidden'));
            return; // İşlemi durdur
        }

        // 2. EĞER HER ŞEY YOLUNDAYSA JSON'A ÇEVİR
        const data = JSON.parse(rawText);

        if (data.status === "success") {
            for (const [d_id, res] of Object.entries(data.results)) {
                
                const exportDiv = document.getElementById('export-container');
                if(exportDiv) {
                    exportDiv.classList.remove('hidden');
                    exportDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }

                if (res.title) document.getElementById(`seo-title-${d_id}`).value = res.title;
                if (res.tags) document.getElementById(`seo-tags-${d_id}`).value = res.tags;
                
                const loader = document.getElementById(`seo-loading-${d_id}`);
                if (loader) loader.classList.add('hidden');
                
                const row = document.querySelector(`.seo-row[data-id="${d_id}"]`);
                if (row) row.classList.add('border-emerald-500', 'bg-emerald-50');
                saveAppState('page-seo', { seoResults: data.results });
            }
            alert("SEO Başarıyla Üretildi!");
        } else {
            alert("Üretim Hatası: " + data.message);
        }
    } catch (err) { 
        alert("Sistem/Parse Hatası: " + err.message); 
    } finally { 
        btn.disabled = false; 
        btn.innerHTML = originalText;
        document.querySelectorAll('[id^="seo-loading-"]').forEach(el => el.classList.add('hidden'));
    }
}

async function exportPipeline1() {
    // Üretimi yapılmış (cache'de olan) tasarım ID'lerini topla
    const designIds = Object.keys(generatedMockupsCache);
    
    if (designIds.length === 0) {
        alert("İndirilecek hazır tasarım bulunamadı.");
        return;
    }

    const btn = document.getElementById('btn-export-pipeline1');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Paket Hazırlanıyor...';
    btn.disabled = true;

    try {
        // İSTEK ARTIK common ALTINDAKİ YENİ URL'E GİDİYOR
        const response = await fetch('/common/api/export-pipeline1/', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') || ''
            },
            body: JSON.stringify({ design_ids: designIds })
        });

        if (!response.ok) throw new Error("ZIP paketi oluşturulurken bir hata oluştu.");

        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `Etsy_Project_${new Date().getTime()}.zip`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);

    } catch (err) {
        alert("Export Hatası: " + err.message);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}