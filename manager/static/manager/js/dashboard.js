        // Mevcut İşlemdeki Ürün State'i (Sayfalar arası veri taşımak için)
let currentActiveProduct = null;


        // --- SAYFA GEÇİŞLERİ VE GÖRÜNÜM KONTROLLERİ ---
const pageAnalyze = document.getElementById('page-analyze');
const pageGenerate = document.getElementById('page-generate');

// --- SAYFA GEÇİŞLERİ VE GÖRÜNÜM KONTROLLERİ ---
function selectPipeline(pipelineId) {
    const pipe1Container = document.getElementById('pipeline-1-container');
    const pipe2Container = document.getElementById('pipeline-2-container');
    
    // Kartların renklerini yönetmek için (Opsiyonel ama şık durur)
    const card1 = document.querySelector('[onclick="selectPipeline(\'pipeline-1\')"]');
    const card2 = document.getElementById('card-pipe-2');

    if(pipelineId === 'pipeline-1') {
        pipe1Container.classList.remove('hidden');
        if (pipe2Container) pipe2Container.classList.add('hidden');
        
        card1.classList.add('border-orange-500');
        if (card2) card2.classList.remove('border-indigo-500');
    } else if (pipelineId === 'pipeline-2') {
        if (pipe1Container) pipe1Container.classList.add('hidden');
        pipe2Container.classList.remove('hidden');
        
        if (card1) card1.classList.remove('border-orange-500');
        card2.classList.add('border-indigo-500');
    }
}

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


// --- 3. AŞAMAYA GEÇİŞ ---
function goToMockupStep() {
    const checkboxes = document.querySelectorAll('.proc-checkbox');
    let hasSelection = false;
    checkboxes.forEach(cb => { if(cb.checked) hasSelection = true; });

    if(!hasSelection) {
        alert("Mockup giydirmek için en az 1 transparan görsel seçili olmalıdır.");
        return;
    }
    
    document.getElementById('mockup-section').classList.remove('hidden');
    document.getElementById('mockup-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// --- MOCKUP MOTORUNU TETİKLEME ---
async function applyMockups(force = false) {
    const groupId = document.getElementById('mockup-group-select').value;
    if(!groupId) {
        alert("Lütfen bir Mockup Koleksiyonu seçin.");
        return;
    }

    // Seçili tasarımların ID'lerini topla
    const checkboxes = document.querySelectorAll('.proc-checkbox');
    let selectedDesignIds = [];
    checkboxes.forEach(cb => { 
        if(cb.checked) selectedDesignIds.push(parseInt(cb.dataset.id)); 
    });

    document.getElementById('loading-mockups').classList.remove('hidden');
    document.getElementById('generated-mockups-container').innerHTML = '';
    document.getElementById('proceed-seo-btn-container').classList.add('hidden');
    
    // Varsa eski 'Yeniden Üret' butonunu gizle
    const oldRegenBtn = document.getElementById('regen-mockup-btn');
    if(oldRegenBtn) oldRegenBtn.remove();

    try {
        const response = await fetch('/apply-mockups/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                product_id: currentActiveProduct.id,
                design_ids: selectedDesignIds,
                group_id: groupId,
                force_recreate: force // Backend'e "Klasörü boşver, baştan yap" sinyali
            })
        });

        const data = await response.json();
        document.getElementById('loading-mockups').classList.add('hidden');

        if (data.status === "success") {
            const container = document.getElementById('generated-mockups-container');
            
            // Resimleri ekrana bas
            data.mockups.forEach((url, idx) => {
                container.innerHTML += `
                    <div class="border rounded shadow-sm p-1">
                        <img src="${url}" class="w-full h-32 object-cover rounded cursor-pointer zoomable" onclick="openModal(this.src)">
                    </div>
                `;
            });
            
            document.getElementById('proceed-seo-btn-container').classList.remove('hidden');
            
            // Eğer Backend "Bunların hepsini klasörden hazır getirdim" derse
            // Kullanıcıya şablon değişmiş olma ihtimaline karşı "Yeniden Üret" seçeneği sunalım
            if (data.cached) {
                const regenBtnHtml = `
                    <div id="regen-mockup-btn" class="col-span-full flex justify-center mt-2">
                        <button onclick="applyMockups(true)" class="bg-gray-200 hover:bg-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm transition-all flex items-center gap-2">
                            <i class="fa-solid fa-rotate-right"></i> Şablonları Değiştirdiyseniz: Baştan Üret (Zorla)
                        </button>
                    </div>
                `;
                container.innerHTML += regenBtnHtml;
            }
            
        } else {
            alert("Mockup Hatası: " + data.message);
        }
    } catch (err) {
        document.getElementById('loading-mockups').classList.add('hidden');
        alert("Bağlantı hatası: " + err.message);
    }
}

        // --- 4. AŞAMA: SEÇİLİ GÖRSELLERİ İŞLEME ---
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

// --- 5. AŞAMA: TAG & TITLE ÜRETİMİ ---
// Fonksiyona varsayılan olarak force=false parametresi ekledik
// --- Sadece SEO Bölümünü Açan Fonksiyon ---
function openSeoSection() {
    document.getElementById('seo-section').classList.remove('hidden');
    document.getElementById('seo-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// --- Hedefli (Targeted) SEO Üretimi ---
// target alabileceği değerler: 'title', 'tags', 'both'
async function generateTagAndTitle(target = 'both', force = false) {
    // 1. ÖNCE SEO BÖLÜMÜNÜ GÖRÜNÜR YAP (Çünkü kullanıcı 'İleri' dedi)
    const seoSection = document.getElementById('seo-section');
    seoSection.classList.remove('hidden');
    
    // 2. Yükleniyor animasyonunu göster ve oraya odaklan
    document.getElementById('loading-tags').classList.remove('hidden');
    seoSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    // Neyi ürettiğimize göre mesajı güncelle
    const loadingText = document.querySelector('#loading-tags p');
    if (loadingText) {
        if(target === 'title') loadingText.innerText = "Yapay Zeka başlık (Title) üretiyor...";
        else if(target === 'tags') loadingText.innerText = "13 adet SEO uyumlu Tag hesaplanıyor...";
        else loadingText.innerText = "Title ve Tagler birlikte üretiliyor...";
    }

    try {
        const response = await fetch('/generate-seo/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                product_id: currentActiveProduct.id,
                force_recreate: force,
                target: target 
            })
        });

        const data = await response.json();
        
        // İşlem bitti, yükleniyor'u gizle
        document.getElementById('loading-tags').classList.add('hidden');

        if (data.status === "success") {
            // Verileri kutulara doldur
            if (data.title) {
                document.getElementById('output-title').value = data.title;
            }
            if (data.tags) {
                document.getElementById('output-tags').value = data.tags;
            }
            
            // Başarılı olduktan sonra tekrar bir süzülme efekti
            seoSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            
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




// =====================================================================
// PIPELINE 2: MANUEL YÜKLEME VE TOPLU İŞLEM MANTIĞI
// =====================================================================

let manualSelectedFiles = []; // Yüklenmek üzere bekleyen dosyalar

// 1. Sürükle Bırak ve Dosya Seçimi Dinleyicileri
const fileInput = document.getElementById('manual-file-input');
const dropzone = document.getElementById('dropzone');
const previewContainer = document.getElementById('upload-preview-container');
const settingsSection = document.getElementById('batch-settings-section');

if (fileInput) {
    fileInput.addEventListener('change', handleFileSelect);
}

if (dropzone) {
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('border-indigo-500', 'bg-indigo-100');
    });
    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('border-indigo-500', 'bg-indigo-100');
    });
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('border-indigo-500', 'bg-indigo-100');
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files; // Input'a aktar
            handleFileSelect({ target: fileInput }); // İşle
        }
    });
}

function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    manualSelectedFiles = files; // Hafızada tut
    
    // Önizlemeleri Göster
    previewContainer.innerHTML = '';
    files.forEach(file => {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewContainer.innerHTML += `
                <div class="relative border rounded-lg p-2 bg-gray-50 shadow-sm">
                    <img src="${e.target.result}" class="w-full h-24 object-contain rounded">
                    <p class="text-xs text-center mt-1 truncate text-gray-600">${file.name}</p>
                </div>
            `;
        };
        reader.readAsDataURL(file);
    });

    previewContainer.classList.remove('hidden');
    settingsSection.classList.remove('hidden');
    settingsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// --- Global Değişkenler (Hafıza) ---
let pendingUploadIds = []; // İşlenecek ID'ler
let pendingProcessSettings = {}; // Kullanıcı ayarları
let globalOriginalItems = []; // KIRIK RESİM HATASINI ÇÖZEN HAFIZA!

// 2. Ana Toplu İşlem Motoru
async function startBatchProcessing() {
    if (manualSelectedFiles.length === 0) {
        alert("Lütfen en az bir tasarım yükleyin.");
        return;
    }

    const doMockup = document.getElementById('batch-do-mockup').checked;
    const doSeo = document.getElementById('batch-do-seo').checked;
    const mockupGroupId = document.getElementById('batch-mockup-group').value;

    if (doMockup && !mockupGroupId) {
        alert("Mockup uygulanmasını istiyorsanız, lütfen bir Mockup Koleksiyonu seçin.");
        return;
    }

    if (!doMockup && !doSeo) {
        alert("Lütfen yapılacak en az bir işlem seçin (Mockup veya SEO).");
        return;
    }

    pendingProcessSettings = { doSeo, doMockup, mockupGroupId };

    document.getElementById('batch-settings-section').classList.add('hidden');
    document.getElementById('cache-warning-section').classList.add('hidden');
    const loadingDiv = document.getElementById('batch-loading');
    loadingDiv.classList.remove('hidden');
    loadingDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });

    try {
        const formData = new FormData();
        formData.append('group_name', `Batch Upload ${new Date().toLocaleDateString()}`);
        manualSelectedFiles.forEach(file => {
            formData.append('designs', file);
        });

        const uploadRes = await fetch('/upload-manual-designs/', {
            method: 'POST',
            body: formData 
        });
        const uploadData = await uploadRes.json();

        if (uploadData.status !== "success") throw new Error("Yükleme Hatası: " + uploadData.message);

        // --- HAFIZAYA YAZMA ---
        pendingUploadIds = uploadData.items.map(item => item.id);
        globalOriginalItems = uploadData.items; // Gerçek resim linklerini burada tutuyoruz!

        const cachedItems = uploadData.items.filter(item => item.cached === true);
        
        if (cachedItems.length > 0) {
            loadingDiv.classList.add('hidden');
            const warningSection = document.getElementById('cache-warning-section');
            document.getElementById('cached-files-count').innerText = cachedItems.length;
            warningSection.classList.remove('hidden');
            warningSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return; // İşlemi durdur, kullanıcıdan buton seçimi bekle
        }

        // Hiç cache yoksa doğrudan işleme devam et (use_existing sinyali vererek)
        await executeProcessBatch('use_existing');

    } catch (err) {
        document.getElementById('batch-loading').classList.add('hidden');
        alert(err.message);
    }
}

// 2.1. Kullanıcı Butona Bastığında Çalışan Fonksiyon
async function continueWithCache(actionType) {
    document.getElementById('cache-warning-section').classList.add('hidden');
    const loadingDiv = document.getElementById('batch-loading');
    loadingDiv.classList.remove('hidden');
    
    // Kullanıcının seçtiği aksiyonu gönder
    await executeProcessBatch(actionType);
}

// 2.2 Asıl Backend İşlemini Yapan Fonksiyon
async function executeProcessBatch(actionType) {
    try {
        const processRes = await fetch('/process-batch/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                upload_ids: pendingUploadIds,
                do_seo: pendingProcessSettings.doSeo,
                do_mockup: pendingProcessSettings.doMockup,
                mockup_group_id: pendingProcessSettings.mockupGroupId,
                action_type: actionType // YENİ: Backend'e ne yapacağını söylüyoruz!
            })
        });

        const processData = await processRes.json();
        if (processData.status !== "success") throw new Error("İşlem Hatası: " + processData.message);

        // --- HATANIN ÇÖZÜMÜ ---
        // Artık uydurma veri değil, global hafızadaki GERÇEK resimleri gönderiyoruz.
        renderBatchResults(globalOriginalItems, processData.results);

    } catch (err) {
        alert(err.message);
    } finally {
        document.getElementById('batch-loading').classList.add('hidden');
    }
}

// 3. Sonuçları Ekranda Gösterme
// =====================================================================
// BATCH EXPORT (TOPLU İNDİRME) VE MODAL FONKSİYONLARI
// =====================================================================

let currentProcessedIds = []; // İşlem bitince ID'leri burada tutacağız

// Bu fonksiyonu önceki kodda renderBatchResults içinde çağıracağız
// Tabloyu çizerken ID'leri hafızaya almayı unutma!
function renderBatchResults(originalItems, results) {
    const tbody = document.getElementById('batch-results-tbody');
    tbody.innerHTML = '';
    
    currentProcessedIds = []; // Export için ID'leri temizle/hazırla

    results.forEach(res => {
        // HATA ÖNLEME: Eğer res.status success dönmüşse ID'sini export dizisine ekle
        if(res.status === 'success') {
            currentProcessedIds.push(res.id); 
        }

        // --- KESİN ÇÖZÜM: TİP DÖNÜŞÜMÜ (TYPE-SAFE) EŞLEŞTİRME ---
        // Bazen backend'den gelen ID string ('42'), hafızadaki Number (42) olabilir.
        // Bu yüzden ikisini de parseInt ile sayıya çevirip öyle kıyaslıyoruz!
        const original = originalItems.find(item => parseInt(item.id) === parseInt(res.id));
        
        // EĞER ORİJİNAL KAYIT YOKSA BİR ŞEY YAZDIRMA (HATA ÖNLEME)
        if (!original) {
            console.warn(`ID ${res.id} eşleştirilemedi. originalItems içinde bu ID yok!`);
            return; 
        }
        
        let mockupHtml = '<span class="text-gray-400 text-xs italic">Uygulanmadı</span>';
        if (res.mockup) {
            // Sadece tek resmi değil, modal'a tüm ID'yi gönderiyoruz
            mockupHtml = `<button onclick="openBatchMockupModal(${res.id})" class="text-indigo-600 hover:text-indigo-800 text-sm font-bold flex items-center gap-1"><i class="fa-solid fa-images"></i> Mockupları Gör</button>`;
        } else if (res.status === 'error' || res.mockup_error) {
            mockupHtml = `<span class="text-red-500 text-xs">Hata Oluştu</span>`;
        }

        // ... SEO ve Tablo çizimi aynı kalıyor ...
        let seoHtml = '<span class="text-gray-400 text-xs italic">Uygulanmadı</span>';
        if (res.seo && res.seo.title) {
            seoHtml = `
                <div class="text-sm">
                    <p class="font-bold text-gray-800 line-clamp-1 mb-1">${res.seo.title}</p>
                    <p class="text-xs text-gray-500 line-clamp-2">${res.seo.tags}</p>
                </div>
            `;
        } else if (res.seo_error) {
             seoHtml = `<span class="text-red-500 text-xs">SEO Hatası</span>`;
        }

        tbody.innerHTML += `
            <tr class="hover:bg-gray-50 transition">
                <td class="py-4 px-4 border-b">
                    <div class="flex items-center gap-3">
                        <img src="${original.url}" class="h-16 w-16 object-contain bg-gray-100 rounded">
                        <span class="text-xs font-medium text-gray-600 truncate w-32">${original.name}</span>
                    </div>
                </td>
                <td class="py-4 px-4 border-b">${mockupHtml}</td>
                <td class="py-4 px-4 border-b">${seoHtml}</td>
            </tr>
        `;
    });

    const resultsSection = document.getElementById('batch-results-section');
    resultsSection.classList.remove('hidden');
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}


// --- EXPORT TETİKLEYİCİ ---
async function exportBatch() {
    if (!currentProcessedIds || currentProcessedIds.length === 0) {
        alert("Dışa aktarılacak geçerli (başarılı) bir sonuç bulunamadı.");
        return;
    }

    const btn = document.getElementById('btn-export-batch');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Paketleniyor... (Zaman Alabilir)';
    btn.disabled = true;

    try {
        const response = await fetch('/export-batch/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ upload_ids: currentProcessedIds })
        });

        if (!response.ok) {
            // Eğer JSON dönerse hatayı göster, dönmezse genel metin
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
                const errorData = await response.json();
                throw new Error(errorData.message || "İndirme başarısız oldu.");
            } else {
                throw new Error("Sunucudan geçersiz bir dosya veya I/O hatası döndü.");
            }
        }

        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = downloadUrl;
        
        const disposition = response.headers.get('Content-Disposition');
        let filename = 'Etsy_Batch_Export.zip';
        if (disposition && disposition.indexOf('filename=') !== -1) {
            filename = disposition.split('filename=')[1].replace(/"/g, '');
        }
        
        a.download = filename;
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

// --- TÜM MOCKUPLARI GETİREN MODAL ---
async function openBatchMockupModal(uploadId) {
    // HTML'de henüz bu modalın tasarımını yapmadıysan, şimdilik sadece ilk resmi açacak şekilde fallback koyalım:
    // Eğer 'batch-mockup-modal' adında bir div'in varsa onu açsın, yoksa uyarı versin.
    
    const modal = document.getElementById('batch-mockup-modal');
    if (!modal) {
        alert("Sisteme henüz 'Mockup Galerisi' HTML şablonu eklenmemiş. Lütfen standart Modal kodunu HTML'inize ekleyin.");
        return;
    }

    const grid = document.getElementById('batch-mockup-grid');
    const loading = document.getElementById('batch-mockup-loading');
    
    grid.innerHTML = '';
    loading.classList.remove('hidden');
    modal.classList.remove('hidden');
    
    // Animasyon
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        modal.classList.add('opacity-100');
    }, 10);
    document.body.style.overflow = 'hidden';

    try {
        const response = await fetch(`/get-batch-mockups/${uploadId}/`);
        const data = await response.json();
        
        loading.classList.add('hidden');
        
        if (data.status === 'success' && data.urls.length > 0) {
            data.urls.forEach(url => {
                grid.innerHTML += `
                    <div class="bg-white p-2 rounded shadow-sm hover:shadow transition cursor-pointer" onclick="openModal('${url}')">
                        <img src="${url}" class="w-full h-32 object-cover rounded">
                    </div>
                `;
            });
        } else {
            grid.innerHTML = `<div class="col-span-full text-center text-gray-500">Mockup bulunamadı.</div>`;
        }
    } catch (err) {
        loading.classList.add('hidden');
        grid.innerHTML = `<div class="col-span-full text-center text-red-500">Hata: ${err.message}</div>`;
    }
}