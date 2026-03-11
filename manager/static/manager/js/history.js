// static/manager/js/history.js

function deleteData(productId, target) {
    let msg = target === 'full' ? "Bu analizi tamamen silmek istediğinize emin misiniz? (Tasarım ve SEO dahil)" : 
              target === 'design' ? "Sadece üretilen tasarımları silmek istediğinize emin misiniz?" : 
              "Sadece SEO verilerini silmek istediğinize emin misiniz?";
              
    if (!confirm(msg)) return;

    const formData = new FormData();
    formData.append('product_id', productId);
    formData.append('target', target);

    // DİKKAT: URL'yi artık HTML'den gelen global değişkenden (window.URLS) alıyoruz!
    fetch(window.URLS.deleteHistory, {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            if (target === 'full') {
                const card = document.getElementById(`card-${productId}`);
                if (card) {
                    card.style.opacity = '0';
                    setTimeout(() => card.remove(), 300);
                }
            } else {
                window.location.reload(); 
            }
        } else {
            alert("Hata: " + data.message);
        }
    })
    .catch(err => alert("Sistemsel bir hata oluştu."));
}