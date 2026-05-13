let currentOffset = 0;
const limit = 24;
let isLoading = false;
let hasMore = true;
let currentFilter = 'all';
let selectedAssets = new Set();

document.addEventListener('DOMContentLoaded', () => {
    // Sayfa açıldığında ilk 24'ü getir
    fetchAssetLibrary(true);

    // SONSUZ KAYDIRMA (İnfinite Scroll) DİNLEYİCİSİ
    window.addEventListener('scroll', () => {
        // Sayfanın en altına 500 piksel yaklaşıldıysa ve yüklenmiyorsa
        if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 500) {
            if (hasMore && !isLoading) {
                fetchAssetLibrary(false);
            }
        }
    });
});

async function fetchAssetLibrary(reset = false) {
    if (isLoading) return;
    isLoading = true;

    const grid = document.getElementById('assets-grid');

    if (reset) {
        currentOffset = 0;
        hasMore = true;
        grid.innerHTML = ''; // Listeyi temizle
    }

    // Yükleniyor Göstergesi Ekle
    const loaderId = 'assets-loader';
    grid.insertAdjacentHTML('beforeend', `<div id="${loaderId}" class="col-span-full text-center py-8 text-slate-400"><i class="fa-solid fa-spinner fa-spin text-3xl mb-3"></i><p>Yükleniyor...</p></div>`);

    try {
        const response = await fetch(`/common/api/get-assets/?type=${currentFilter}&offset=${currentOffset}&limit=${limit}`);
        const data = await response.json();
        
        document.getElementById(loaderId)?.remove();

        if (data.status === 'success') {
            if (data.assets.length === 0 && currentOffset === 0) {
                grid.innerHTML = `<div class="col-span-full text-center py-12 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-slate-500">Bu kategoride tasarım bulunamadı.</div>`;
            } else {
                renderAssets(data.assets);
                currentOffset += limit;
                hasMore = data.has_more;
            }
        }
    } catch (error) {
        document.getElementById(loaderId)?.remove();
        if (currentOffset === 0) {
            grid.innerHTML = '<div class="col-span-full text-red-500 text-center py-8">Veriler bağlanırken hata oluştu!</div>';
        }
    } finally {
        isLoading = false;
    }
}

function filterAssets(type) {
    if (currentFilter === type) return; 
    currentFilter = type;
    
    // UI Sekme Renklerini Güncelle
    ['all', 'ai', 'manual'].forEach(t => {
        const btn = document.getElementById(`btn-filter-${t}`);
        if(t === type) {
            btn.className = "pb-3 font-bold text-sm border-b-2 border-indigo-600 text-indigo-600 transition";
        } else {
            btn.className = "pb-3 font-bold text-sm border-b-2 border-transparent text-slate-500 hover:text-slate-700 transition";
        }
    });

    // Filtre değiştiği için listeyi sıfırla ve baştan çek
    fetchAssetLibrary(true);
}

function renderAssets(assets) {
    const grid = document.getElementById('assets-grid');
    let html = '';
    
    assets.forEach(asset => {
        const bgBadge = asset.has_bg 
            ? `<div class="absolute top-2 right-2 bg-orange-500 text-white text-[10px] font-bold px-2 py-1 rounded shadow-sm z-10" title="Arka planı temizlenmemiş"><i class="fa-solid fa-scissors"></i> Ham AI</div>` 
            : ``;
        
        const typeBadge = asset.type === 'ai' 
            ? `<div class="absolute top-2 right-2 bg-indigo-500/90 backdrop-blur text-white text-[10px] font-bold px-2 py-1 rounded shadow-sm z-10"><i class="fa-solid fa-robot"></i> AI</div>`
            : `<div class="absolute top-2 right-2 bg-emerald-500/90 backdrop-blur text-white text-[10px] font-bold px-2 py-1 rounded shadow-sm z-10"><i class="fa-solid fa-upload"></i> Manuel</div>`;

        html += `
        <div class="relative group bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition aspect-square flex flex-col">
            <div class="absolute top-2 left-2 z-30">
                <input type="checkbox" id="chk-${asset.id}" value="${asset.id}" data-type="${asset.type}" onchange="toggleSelection('${asset.id}')" 
                       class="asset-checkbox w-5 h-5 text-indigo-600 bg-white border-slate-300 rounded focus:ring-indigo-500 cursor-pointer shadow-sm">
            </div>
            
            ${bgBadge}
            ${typeBadge}
            
            <div class="flex-1 bg-slate-50 flex items-center justify-center p-2 overflow-hidden relative">
                <div class="absolute inset-0" style="background-image: linear-gradient(45deg, #f0f0f0 25%, transparent 25%), linear-gradient(-45deg, #f0f0f0 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #f0f0f0 75%), linear-gradient(-45deg, transparent 75%, #f0f0f0 75%); background-size: 20px 20px; background-position: 0 0, 0 10px, 10px -10px, -10px 0px; opacity: 0.5;"></div>
                
                <img src="${asset.url}" loading="lazy" decoding="async" class="w-full h-full object-contain relative z-10 group-hover:scale-105 transition duration-300">
                
                <div class="absolute inset-0 bg-slate-900/80 backdrop-blur-sm flex flex-col items-center justify-center gap-3 opacity-0 group-hover:opacity-100 transition duration-200 z-20">
                    
                    ${asset.type === 'ai' ? `
                    <div class="bg-white/10 p-2 rounded-lg flex flex-col gap-1 w-32 text-xs font-bold shadow-inner mb-1">
                        <span class="text-slate-300 text-[9px] uppercase tracking-wider mb-1 text-center">Hedef Pipeline</span>
                        <label class="flex items-center text-white cursor-pointer hover:text-indigo-300">
                            <input type="radio" name="route_${asset.id}" value="p1" class="mr-2 text-indigo-500 focus:ring-indigo-500"> Pipeline 1
                        </label>
                        <label class="flex items-center text-white cursor-pointer hover:text-indigo-300">
                            <input type="radio" name="route_${asset.id}" value="p2" checked class="mr-2 text-indigo-500 focus:ring-indigo-500"> Pipeline 2
                        </label>
                    </div>
                    ` : ''}
                    
                    <button onclick="deleteAsset('${asset.id}')" class="bg-red-500 hover:bg-red-600 text-white px-4 py-1.5 rounded-full text-xs font-bold w-32 shadow-lg"><i class="fa-solid fa-trash-can mr-1"></i> Sil</button>
                </div>
            </div>
        </div>
        `;
    });

    grid.insertAdjacentHTML('beforeend', html);
}

// CSRF Token okuyucu (Django POST istekleri için zorunludur)
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

// Dosya seçildiğinde tetiklenen olay dinleyicisi
document.getElementById('asset-upload-input').addEventListener('change', async function(e) {
    const files = e.target.files;
    if (files.length === 0) return;

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }

    // Butonu yükleniyor moduna al
    const btnText = document.getElementById('upload-btn-text');
    const originalText = btnText.innerText;
    btnText.innerHTML = `Yükleniyor (${files.length})... <i class="fa-solid fa-spinner fa-spin ml-1"></i>`;
    document.getElementById('btn-upload-trigger').disabled = true;

    try {
        const response = await fetch('/common/api/upload-asset/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: formData
        });

        const data = await response.json();

        if (data.status === 'success') {
            if (data.uploaded_assets.length > 0) {
                // Eğer "Manuel" veya "Tümü" sekmesindeysek, yeni resimleri en başa ekle
                if (currentFilter === 'all' || currentFilter === 'manual') {
                    // Sayfayı tamamen yenilemek yerine, listeyi baştan çekmek en temizidir
                    fetchAssetLibrary(true);
                }
            } else {
                alert("Seçtiğiniz dosyalar zaten kütüphanenizde mevcut.");
            }
        } else {
            alert("Hata: " + data.message);
        }
    } catch (error) {
        alert("Dosyalar yüklenirken sunucu ile bağlantı koptu.");
    } finally {
        // İşlem bitince butonu eski haline getir ve input'u temizle
        btnText.innerText = originalText;
        document.getElementById('btn-upload-trigger').disabled = false;
        e.target.value = ''; 
    }
});




async function deleteAsset(assetId) {
    // 1. Kullanıcıyı net bir şekilde uyar (Etsy odaklı bir uyarı)
    const confirmMessage = "DİKKAT: Bu tasarımı silmek üzeresiniz.\n\nEğer silerseniz bu tasarımla üretilmiş olan tüm Mockup görselleri ve SEO (Başlık/Etiket) kayıtları da Geçmiş'ten kalıcı olarak SİLİNECEKTİR. Sunucudan tamamen temizlenecektir.\n\nOnaylıyor musunuz?";
    
    if (!confirm(confirmMessage)) {
        return; // Kullanıcı iptal etti
    }

    try {
        const response = await fetch('/common/api/delete-asset/', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') 
            },
            body: JSON.stringify({ id: assetId })
        });

        const data = await response.json();

        if (data.status === 'success') {
            // Başarılı olursa listeyi baştan çek ve arayüzü güncelle
            fetchAssetLibrary(true);
        } else {
            alert("Silme hatası: " + data.message);
        }
    } catch (error) {
        alert("Sunucu ile iletişim kurulamadı.");
    }
}

// Eski toggleSelection'ı bununla değiştir
function toggleSelection(assetId) {
    const chk = document.getElementById(`chk-${assetId}`);
    if (chk.checked) selectedAssets.add(assetId);
    else selectedAssets.delete(assetId);
    
    // Eğer hepsi seçilmediyse "Tümünü Seç" kutusunu kaldır
    const allChecked = document.querySelectorAll('.asset-checkbox').length === selectedAssets.size;
    document.getElementById('selectAllCheckbox').checked = allChecked;
    
    updateActionBar();
}

// Bunu yeni ekle
function toggleSelectAll(isChecked) {
    document.querySelectorAll('.asset-checkbox').forEach(chk => {
        chk.checked = isChecked;
        if (isChecked) selectedAssets.add(chk.value);
        else selectedAssets.delete(chk.value);
    });
    updateActionBar();
}

function clearSelection() {
    selectedAssets.clear();
    document.querySelectorAll('.asset-checkbox').forEach(chk => chk.checked = false);
    document.getElementById('selectAllCheckbox').checked = false;
    updateActionBar();
}

function updateActionBar() {
    const bar = document.getElementById('batch-action-bar');
    document.getElementById('selected-count-text').innerText = selectedAssets.size;
    if (selectedAssets.size === 0) bar.classList.add('translate-y-full');
    else bar.classList.remove('translate-y-full');
}

async function sendToProduction() {
    if (selectedAssets.size === 0) return;

    const routeMapping = {};
    let hasP1 = false;
    let hasP2 = false;

    selectedAssets.forEach(assetId => {
        if (assetId.startsWith('ai_')) {
            const selectedRadio = document.querySelector(`input[name="route_${assetId}"]:checked`);
            const target = selectedRadio ? selectedRadio.value : 'p2';
            routeMapping[assetId] = target;
            if (target === 'p1') hasP1 = true;
            if (target === 'p2') hasP2 = true;
        } else {
            routeMapping[assetId] = 'p2';
            hasP2 = true;
        }
    });

    // POPUP BLOCKER ÇÖZÜMÜ: Eğer her iki pipeline da varsa, sekmeyi hemen (boş olarak) açıyoruz
    let p1Window = null;
    if (hasP1 && hasP2) {
        p1Window = window.open('about:blank', '_blank');
    }

    const btnProd = document.getElementById('btn-route-prod');
    const originalText = btnProd.innerHTML;
    btnProd.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> İşleniyor...`;
    btnProd.disabled = true;

    try {
        const response = await fetch('/common/api/route-assets/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ routes: routeMapping })
        });

        const data = await response.json();

        if (data.status === 'success') {
            if (data.redirect_p1 && data.redirect_p2) {
                // Önceden açtığımız sekmeyi P1'e yönlendir, mevcut sekmeyi P2 yap
                if (p1Window) p1Window.location.href = data.redirect_p1;
                window.location.href = data.redirect_p2;
            } else if (data.redirect_p1) {
                window.location.href = data.redirect_p1;
            } else if (data.redirect_p2) {
                window.location.href = data.redirect_p2;
            }
        } else {
            if (p1Window) p1Window.close();
            alert("Hata: " + data.message);
        }
    } catch (error) {
        if (p1Window) p1Window.close();
        alert("Bağlantı hatası.");
    } finally {
        btnProd.innerHTML = originalText;
        btnProd.disabled = false;
    }
}