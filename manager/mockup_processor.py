# manager/mockup_processor.py

import cv2
import numpy as np
import os
from django.conf import settings

def process_single_mockup(mockup_path, design_path, coords, output_path):
    """
    Tasarımı belirtilen koordinatlara, kumaş kıvrımlarını (Displacement) ve 
    gölgeleri hesaplayarak son derece gerçekçi bir şekilde giydirir.
    """
    
    # 1. GÖRSELLERİ YÜKLE (Transparanlık kanallarıyla birlikte - IMREAD_UNCHANGED)
    bg_img = cv2.imread(mockup_path, cv2.IMREAD_UNCHANGED)
    design = cv2.imread(design_path, cv2.IMREAD_UNCHANGED)

    if bg_img is None or design is None:
        raise ValueError("Görsellerden biri okunamadı. Yolları kontrol edin.")

    # Arka plan RGB mi RGBA mı kontrol et, RGBA ise RGB'ye çevir (Arka planda şeffaflık istemeyiz)
    if bg_img.shape[2] == 4:
        bg_img = cv2.cvtColor(bg_img, cv2.COLOR_BGRA2BGR)
        
    # Tasarım RGBA değilse hata fırlat (Tasarımın arkası şeffaf olmalı)
    if design.shape[2] != 4:
        # Eğer RGB gelirse zorla RGBA yap (siyahları veya beyazları silmek gerekebilir ama şimdilik standart bırakıyoruz)
        design = cv2.cvtColor(design, cv2.COLOR_BGR2BGRA)

    # 2. KOORDİNATLARI GERÇEK PİKSELLERE ÇEVİR (Frontend Scale Hesabı)
    canvas_scale = coords.get('canvas_scale', 1.0)
    
    # Gerçek X ve Y (Tuval küçültüldüğü için gerçek resimde büyütüyoruz)
    real_x = int(coords['left'] / canvas_scale)
    real_y = int(coords['top'] / canvas_scale)
    
    # Gerçek Genişlik ve Yükseklik (ScaleX/Y kumaştaki esnemeleri de tutar)
    real_w = int((coords['width'] * coords.get('scaleX', 1.0)) / canvas_scale)
    real_h = int((coords['height'] * coords.get('scaleY', 1.0)) / canvas_scale)
    angle = coords.get('angle', 0)
    is_circle = coords.get('is_circle', False)

    # 3. TASARIMI YENİDEN BOYUTLANDIR VE HAZIRLA
    design_resized = cv2.resize(design, (real_w, real_h), interpolation=cv2.INTER_AREA)

    # Dairesel kesim istenmişse (Kupa, tabak, yaka içi vs.)
    if is_circle:
        circle_mask = np.zeros((real_h, real_w), dtype=np.uint8)
        center = (real_w // 2, real_h // 2)
        radius = min(center[0], center[1])
        cv2.circle(circle_mask, center, radius, 255, -1)
        # Tasarımın Alpha (şeffaflık) kanalını maskeye göre kırp
        design_resized[:, :, 3] = cv2.bitwise_and(design_resized[:, :, 3], circle_mask)

    # Döndürme (Rotation) işlemi varsa
    if angle != 0:
        center = (real_w // 2, real_h // 2)
        M = cv2.getRotationMatrix2D(center, -angle, 1.0) # Eksi açı, çünkü OpenCV ters yönde döner
        design_resized = cv2.warpAffine(design_resized, M, (real_w, real_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))

    # 4. HEDEF ALANI (ROI - Region of Interest) BELİRLE VE GÜVENLİK KONTROLÜ
    bg_h, bg_w = bg_img.shape[:2]
    
    # Resim sınırlarını aşmamak için koordinatları kırp
    start_y, end_y = max(0, real_y), min(bg_h, real_y + real_h)
    start_x, end_x = max(0, real_x), min(bg_w, real_x + real_w)
    
    # Tasarımın da taşan kısımlarını kırp
    ds_start_y = 0 if real_y >= 0 else -real_y
    ds_end_y = real_h - ((real_y + real_h) - bg_h) if (real_y + real_h) > bg_h else real_h
    ds_start_x = 0 if real_x >= 0 else -real_x
    ds_end_x = real_w - ((real_x + real_w) - bg_w) if (real_x + real_w) > bg_w else real_w

    roi = bg_img[start_y:end_y, start_x:end_x]
    design_crop = design_resized[ds_start_y:ds_end_y, ds_start_x:ds_end_x]

    # 5. GERÇEKÇİLİK İÇİN SANDVİÇ MODELİ (DISPLACEMENT & BLENDING) - GÜNCELLENDİ
    
    # ROI'nin gri tonlamalı (Grayscale) halini alıyoruz
    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # HATA 1 ÇÖZÜMÜ: İplik dokusunu (noise) yok etmek için Blur'u devasa yapıyoruz.
    # Sadece ana kumaş katlanmaları ve kırışıklıklar hayatta kalacak.
    blur_map = cv2.GaussianBlur(roi_gray, (35, 35), 0)

    # --- Displacement Map (Kırışıklıklara göre bükme) ---
    sobel_x = cv2.Sobel(blur_map, cv2.CV_64F, 1, 0, ksize=5)
    sobel_y = cv2.Sobel(blur_map, cv2.CV_64F, 0, 1, ksize=5)
    
    map_x = np.tile(np.arange(design_crop.shape[1]), (design_crop.shape[0], 1)).astype(np.float32)
    map_y = np.tile(np.arange(design_crop.shape[0]).reshape(-1, 1), (1, design_crop.shape[1])).astype(np.float32)

    # Bükülme şiddetini biraz artırabiliriz çünkü blur'u çok artırdık
    # ÇÖZÜM: Dinamik (Çözünürlükten Bağımsız) Bükülme Şiddeti
    # 1000 piksellik bir resimde ideal değerin 0.005 olduğunu referans alıyoruz
    base_intensity = 0.005
    reference_width = 1000.0
    
    # Arka plan görselinin genişliğine (bg_w) göre dinamik çarpan hesapla
    displacement_intensity = base_intensity * (bg_w / reference_width)
    map_x += (sobel_x * displacement_intensity).astype(np.float32)
    map_y += (sobel_y * displacement_intensity).astype(np.float32)

    # Tasarımı dalgalandır
    displaced_design = cv2.remap(design_crop, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_TRANSPARENT)

    # --- HATA 2 ÇÖZÜMÜ: Smart Illumination (Akıllı Işıklandırma) ---
    alpha_mask = displaced_design[:, :, 3] / 255.0
    design_rgb = displaced_design[:, :, :3].astype(np.float32)

    # Tişörtün o bölgesindeki "Ortalama" parlaklığı buluyoruz
    mean_gray = np.mean(blur_map)
    
    # Pikselleri ortalamaya bölerek bir "Işık Haritası" çıkartıyoruz
    # (Örn: Ortalama 50 ise; 40 olan yerler 0.8 (Gölge), 60 olan yerler 1.2 (Işık) değeri alır)
    # Bu sayede tişört siyah da olsa, beyaz da olsa tasarımın kendi rengi ölmez!
    illumination_map = (blur_map / (mean_gray + 1e-5)) 
    
    # Işık haritasını 3 kanallı (RGB) formata getir
    illumination_map_3d = cv2.cvtColor(illumination_map.astype(np.float32), cv2.COLOR_GRAY2BGR)

    # Işığı tasarımla çarp ve 255'i aşan değerleri kırp (Patlamayı önle)
    blended_design = np.clip(design_rgb * illumination_map_3d, 0, 255).astype(np.uint8)

    # Sonucu ana görsele alfa maskesiyle bindir
    for c in range(0, 3):
        roi[:, :, c] = (alpha_mask * blended_design[:, :, c] + (1 - alpha_mask) * roi[:, :, c])

    # 6. SONUCU ANA GÖRSELE YERLEŞTİR VE KAYDET
    bg_img[start_y:end_y, start_x:end_x] = roi

    # Çıktı klasörü yoksa oluştur
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Kaliteyi bozmadan kaydet
    cv2.imwrite(output_path, bg_img)
    print(f"✅ Görsel başarıyla işlendi ve kaydedildi: {output_path}")
    
    return output_path