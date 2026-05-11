
window.historyMockupsCache = { p1: {}, p2: {} };
let state = {
    p1: { offset: 0, limit: 30, hasMore: true, isLoading: false },
    p2: { offset: 0, limit: 30, hasMore: true, isLoading: false },
    activeTab: 'p1'
};

document.addEventListener('DOMContentLoaded', () => {
    // İlk yükleme
    fetchHistoryData('p1');
    fetchHistoryData('p2');

    // SCROLL EVENT: Sayfa sonuna yaklaşıldığında yeni veri çek
    window.onscroll = function() {
        if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 500) {
            if (state[state.activeTab].hasMore && !state[state.activeTab].isLoading) {
                fetchHistoryData(state.activeTab);
            }
        }
    };
});


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

function switchTab(tabId) {
    state.activeTab = tabId;
    document.getElementById('tab-p1').classList.toggle('hidden', tabId !== 'p1');
    document.getElementById('tab-p2').classList.toggle('hidden', tabId !== 'p2');
    
    document.getElementById('btn-tab-p1').className = tabId === 'p1' 
        ? "px-6 py-3 font-bold text-sm border-b-2 border-indigo-600 text-indigo-600 transition" 
        : "px-6 py-3 font-bold text-sm border-b-2 border-transparent text-slate-500 hover:text-slate-700 transition";
        
    document.getElementById('btn-tab-p2').className = tabId === 'p2' 
        ? "px-6 py-3 font-bold text-sm border-b-2 border-indigo-600 text-indigo-600 transition" 
        : "px-6 py-3 font-bold text-sm border-b-2 border-transparent text-slate-500 hover:text-slate-700 transition";
}

async function fetchHistoryData(type) {
    const s = state[type];
    s.isLoading = true;
    
    // Alt tarafa yükleniyor ikonu ekleyelim (opsiyonel)
    const tbody = document.getElementById(`${type}-tbody`);
    if(s.offset === 0) tbody.innerHTML = `<tr><td colspan="5" class="p-10 text-center"><i class="fa-solid fa-spinner fa-spin text-3xl text-indigo-500"></i></td></tr>`;

    try {
        const res = await fetch(`/common/api/get-history/?type=${type}&offset=${s.offset}&limit=${s.limit}`);
        const data = await res.json();
        
        if(data.status === 'success') {
            if(s.offset === 0) tbody.innerHTML = ''; // İlk yüklemede temizle
            
            renderTableRows(type, data.items);
            
            s.offset = data.next_offset;
            s.hasMore = data.has_more;
        }
    } catch (err) {
        console.error("Yükleme hatası:", err);
    } finally {
        s.isLoading = false;
    }
}

function renderTableRows(type, items) {
    const tbody = document.getElementById(`${type}-tbody`);
    if(items.length === 0 && state[type].offset === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-slate-400 font-medium">Kayıt bulunamadı.</td></tr>`;
        return;
    }

    items.forEach(item => {
        window.historyMockupsCache[type][item.id] = item.mockups;
        
        // Önceki renderTable mantığının aynısı (HTML satırlarını oluştur)
        const row = createRowHtml(type, item);
        tbody.insertAdjacentHTML('beforeend', row);
    });
}

function createRowHtml(type, item) {
    const mockupsHtml = item.mockups.length > 0 
        ? `<div class="relative inline-block cursor-pointer group" onclick="openHistoryCarousel('${type}', ${item.id})">
              <img src="${item.mockups[0]}" class="w-16 h-16 rounded border-2 border-slate-200 group-hover:border-indigo-500 transition object-cover shadow-sm">
              <div class="absolute -top-2 -right-2 bg-indigo-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full shadow">${item.mockups.length}</div>
           </div>`
        : `<span class="text-xs text-slate-400 italic">Yok</span>`;

    const seoHtml = item.seo && item.seo.title 
        ? `<div class="text-xs bg-slate-50 p-3 rounded border border-slate-200">
               <p class="font-bold text-slate-800 mb-2">${item.seo.title}</p>
               <p class="text-slate-500">${item.seo.tags}</p>
           </div>`
        : `<span class="text-xs text-slate-400 italic">Yok</span>`;

    if(type === 'p1') {
        const sourceHtml = item.source_image 
            ? `<div class="flex flex-col gap-1 items-center w-16">
                   <a href="${item.source_url}" target="_blank"><img src="${item.source_image}" class="h-16 w-16 object-cover rounded border border-slate-200 hover:opacity-75 transition p-1 bg-white"></a>
                   <a href="${item.source_url}" target="_blank" class="text-[9px] text-indigo-500 hover:underline font-medium text-center truncate w-full"><i class="fa-solid fa-link"></i> Kaynak</a>
               </div>`
            : `<a href="${item.source_url}" target="_blank" class="text-indigo-500 text-xs hover:underline"><i class="fa-solid fa-link"></i> Kaynak</a>`;

        return `
            <tr class="hover:bg-slate-50 transition border-b border-slate-100">
                <td class="p-4 align-top"><input type="checkbox" value="${item.id}" class="cb-p1 w-4 h-4 mt-2 text-indigo-600 rounded"></td>
                <td class="p-4 align-top">${sourceHtml}</td>
                <td class="p-4 align-top"><img src="${item.design_image}" class="h-16 w-16 object-contain bg-slate-100 rounded border border-slate-200 p-1"></td>
                <td class="p-4 align-top">${mockupsHtml}</td>
                <td class="p-4 align-top w-2/5">${seoHtml}</td>
            </tr>`;
    } else {
        return `
            <tr class="hover:bg-slate-50 transition border-b border-slate-100">
                <td class="p-4 align-top"><input type="checkbox" value="${item.id}" class="cb-p2 w-4 h-4 mt-2 text-indigo-600 rounded"></td>
                <td class="p-4 align-top"><div class="flex flex-col gap-2"><img src="${item.original_image}" class="h-16 w-16 object-contain bg-slate-100 rounded border border-slate-200 p-1"><span class="text-[10px] font-bold text-slate-500 truncate w-24">${item.filename}</span></div></td>
                <td class="p-4 align-top">${mockupsHtml}</td>
                <td class="p-4 align-top w-2/5">${seoHtml}</td>
            </tr>`;
    }
}

function toggleAll(type) {
    const isChecked = document.getElementById(`selectAll${type.toUpperCase()}`).checked;
    document.querySelectorAll(`.cb-${type}`).forEach(cb => cb.checked = isChecked);
}

// === ZIP İNDİRME İŞLEMİ (Pipeline 1 ve Pipeline 2 Export Servislerine Bağlantı) ===
async function exportSelected(type) {
    const checkboxes = document.querySelectorAll(`.cb-${type}:checked`);
    if(checkboxes.length === 0) return alert("Lütfen indirmek için en az bir satır seçin.");

    const ids = Array.from(checkboxes).map(cb => parseInt(cb.value));
    const btn = document.getElementById(`export-btn-${type}`);
    const originalHtml = btn.innerHTML;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Paketleniyor...`;
    btn.disabled = true;

    // Hangi pipeline ise onun URL'sini ve beklediği JSON anahtarını seç
    const url = type === 'p1' ? '/common/api/export-pipeline1/' : '/common/api/export-pipeline2/';
    const bodyData = type === 'p1' ? { design_ids: ids } : { upload_ids: ids };

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') || '' },
            body: JSON.stringify(bodyData)
        });

        if (!response.ok) throw new Error("Sunucudan dosya oluşturulamadı.");

        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `Etsy_${type.toUpperCase()}_Export_${new Date().getTime()}.zip`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
        alert("İndirme Hatası: " + err.message);
    } finally {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    }
}

// ==========================================
// GEÇMİŞ GALERİ MOTORU
// ==========================================
let currentHistoryImages = [];
let currentHistoryIndex = 0;

function openHistoryCarousel(type, id) {
    currentHistoryImages = window.historyMockupsCache[type][id] || [];
    if (currentHistoryImages.length === 0) return;
    
    currentHistoryIndex = 0;
    updateHistoryModalUI();
    
    const modal = document.getElementById('history-modal');
    modal.classList.remove('hidden');
    setTimeout(() => modal.classList.add('opacity-100'), 10);
}

function changeHistoryCarousel(direction) {
    currentHistoryIndex += direction;
    if (currentHistoryIndex < 0) currentHistoryIndex = currentHistoryImages.length - 1;
    if (currentHistoryIndex >= currentHistoryImages.length) currentHistoryIndex = 0;
    updateHistoryModalUI();
}

function updateHistoryModalUI() {
    document.getElementById('history-modal-image').src = currentHistoryImages[currentHistoryIndex];
    
    const hasMultiple = currentHistoryImages.length > 1;
    document.getElementById('modal-prev-btn').classList.toggle('hidden', !hasMultiple);
    document.getElementById('modal-next-btn').classList.toggle('hidden', !hasMultiple);
    document.getElementById('history-modal-counter').classList.toggle('hidden', !hasMultiple);
    
    if (hasMultiple) {
        document.getElementById('history-modal-counter').innerText = `${currentHistoryIndex + 1} / ${currentHistoryImages.length}`;
    }
}

function closeHistoryCarousel() {
    const modal = document.getElementById('history-modal');
    modal.classList.remove('opacity-100');
    setTimeout(() => modal.classList.add('hidden'), 300);
}