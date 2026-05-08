// ==========================================
// GLOBAL DEĞİŞKENLER VE HAFIZA YÖNETİMİ
// ==========================================
let selectedDesigns = [];
let manualSelectedFiles = []; // Yüklenen dosya objeleri
let pendingUploadIds = [];    // Veritabanından dönen ID'ler
let globalOriginalItems = []; // Backend'den dönen gerçek dosya yolları
let mockupMapping = {};       // Her index için seçilen şablonlar (Örn: {0: ["1", "3"], 1: ["2"]})
let allTemplates = [];        // Veritabanından gelen tüm şablonlar
let activeRowIndex = null;    // En son tıklanan satır (Mavi vurgu için)
let pendingProcessSettings = {};
let currentProcessedIds = [];

// CSRF Token Okuyucu
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
// HAFIZA YÖNETİMİ (STATE PERSISTENCE)
// ==========================================
function saveAppState() {
    const safeDesigns = [];
    const safeMapping = {};
    
    selectedDesigns.forEach((d, idx) => {
        // Güvenlik: Tarayıcılar yerel dosyaların (isNew) yenilemede tutulmasına izin vermez. 
        // Sadece kütüphaneden seçilenleri (DB kayıtlarını) hafızaya alıyoruz.
        if (!d.isNew) { 
            const seoRadio = document.querySelector(`input[name="seo_${idx}"]:checked`);
            safeDesigns.push({
                id: d.id, url: d.url, name: d.name, 
                seoTarget: seoRadio ? seoRadio.value : 'both'
            });
            safeMapping[safeDesigns.length - 1] = mockupMapping[idx];
        }
    });

    localStorage.setItem('p2_designs', JSON.stringify(safeDesigns));
    localStorage.setItem('p2_mapping', JSON.stringify(safeMapping));
    if (window.generatedMockupsCache) localStorage.setItem('p2_mockups', JSON.stringify(window.generatedMockupsCache));
    
    if (currentProcessedIds && currentProcessedIds.length > 0) {
        localStorage.setItem('p2_resultsHtml', document.getElementById('batch-results-tbody').innerHTML);
        localStorage.setItem('p2_processedIds', JSON.stringify(currentProcessedIds));
    }
}

async function restoreAppState() {
    const savedDesigns = JSON.parse(localStorage.getItem('p2_designs'));
    const savedMapping = JSON.parse(localStorage.getItem('p2_mapping'));
    const savedMockups = JSON.parse(localStorage.getItem('p2_mockups'));
    const savedResultsHtml = localStorage.getItem('p2_resultsHtml');
    const savedIds = JSON.parse(localStorage.getItem('p2_processedIds'));

    if (savedDesigns && savedDesigns.length > 0) {
        selectedDesigns = savedDesigns.map(d => ({
            isNew: false, id: d.id, file: null, url: d.url, name: d.name
        }));
        if (savedMapping) mockupMapping = savedMapping;
        
        renderPreviewRows();
        document.getElementById('mockup-pool-section').classList.remove('hidden');
        document.getElementById('batch-settings-section').classList.remove('hidden');

        // Radyo butonlarını eski haline getir
        setTimeout(() => {
            savedDesigns.forEach((d, i) => {
                if (d.seoTarget) {
                    const radio = document.querySelector(`input[name="seo_${i}"][value="${d.seoTarget}"]`);
                    if (radio) radio.checked = true;
                }
            });
        }, 150);
    }

    if (savedMockups) window.generatedMockupsCache = savedMockups;

    if (savedResultsHtml && savedIds) {
        document.getElementById('batch-results-tbody').innerHTML = savedResultsHtml;
        currentProcessedIds = savedIds;
        document.getElementById('batch-results-section').classList.remove('hidden');
    }
}

function clearSession() {
    if(confirm("Tüm işlemleri ve seçimleri sıfırlamak istediğinize emin misiniz?")) {
        localStorage.removeItem('p2_designs');
        localStorage.removeItem('p2_mapping');
        localStorage.removeItem('p2_mockups');
        localStorage.removeItem('p2_resultsHtml');
        localStorage.removeItem('p2_processedIds');
        window.location.reload();
    }
}

// ==========================================
// SAYFA YÜKLENDİĞİNDE
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    fetchMockupTemplates(); // Await ekledik ki şablonlar önce yüklensin
    fetchUserLibrary(); 
    restoreAppState();
    
    const fileInput = document.getElementById('manual-file-input');
    const dropzone = document.getElementById('dropzone');
    
    if (fileInput) fileInput.addEventListener('change', handleFileSelect);
    
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
                fileInput.files = e.dataTransfer.files;
                handleFileSelect({ target: fileInput });
            }
        });
    }
});

async function fetchUserLibrary() {
    const grid = document.getElementById('library-grid');
    if(!grid) return;

    try {
        const response = await fetch('/products/api/get-library/');
        const data = await response.json();
        
        if (data.status === "success" && data.designs.length > 0) {
            grid.innerHTML = '';
            data.designs.forEach(design => {
                grid.insertAdjacentHTML('beforeend', `
                    <div class="relative cursor-pointer group rounded-lg overflow-hidden border border-slate-200 hover:border-orange-500 transition aspect-square bg-white shadow-sm flex items-center justify-center" onclick="addFromLibrary(${design.id}, '${design.url}', '${design.name}')">
                        <img src="${design.url}" class="w-full h-full object-contain p-2">
                        <div class="absolute inset-0 bg-slate-900/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition"><i class="fa-solid fa-plus text-white text-2xl"></i></div>
                    </div>
                `);
            });
        } else {
            grid.innerHTML = '<div class="col-span-full text-center text-xs text-slate-400 mt-4">Kayıtlı tasarım yok.</div>';
        }
    } catch (err) {
        console.warn("Kütüphane API Hatası (404 olabilir):", err);
        grid.innerHTML = '<div class="col-span-full text-center text-xs text-red-400 mt-4">Kütüphane yüklenemedi.</div>';
    }
}

// YENİ: Kütüphaneden Tasarım Ekleme (Yeni Upload Yapmaz, DB'deki ID'yi kullanır!)
function addFromLibrary(id, url, name) {
    // Zaten ekli mi kontrol et
    if (selectedDesigns.some(d => d.id === id)) return;
    
    selectedDesigns.push({ isNew: false, id: id, file: null, url: url, name: name });
    mockupMapping[selectedDesigns.length - 1] = [];
    finalizeSelectionUI();
}

// ==========================================
// ŞABLONLARI ÇEKME VE YÖNETME
// ==========================================
async function fetchMockupTemplates() {
    const grid = document.getElementById('mockup-templates-grid');
    grid.innerHTML = '<div class="col-span-full text-center py-10"><i class="fa-solid fa-spinner fa-spin text-3xl text-indigo-500 mb-3"></i><p>Şablonlar yükleniyor...</p></div>';
    
    try {
        const response = await fetch('/image_processor/api/get-templates/');
        if (!response.ok) throw new Error("API yanıt vermedi.");
        const data = await response.json();
        
        if (data.templates && data.templates.length > 0) {
            allTemplates = data.templates;
            grid.innerHTML = '';
            allTemplates.forEach(tpl => {
                grid.insertAdjacentHTML('beforeend', `
                    <div class="relative cursor-pointer group hover:-translate-y-1 transition transform" onclick="toggleTemplateToSelected('${tpl.id}')">
                        <div class="border-2 border-slate-200 rounded-xl overflow-hidden shadow-sm group-hover:border-indigo-400">
                            <img src="${tpl.image_url}" class="w-full h-24 object-cover bg-white">
                            <div class="absolute bottom-0 w-full bg-slate-900/70 text-white text-[10px] p-1.5 text-center font-bold truncate backdrop-blur-sm">${tpl.title}</div>
                        </div>
                    </div>`);
            });
        } else {
            grid.innerHTML = `<div class="col-span-full text-center py-6 bg-slate-50 rounded-xl border-2 border-dashed border-slate-300"><p class="text-slate-500 font-bold">Mockup Şablonu Yok</p></div>`;
        }
    } catch (err) { 
        console.error("Şablon yükleme hatası:", err); 
        grid.innerHTML = `<p class="text-red-500 text-sm col-span-full">Şablonlar yüklenemedi: ${err.message}</p>`;
    }
}

// ==========================================
// TASARIM YÜKLEME VE SATIRLARI (ROWS) ÇİZME
// ==========================================
function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    files.forEach(file => {
        const tempUrl = URL.createObjectURL(file);
        selectedDesigns.push({ isNew: true, id: null, file: file, url: tempUrl, name: file.name });
        mockupMapping[selectedDesigns.length - 1] = []; 
    });
    finalizeSelectionUI();
}

function finalizeSelectionUI() {
    renderPreviewRows();
    document.getElementById('mockup-pool-section').classList.remove('hidden');
    document.getElementById('batch-settings-section').classList.remove('hidden');
    saveAppState();
}

function removeFile(index) {
    selectedDesigns.splice(index, 1);
    const newMapping = {};
    selectedDesigns.forEach((_, i) => { 
        const oldIndex = i >= index ? i + 1 : i;
        newMapping[i] = mockupMapping[oldIndex] || []; 
    });
    mockupMapping = newMapping;
    renderPreviewRows();
    
    if(selectedDesigns.length === 0){
        document.getElementById('mockup-pool-section').classList.add('hidden');
        document.getElementById('batch-settings-section').classList.add('hidden');
    }
    saveAppState();
}

function setActiveRow(index) {
    activeRowIndex = index;
    document.querySelectorAll('.design-row').forEach(r => r.classList.remove('border-indigo-500', 'bg-indigo-50', 'border-2'));
    const activeRow = document.getElementById(`row-${index}`);
    if (activeRow) activeRow.classList.add('border-indigo-500', 'bg-indigo-50', 'border-2');
}

function renderPreviewRows() {
    const container = document.getElementById('upload-preview-container');
    container.innerHTML = '';

    selectedDesigns.forEach((design, index) => {
        // Yeni tasarımsa yeşil rozet, kütüphanedense turuncu rozet
        const badge = design.isNew 
            ? `<span class="bg-emerald-100 text-emerald-700 text-[9px] font-bold px-1.5 py-0.5 rounded ml-2">YENİ DOSYA</span>`
            : `<span class="bg-orange-100 text-orange-700 text-[9px] font-bold px-1.5 py-0.5 rounded ml-2"><i class="fa-solid fa-database"></i> KÜTÜPHANE</span>`;

        const rowHtml = `
        <div id="row-${index}" class="design-row flex flex-col md:flex-row gap-6 p-4 border border-slate-200 rounded-xl bg-white items-center shadow-sm relative transition cursor-pointer" onclick="setActiveRow(${index})">
            <button onclick="event.stopPropagation(); removeFile(${index})" class="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center hover:bg-red-600 shadow-md z-10"><i class="fa-solid fa-xmark text-xs"></i></button>
            
            <div class="flex items-center gap-4 w-full md:w-1/3 md:border-r border-slate-100 pr-4">
                <input type="checkbox" class="row-checkbox w-5 h-5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer" data-index="${index}" onclick="event.stopPropagation()">
                <img src="${design.url}" class="w-16 h-16 object-contain bg-slate-50 rounded border border-slate-200">
                <div class="flex flex-col">
                    <span class="text-xs font-bold text-slate-600 truncate w-32" title="${design.name}">${design.name}</span>
                    <div>${badge}</div>
                </div>
            </div>

            <div class="w-full md:w-auto flex-shrink-0 flex flex-col gap-1.5 md:border-r border-slate-100 md:pr-4">
                <label class="text-[10px] font-bold text-slate-400 uppercase">SEO HEDEFİ</label>
                <div class="flex gap-2">
                    <label class="text-[10px] font-semibold cursor-pointer hover:text-indigo-600"><input type="radio" name="seo_${index}" value="both" checked class="text-indigo-600 focus:ring-indigo-500"> İkisi</label>
                    <label class="text-[10px] font-semibold cursor-pointer hover:text-indigo-600"><input type="radio" name="seo_${index}" value="title" class="text-indigo-600 focus:ring-indigo-500"> Title</label>
                    <label class="text-[10px] font-semibold cursor-pointer hover:text-indigo-600"><input type="radio" name="seo_${index}" value="tags" class="text-indigo-600 focus:ring-indigo-500"> Tag</label>
                    <label class="text-[10px] font-semibold cursor-pointer text-red-500"><input type="radio" name="seo_${index}" value="none" class="text-red-500 focus:ring-red-500"> Pasif</label>
                </div>
            </div>

            <div class="flex-1 flex flex-wrap gap-2 items-center min-h-[3rem]" id="templates-for-${index}"></div>
        </div>`;
        container.insertAdjacentHTML('beforeend', rowHtml);
        updateRowTemplatesUI(index);
    });

    if (selectedDesigns.length > 0) setTimeout(() => setActiveRow(0), 50);
}



// ==========================================
// ŞABLON EŞLEŞTİRME VE ÇİZİM
// ==========================================
function toggleTemplateToSelected(templateId) {
    const masterBox = document.getElementById('select-all-mockup-designs');
    // DÜZELTİLDİ: manualSelectedFiles yerine selectedDesigns kullanıyoruz
    let targets = (masterBox && masterBox.checked) 
        ? selectedDesigns.map((_, i) => i) 
        : (activeRowIndex !== null ? [activeRowIndex] : []);

    if (targets.length === 0) return alert("Lütfen önce bir satıra tıklayın veya 'Tümünü Seç'i işaretleyin.");

    targets.forEach(idx => {
        const list = mockupMapping[idx];
        const pos = list.indexOf(String(templateId));
        if (pos === -1) {
            list.push(String(templateId)); 
            const cb = document.querySelector(`.row-checkbox[data-index="${idx}"]`);
            if(cb) cb.checked = true; 
        } else {
            list.splice(pos, 1); 
        }
        updateRowTemplatesUI(idx);
    });
}

function updateRowTemplatesUI(index) {
    const container = document.getElementById(`templates-for-${index}`);
    if (!container) return;
    const selectedIds = mockupMapping[index] || [];
    
    if (selectedIds.length === 0) {
        container.innerHTML = '<p class="text-[10px] text-slate-400 italic">Şablon seçilmedi. Satıra tıklayıp şablon ekleyin.</p>';
        return;
    }

    container.innerHTML = '';
    selectedIds.forEach(tplId => {
        const tpl = allTemplates.find(t => String(t.id) === String(tplId));
        if (tpl) {
            container.insertAdjacentHTML('beforeend', `
                <div class="relative group" onclick="event.stopPropagation(); removeSingleTemplate(${index}, '${tplId}')">
                    <img src="${tpl.image_url}" class="w-10 h-10 object-cover rounded border-2 border-indigo-400 shadow-sm cursor-pointer">
                    <div class="absolute inset-0 bg-red-500/80 text-white opacity-0 group-hover:opacity-100 flex items-center justify-center rounded transition cursor-pointer shadow"><i class="fa-solid fa-xmark text-[10px]"></i></div>
                </div>`);
        }
    });
    saveAppState();
}

function removeSingleTemplate(index, tplId) {
    mockupMapping[index] = mockupMapping[index].filter(id => id !== String(tplId));
    updateRowTemplatesUI(index);
}

function setGlobalSeoTarget(val) {
    // DÜZELTİLDİ: manualSelectedFiles yerine selectedDesigns kullanıyoruz
    selectedDesigns.forEach((_, i) => {
        const radio = document.querySelector(`input[name="seo_${i}"][value="${val}"]`);
        if (radio) radio.checked = true;
    });
}

function toggleAllMockupDesigns(master) {
    document.querySelectorAll('.row-checkbox').forEach(cb => cb.checked = master.checked);
}

// ==========================================
// BACKEND İŞLEMLERİNİ BAŞLATMA VE SONUÇLAR
// ==========================================
// GÜNCELLENDİ: Ana Başlatma Motoru (Akıllı Yükleyici)
async function startBatchProcessing() {
    const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
    if (checkedBoxes.length === 0) return alert("Lütfen işleme sokmak istediğiniz tasarımları işaretleyin.");

    const selectedIndices = Array.from(checkedBoxes).map(cb => parseInt(cb.dataset.index));
    
    // 1. Yeni Dosyaları Ayır (Sadece bunları sunucuya yükleyeceğiz)
    const filesToUpload = [];
    const libraryIds = []; // Zaten DB'de olanlar
    
    selectedIndices.forEach(idx => {
        const design = selectedDesigns[idx];
        if (design.isNew) filesToUpload.push(design.file);
        else libraryIds.push(design.id);
    });

    const fileMockupMapping = {}; // Dosya ismine göre eşleştirme (Yeni dosyalar için)
    const dbMockupMapping = {};   // Direkt ID'ye göre eşleştirme (Kütüphane dosyaları için)
    const fileSeoTargets = [];
    const dbSeoMapping = {};
    let hasAnyMockup = false;

    selectedIndices.forEach(idx => {
        const design = selectedDesigns[idx];
        const templates = mockupMapping[idx];
        const seoTarget = document.querySelector(`input[name="seo_${idx}"]:checked`).value;

        if (templates && templates.length > 0) hasAnyMockup = true;

        if (design.isNew) {
            if (templates && templates.length > 0) fileMockupMapping[design.name] = templates;
            fileSeoTargets.push({ fileName: design.name, target: seoTarget });
        } else {
            if (templates && templates.length > 0) dbMockupMapping[design.id] = templates;
            dbSeoMapping[design.id] = seoTarget;
        }
    });

    pendingProcessSettings = { fileMockupMapping, fileSeoTargets, dbMockupMapping, dbSeoMapping, hasAnyMockup };

    document.getElementById('batch-settings-section').classList.add('hidden');
    document.getElementById('mockup-pool-section').classList.add('hidden');
    document.getElementById('batch-loading').classList.remove('hidden');

    try {
        let finalUploadIds = [...libraryIds]; // Kütüphanedekileri direkt nihai listeye koy
        globalOriginalItems = []; // Temizle

        // Kütüphane itemlerini global listeye ekle (Render için)
        selectedIndices.forEach(idx => {
            const design = selectedDesigns[idx];
            if (!design.isNew) globalOriginalItems.push({ id: design.id, name: design.name, url: design.url });
        });

        // 2. Eğer YENİ dosya varsa sunucuya gönder
        if (filesToUpload.length > 0) {
            const formData = new FormData();
            formData.append('group_name', `Batch_Upload_${new Date().getTime()}`);
            filesToUpload.forEach(file => formData.append('designs', file));

            const uploadRes = await fetch('/products/upload-manual-designs/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') || '' },
                body: formData 
            });
            const uploadData = await uploadRes.json();
            if (uploadData.status !== "success") throw new Error("Yükleme Hatası: " + uploadData.message);

            // Yeni yüklenenlerin ID'lerini ve ayarlarını haritaya işle
            uploadData.items.forEach(item => {
                finalUploadIds.push(item.id);
                globalOriginalItems.push(item);
                
                if (pendingProcessSettings.fileMockupMapping[item.name]) {
                    pendingProcessSettings.dbMockupMapping[item.id] = pendingProcessSettings.fileMockupMapping[item.name];
                }
                const seoSetting = pendingProcessSettings.fileSeoTargets.find(s => s.fileName === item.name);
                pendingProcessSettings.dbSeoMapping[item.id] = seoSetting ? seoSetting.target : 'both';
            });
        }

        // Toparlanan nihai listeyi işleme gönder
        pendingUploadIds = finalUploadIds;
        await executeProcessBatch('use_existing');

    } catch (err) {
        document.getElementById('batch-loading').classList.add('hidden');
        alert(err.message);
    }
}

async function continueWithCache(actionType) {
    document.getElementById('cache-warning-section').classList.add('hidden');
    document.getElementById('batch-loading').classList.remove('hidden');
    await executeProcessBatch(actionType);
}

async function executeProcessBatch(actionType) {
    try {
        const processRes = await fetch('/products/process-batch/', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') || ''
            },
            body: JSON.stringify({
                upload_ids: pendingUploadIds,
                mockup_mapping: pendingProcessSettings.dbMockupMapping, // Frontend'deki yeni yapı!
                do_mockup: pendingProcessSettings.hasAnyMockup,
                seo_targets: pendingProcessSettings.dbSeoMapping,
                action_type: actionType 
            })
        });

        const processData = await processRes.json();
        if (processData.status !== "success") throw new Error(processData.message);

        renderBatchResults(globalOriginalItems, processData.results);

    } catch (err) {
        alert("İşlem Hatası: " + err.message);
    } finally {
        document.getElementById('batch-loading').classList.add('hidden');
    }
}

function renderBatchResults(originalItems, results) {
    const tbody = document.getElementById('batch-results-tbody');
    tbody.innerHTML = '';
    currentProcessedIds = []; 

    results.forEach(res => {
        if(res.status === 'success') currentProcessedIds.push(res.id); 

        const original = originalItems.find(item => parseInt(item.id) === parseInt(res.id));
        if (!original) return; 
        
        let mockupHtml = '<span class="text-slate-400 text-xs italic">Uygulanmadı</span>';
        
        // DÜZELTME: Artık res.mockups bir dizi (array) değil, sözlük (object). { "group_id": [url1, url2] }
        if (res.mockups && Object.keys(res.mockups).length > 0) {
            if (!window.generatedMockupsCache) window.generatedMockupsCache = {};
            window.generatedMockupsCache[res.id] = res.mockups; 
            
            // Pipeline 1'deki "renderGeneratedMockupsUI" mantığının aynısını tablo hücresine çiziyoruz
            let coverHtml = `<div class="flex flex-wrap items-center gap-2">`;
            let totalCount = 0;
            
            for (const [groupId, urls] of Object.entries(res.mockups)) {
                if (!urls || urls.length === 0) continue;
                totalCount += urls.length;
                const coverUrl = urls[0];
                
                coverHtml += `
                <div class="relative group cursor-pointer border-2 border-emerald-500 rounded p-1 bg-white w-14 h-14 flex-shrink-0 shadow-sm" 
                     onclick="openMockupCarousel('${res.id}', '${groupId}', 0)">
                    <div class="absolute -top-2 -right-2 bg-emerald-600 text-white text-[9px] font-bold px-1.5 rounded-full z-20 shadow">${urls.length}</div>
                    <img src="${coverUrl}" class="w-full h-full object-cover rounded group-hover:opacity-75 transition">
                </div>`;
            }
            coverHtml += `</div>`;
            mockupHtml = coverHtml; // Şık kapak fotoğraflarını tabloya bas!
        } else if (res.status === 'error' || res.mockup_error) {
            mockupHtml = `<span class="text-red-500 text-xs font-medium"><i class="fa-solid fa-triangle-exclamation"></i> Hata</span>`;
        }

        let seoHtml = '<span class="text-slate-400 text-xs italic">Uygulanmadı</span>';
        if (res.seo && res.seo.title) {
            seoHtml = `
                <div class="text-sm bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                    <p class="font-bold text-slate-800 line-clamp-1 mb-1" title="${res.seo.title}">${res.seo.title}</p>
                    <p class="text-[10px] text-slate-500 line-clamp-2 leading-relaxed" title="${res.seo.tags}">${res.seo.tags}</p>
                </div>`;
        } else if (res.seo_error) {
             seoHtml = `<span class="text-red-500 text-xs font-medium"><i class="fa-solid fa-triangle-exclamation"></i> SEO Hatası</span>`;
        }

        tbody.innerHTML += `
            <tr class="hover:bg-slate-50 transition border-b border-slate-100">
                <td class="py-4 px-6">
                    <div class="flex items-center gap-4">
                        <img src="${original.url}" class="h-16 w-16 object-contain bg-slate-100 rounded-lg border border-slate-200">
                        <span class="text-sm font-bold text-slate-700 truncate w-32" title="${original.name}">${original.name}</span>
                    </div>
                </td>
                <td class="py-4 px-6">${mockupHtml}</td>
                <td class="py-4 px-6">${seoHtml}</td>
            </tr>`;
    });

    document.getElementById('batch-results-section').classList.remove('hidden');
    document.getElementById('batch-results-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
    saveAppState();
}

// ==========================================
// GALERİ (CAROUSEL) YÖNETİMİ
// ==========================================
let currentCarouselImages = [];
let currentCarouselIndex = 0;

function openMockupCarousel(designId, groupId, startIndex = 0) {
    if (!window.generatedMockupsCache || !window.generatedMockupsCache[designId] || !window.generatedMockupsCache[designId][groupId]) return;
    
    currentCarouselImages = window.generatedMockupsCache[designId][groupId];
    currentCarouselIndex = startIndex;
    
    updateModalUI();
    showModal();
}

function changeCarousel(direction) {
    currentCarouselIndex += direction;
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

// ==========================================
// İNDİRME
// ==========================================
async function exportBatch() {
    if (currentProcessedIds.length === 0) return alert("İndirilecek geçerli sonuç bulunamadı.");

    const btn = document.getElementById('btn-export-batch');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Paketleniyor...';
    btn.disabled = true;

    try {
        // İSTEK YENİ YAZDIĞIMIZ PIPELINE 2 URL'SİNE GİDİYOR
        const response = await fetch('/common/api/export-pipeline2/', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') || ''
            },
            body: JSON.stringify({ upload_ids: currentProcessedIds })
        });

        // Backend'den Json dönüyorsa hata okuması yap, dönmüyorsa genel hata ver
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || "Sunucudan dosya oluşturulamadı.");
        }

        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `Etsy_Pipeline2_Project_${new Date().getTime()}.zip`;
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