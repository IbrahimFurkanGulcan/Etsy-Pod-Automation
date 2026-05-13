
// SPA State (Durum) Yönetimi
let uploadedMockups = []; 
let currentEditingId = null;
let currentGroupId = null; // Hangi koleksiyondayız? (Null ise yeni)

let canvas = null;
let selectionRect = null;

// ==========================================
// YÖNLENDİRME (ROUTING) VE SPA GÖRÜNÜMLERİ
// ==========================================

function showCollectionsView() {
    document.getElementById('view-editor').classList.add('hidden');
    document.getElementById('view-collections').classList.remove('hidden');
    uploadedMockups = [];
    currentGroupId = null;
}

function createNewCollection() {
    document.getElementById('view-collections').classList.add('hidden');
    document.getElementById('view-editor').classList.remove('hidden');
    
    // Temiz Sayfa
    currentGroupId = null;
    uploadedMockups = [];
    document.getElementById('group-name-input').value = "Yeni Koleksiyon";
    document.getElementById('mockup-list-container').innerHTML = `
        <div id="empty-state" class="col-span-full p-8 text-center text-gray-400 border-2 border-dashed border-gray-200 rounded-xl">
            <i class="fa-regular fa-images text-4xl mb-3 opacity-50"></i>
            <p>Bu koleksiyon boş.</p>
            <p class="text-sm">Yukarıdan 'Görsel Ekle' butonuna basarak başlayın.</p>
        </div>
    `;
}

function openCollection(groupId) {
    document.getElementById('view-collections').classList.add('hidden');
    document.getElementById('view-editor').classList.remove('hidden');
    
    currentGroupId = groupId;
    const groupData = serverGroupsData.find(g => g.id === groupId);
    
    document.getElementById('group-name-input').value = groupData.name;
    document.getElementById('mockup-list-container').innerHTML = ''; // Listeyi temizle
    
    // Veritabanındaki resimleri çalışma masasına diz (Deep Copy)
    uploadedMockups = JSON.parse(JSON.stringify(groupData.items));
    
    uploadedMockups.forEach(mockup => {
        renderMockupCard(mockup, true); // true = Bu DB'den geldi etiketi koy
    });
}

// ==========================================
// RESİM YÜKLEME VE KART ÇİZİMİ
// ==========================================

document.getElementById('mockup-upload-input')?.addEventListener('change', function(e) {
    const files = e.target.files;
    if (files.length === 0) return;

    const emptyState = document.getElementById('empty-state');
    if(emptyState) emptyState.remove();

    Array.from(files).forEach((file, index) => {
        const id = 'mockup_' + Date.now() + '_' + index; 
        
        // 🚀 BÜYÜK DEĞİŞİM: FileReader ile Base64'e çevirmek yerine 
        // tarayıcının hafızasında geçici, süper hafif bir URL yaratıyoruz
        const objectUrl = URL.createObjectURL(file);
        
        const mockupData = {
            id: id,
            file: file, // 🚀 Asıl dosyayı (Binary) kaydetmek için değişkende saklıyoruz!
            name: file.name.split('.')[0].replace(/[-_]/g, ' '),
            url: objectUrl, // Canvas ve UI bu URL'i kullanacak
            coordinates: null
        };
        uploadedMockups.push(mockupData);
        renderMockupCard(mockupData, false);
    });
});

function renderMockupCard(mockup, isFromDB = false) {
    const container = document.getElementById('mockup-list-container');
    const statusHtml = mockup.coordinates 
        ? `<span class="bg-indigo-100 text-indigo-700 text-xs px-2 py-1 rounded-full font-bold shadow-sm"><i class="fa-solid fa-crop-simple mr-1"></i>Alan Hazır</span>`
        : `<span class="bg-yellow-100 text-yellow-700 text-xs px-2 py-1 rounded-full font-bold shadow-sm animate-pulse"><i class="fa-solid fa-triangle-exclamation mr-1"></i>Alan Bekleniyor</span>`;
        
    const dbBadge = isFromDB ? `<div class="absolute -top-2 -right-2 bg-emerald-500 text-white text-[10px] font-bold px-2 py-1 rounded-full shadow z-10">KAYITLI</div>` : '';

    const cardHTML = `
        <div id="card_${mockup.id}" class="flex items-center p-3 border-2 border-dashed border-indigo-200 rounded-xl hover:border-indigo-400 hover:shadow-md transition bg-white group relative">
            ${dbBadge}
            <div class="w-16 h-16 rounded bg-gray-100 border overflow-hidden shrink-0">
                <img src="${mockup.url}" class="w-full h-full object-cover">
            </div>
            <div class="ml-4 flex-1 min-w-0">
                <input type="text" value="${mockup.name}" class="text-sm font-bold text-gray-800 truncate w-full border-none p-0 focus:ring-0 bg-transparent hover:bg-gray-50 rounded cursor-text" onchange="updateMockupName('${mockup.id}', this.value)">
                <div class="mt-1" id="status_${mockup.id}">
                    ${statusHtml}
                </div>
            </div>
            <div class="ml-2 flex gap-1 opacity-0 group-hover:opacity-100 transition">
                <button onclick="openEditorModal('${mockup.id}')" class="p-2 text-indigo-600 hover:bg-indigo-100 rounded transition" title="Düzenle">
                    <i class="fa-solid fa-pen-to-square"></i>
                </button>
                <button onclick="removeMockup('${mockup.id}')" class="p-2 text-red-400 hover:bg-red-50 rounded transition" title="Sil">
                    <i class="fa-solid fa-times"></i>
                </button>
            </div>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', cardHTML);
    
    // Koordinatı varsa kenarlığı düz yap (tamamlanmış hissi)
    if(mockup.coordinates) {
        const card = document.getElementById(`card_${mockup.id}`);
        card.classList.remove('border-dashed', 'border-indigo-200');
        card.classList.add('border-solid', 'border-indigo-500');
    }
}

function updateMockupName(id, newName) {
    const mockup = uploadedMockups.find(m => m.id === id);
    if (mockup) mockup.name = newName;
}

function removeMockup(id) {
    uploadedMockups = uploadedMockups.filter(m => m.id !== id);
    document.getElementById(`card_${id}`).remove();
    // Not: DB'den silme işlemi güvenlik gereği direkt arayüzden değil, ayrı bir POST isteğiyle yapılmalı.
    // Şimdilik sadece çalışma masasından kaldırıyor.
}

// ==========================================
// FABRIC.JS EDİTÖRÜ
// ==========================================

function openEditorModal(id) {
    currentEditingId = id;
    const mockup = uploadedMockups.find(m => m.id === id);
    if (!mockup) return;

    document.getElementById('mockup-editor-modal').classList.remove('hidden');

    if (canvas) canvas.dispose();
    canvas = new fabric.Canvas('mockup-canvas', { selection: false, preserveObjectStacking: true });

    fabric.Image.fromURL(mockup.url, function(img) {
        const maxWidth = 800;
        let scale = 1;
        if (img.width > maxWidth) scale = maxWidth / img.width;

        canvas.setWidth(img.width * scale);
        canvas.setHeight(img.height * scale);
        img.scale(scale);
        canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas));

        createSelectionRect(mockup.coordinates, img.width * scale, img.height * scale);
    });
}

function createSelectionRect(existingCoords, canvasWidth, canvasHeight) {
    const rectOptions = existingCoords || {
        left: canvasWidth / 2 - 100, top: canvasHeight / 2 - 120, width: 200, height: 240, angle: 0, scaleX: 1, scaleY: 1
    };

    selectionRect = new fabric.Rect({
        ...rectOptions,
        fill: 'rgba(99, 102, 241, 0.4)', stroke: '#4f46e5', strokeWidth: 2, cornerColor: '#ffffff', cornerStrokeColor: '#4f46e5', cornerSize: 12, transparentCorners: false, lockUniScaling: true, hasBorders: true, hasControls: true
    });

    canvas.add(selectionRect);
    canvas.setActiveObject(selectionRect);
    canvas.on('object:modified', updateCoordinateText);
    canvas.on('object:moving', updateCoordinateText);
    canvas.on('object:scaling', updateCoordinateText);
    canvas.on('object:rotating', updateCoordinateText);
    updateCoordinateText();
}

function updateCoordinateText() {
    if (!selectionRect) return;
    
    // Gerçek boyutları hesapla
    const realWidth = selectionRect.width * selectionRect.scaleX;
    const realHeight = selectionRect.height * selectionRect.scaleY;
    
    document.getElementById('live-coordinates').innerHTML = 
        `<span class="text-indigo-500 font-bold">X:</span> ${Math.round(selectionRect.left)} <span class="mx-2">|</span> ` +
        `<span class="text-indigo-500 font-bold">Y:</span> ${Math.round(selectionRect.top)} <span class="mx-2">|</span> ` +
        `<span class="text-indigo-500 font-bold">Boyut:</span> ${Math.round(realWidth)}x${Math.round(realHeight)} <span class="mx-2">|</span> ` +
        `<span class="text-indigo-500 font-bold">Açı:</span> ${Math.round(selectionRect.angle || 0)}°`;
}

function saveMockupCoordinates() {
    if (!selectionRect || !currentEditingId) return;
    const mockupIndex = uploadedMockups.findIndex(m => m.id === currentEditingId);
    if (mockupIndex === -1) return;

    uploadedMockups[mockupIndex].coordinates = {
        left: selectionRect.left, top: selectionRect.top, width: selectionRect.width, height: selectionRect.height, scaleX: selectionRect.scaleX, scaleY: selectionRect.scaleY, angle: selectionRect.angle, canvas_scale: canvas.backgroundImage.scaleX, is_circle: selectionRect.rx > 0
    };

    document.getElementById(`status_${currentEditingId}`).innerHTML = `<span class="bg-indigo-100 text-indigo-700 text-xs px-2 py-1 rounded-full font-bold shadow-sm"><i class="fa-solid fa-crop-simple mr-1"></i>Alan Hazır</span>`;
    const card = document.getElementById(`card_${currentEditingId}`);
    card.classList.remove('border-dashed', 'border-indigo-200');
    card.classList.add('border-solid', 'border-indigo-500');

    closeEditorModal();
}

function closeEditorModal() {
    document.getElementById('mockup-editor-modal').classList.add('hidden');
    currentEditingId = null;
}

function applyToAllMockups() {
    const referenceMockup = uploadedMockups.find(m => m.coordinates !== null);
    if (!referenceMockup) return alert("Önce en az bir resmin alanını belirlemelisiniz!");
    if (!confirm("İlk alan tüm YENİ resimlere kopyalanacak. Onaylıyor musunuz?")) return;

    uploadedMockups.forEach(m => {
        if (m.id !== referenceMockup.id && m.coordinates === null) {
            m.coordinates = JSON.parse(JSON.stringify(referenceMockup.coordinates));
            document.getElementById(`status_${m.id}`).innerHTML = `<span class="bg-indigo-100 text-indigo-700 text-xs px-2 py-1 rounded-full font-bold shadow-sm"><i class="fa-solid fa-copy mr-1"></i>Alan Kopyalandı</span>`;
            const card = document.getElementById(`card_${m.id}`);
            card.classList.remove('border-dashed', 'border-indigo-200');
            card.classList.add('border-solid', 'border-indigo-500');
        }
    });
}

// ==========================================
// BACKEND'E GÖNDERME (FETCH)
// ==========================================

async function saveAllToDatabase() {
    const groupName = document.getElementById('group-name-input').value.trim();
    if(!groupName) return alert("Lütfen bu koleksiyon için bir isim belirleyin!");

    const unready = uploadedMockups.filter(m => m.coordinates === null);
    if (unready.length > 0) return alert(`Tüm mockupların alanını belirleyin. ${unready.length} eksik var.`);

    const btn = document.getElementById('btn-save-all');
    const originalText = btn.innerHTML;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin mr-2"></i>Kaydediliyor...`;
    btn.disabled = true;

    // 🚀 BÜYÜK DEĞİŞİM: JSON objesi yerine Multipart FormData kullanıyoruz.
    const formData = new FormData();
    formData.append('group_id', currentGroupId);
    formData.append('group_name', groupName);

    uploadedMockups.forEach(mockup => {
        if (mockup.id.startsWith('db_')) {
            // Zaten veritabanında olanlar için sadece koordinat ve ismini gönder
            formData.append(`name_${mockup.id}`, mockup.name);
            formData.append(`coords_${mockup.id}`, JSON.stringify(mockup.coordinates));
        } else if (mockup.id.startsWith('mockup_')) {
            // Yeni olanlar için dosyayı (file), adını ve koordinatını gönder
            formData.append(`file_${mockup.id}`, mockup.file);
            formData.append(`name_${mockup.id}`, mockup.name);
            formData.append(`coords_${mockup.id}`, JSON.stringify(mockup.coordinates));
        }
    });

    try {
        const response = await fetch('/image_processor/api/save-mockups/', { // url ismini urls.py a göre yazdım
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken') 
                // DİKKAT: FormData kullanırken 'Content-Type' yazılmaz!
                // Tarayıcı doğru 'boundary' (sınır) değerini otomatik ekler.
            },
            body: formData
        });

        const data = await response.json();

        if (data.status === 'success') {
            alert(data.message);
            window.location.reload(); 
        } else {
            alert("Hata: " + data.message);
            btn.innerHTML = originalText;
            btn.disabled = false;
        }

    } catch (error) {
        alert("Bağlantı hatası oluştu!");
        console.error(error);
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

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

// ŞEKİL DÜZENLEME FONKSİYONLARI
function makeSquare() {
    if (!selectionRect) return;
    // En büyük kenarı baz alarak tam kare yap
    const size = Math.max(selectionRect.width * selectionRect.scaleX, selectionRect.height * selectionRect.scaleY);
    
    selectionRect.set({
        width: size / selectionRect.scaleX,
        height: size / selectionRect.scaleX,
        scaleY: selectionRect.scaleX, // Oranları eşitle
        rx: 0, // Köşeleri sivrilt
        ry: 0
    });
    canvas.renderAll();
    updateCoordinateText();
}

function makeCircle() {
    if (!selectionRect) return;
    const size = Math.max(selectionRect.width * selectionRect.scaleX, selectionRect.height * selectionRect.scaleY);
    
    const unscaledSize = size / selectionRect.scaleX;
    
    selectionRect.set({
        width: unscaledSize,
        height: unscaledSize,
        scaleY: selectionRect.scaleX,
        rx: unscaledSize / 2, // Köşeleri %50 yuvarla (Tam daire)
        ry: unscaledSize / 2
    });
    canvas.renderAll();
    updateCoordinateText();
}