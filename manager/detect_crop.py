import os
import json
import requests
import replicate
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from dotenv import load_dotenv
from .models import EtsyProduct

# .env dosyasını yükle
load_dotenv()

def download_image_from_url(image_url):
    print(f"📥 Resim indiriliyor: {image_url}")
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content)).convert("RGB")
        return image
    except Exception as e:
        print(f"❌ Resim indirme hatası: {e}")
        return None

# --- DÜZELTİLMİŞ SEÇİM MANTIĞI ---
def get_optimized_bounding_box(detections_output, image_width, image_height):
    """
    Grounding DINO sonuçlarını analiz eder.
    YAPILAN DÜZELTME: Gelen veri {'detections': [...]} formatında olduğu için
    önce sözlükten listeyi çıkarır, sonra işler.
    """
    if not detections_output:
        return None

    detections_list = []

    # 1. ADIM: VERİ YAPISINI ÇÖZ (Dict -> List)
    # API cevabı string ise JSON'a çevir
    if isinstance(detections_output, str):
        try:
            detections_output = json.loads(detections_output)
        except:
            return None

    # Eğer Sözlük (Dict) geldiyse 'detections' veya 'objects' anahtarını bul
    if isinstance(detections_output, dict):
        if 'detections' in detections_output:
            detections_list = detections_output['detections']
        elif 'objects' in detections_output:
            detections_list = detections_output['objects']
        else:
            print(f"⚠️ Beklenmedik API Yapısı: {detections_output.keys()}")
            return None
    # Eğer zaten liste geldiyse direkt kullan
    elif isinstance(detections_output, list):
        detections_list = detections_output
    
    # Hala liste elde edemediysek çık
    if not isinstance(detections_list, list):
        print(f"⚠️ Veri formatı çözülemedi: {type(detections_output)}")
        return None

    print(f"📏 Resim Boyutu: {image_width}x{image_height} ({image_width*image_height} px)")
    print(f"📊 İşlenecek Tespit Sayısı: {len(detections_list)}")
    
    candidates = []

    for det in detections_list:
        # Listenin içindeki her bir öğe bir sözlük olmalı
        if not isinstance(det, dict): continue
        
        # 'bbox' veya 'box' anahtarını al
        bbox = det.get('bbox') or det.get('box')
        score = det.get('confidence') or det.get('score') or 0.0
        label = det.get('label', 'unknown')

        if not bbox: continue

        # Koordinatları Al: [x1, y1, x2, y2]
        # (API genelde sol-üst ve sağ-alt köşe döner)
        x1, y1, x2, y2 = bbox
        
        # Normalize Kontrolü (0-1 arasındaysa piksele çevir)
        if x2 <= 1.0 and y2 <= 1.0: 
            x1 = x1 * image_width
            y1 = y1 * image_height
            x2 = x2 * image_width
            y2 = y2 * image_height
        
        # Alan Hesabı
        box_w = x2 - x1
        box_h = y2 - y1
        box_area = box_w * box_h
        total_area = image_width * image_height
        area_ratio = box_area / total_area

        candidates.append({
            'bbox': [x1, y1, x2, y2],
            'score': score,
            'area_ratio': area_ratio,
            'label': label
        })

    # 2. ADIM: SIRALA VE SEÇ (Skor Öncelikli)
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    selected_candidate = None
    MIN_AREA_THRESHOLD = 0.05  # %5'in altındakileri logo diye ele

    for i, cand in enumerate(candidates):
        print(f"   [{i+1}] Skor: {cand['score']:.2f} | Alan: %{cand['area_ratio']*100:.2f}")
        
        if cand['area_ratio'] > MIN_AREA_THRESHOLD:
            selected_candidate = cand
            print(f"      ✅ SEÇİLDİ (Skor yüksek, Alan yeterli)")
            break
        else:
            print(f"      ❌ ATLANDI (Alan çok küçük)")

    # Yedek Plan: Hiçbiri uymazsa en yüksek skorluyu al
    if not selected_candidate and candidates:
        print("⚠️ Uygun boyutta kutu yok, mecburen en yüksek skorlu alınıyor.")
        selected_candidate = candidates[0]

    if not selected_candidate:
        return None

    # 3. ADIM: PADDING (Kenar Payı Ekle)
    # Tasarımın tam sınırından kesmemek için %01 genişlet
    x_min, y_min, x_max, y_max = selected_candidate['bbox']
    w = x_max - x_min
    h = y_max - y_min
    
    pad_x = w * 0.01
    pad_y = h * 0.01
    
    final_x1 = max(0, x_min - pad_x)
    final_y1 = max(0, y_min - pad_y)
    final_x2 = min(image_width, x_max + pad_x)
    final_y2 = min(image_height, y_max + pad_y)
    
    return (final_x1, final_y1, final_x2, final_y2)


def crop_and_save_product_design(product_id):
    print(f"\n✂️ KIRPMA İŞLEMİ (ID: {product_id})")
    
    try:
        product = EtsyProduct.objects.get(id=product_id)
    except EtsyProduct.DoesNotExist:
        return None

    # Eğer zaten kırpılmış resim varsa tekrar yapma (İsteğe bağlı)
    if product.cropped_image and product.cropped_image.name:
        # Dosyanın tam yolunu bul
        file_path = product.cropped_image.path
        
        if os.path.exists(file_path):
            print(f"✅ Görsel diskte mevcut, tekrar kırpılmayacak: {product.cropped_image.name}")
            return product.cropped_image
        else:
            print("⚠️ Veritabanında kayıt var ama dosya silinmiş. Yeniden oluşturuluyor...")

    if not product.image_url: return None

    img = download_image_from_url(product.image_url)
    if not img: return None

    print("🦕 DINO ile analiz ediliyor...")
    

    try:
        output = replicate.run(
            "adirik/grounding-dino:efd10a8ddc57ea28773327e881ce95e20cc1d734c589f7dd01d2036921ed78aa",
            input={"image": product.image_url, "query": "printed graphic design", "box_threshold": 0.20, "text_threshold": 0.20}
        )
        # Fonksiyonu çağırmadan önce import ettiğinden emin ol veya yukarıya kopyala
        crop_box = get_optimized_bounding_box(output, img.width, img.height)
    except Exception as e:
        print(f"⚠️ DINO Hatası: {e}")
        crop_box = None

    if not crop_box:
        print("⚠️ Tespit yapılamadı, varsayılan kesim.")
        crop_box = (img.width*0.4, img.height*0.4, img.width*0.4, img.height*0.4)

    cropped_img = img.crop(crop_box)
    
    # --- VERİTABANINA KAYIT ---
    # Resmi bellekte bir dosyaya çevir
    img_io = BytesIO()
    cropped_img.save(img_io, format='PNG')
    
    # Django File nesnesi oluştur
    file_name = f"crop_{product.id}.png"
    product.cropped_image.save(file_name, ContentFile(img_io.getvalue()), save=True)
    
    print(f"💾 Kırpılan resim veritabanına kaydedildi: {product.cropped_image.name}")
    
    return product.cropped_image