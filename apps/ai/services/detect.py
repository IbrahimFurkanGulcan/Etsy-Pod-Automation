import json
from apps.ai.services.client import UniversalAIClient
from apps.ai.services.config.model_registry import ModelRegistry
from apps.ai.services.config.user_prompts import DEFAULT_USER_PROMPTS

class DetectService:
    @staticmethod
    def get_optimized_bounding_box(detections_output, image_width, image_height):
        """
        Grounding DINO sonuçlarını analiz eder, alan hesabı yapar ve padding ekler.
        """
        if not detections_output:
            return None

        detections_list = []

        # 1. ADIM: VERİ YAPISINI ÇÖZ
        if isinstance(detections_output, str):
            try:
                detections_output = json.loads(detections_output)
            except:
                return None

        if isinstance(detections_output, dict):
            if 'detections' in detections_output:
                detections_list = detections_output['detections']
            elif 'objects' in detections_output:
                detections_list = detections_output['objects']
            else:
                print(f"⚠️ Beklenmedik API Yapısı: {detections_output.keys()}")
                return None
        elif isinstance(detections_output, list):
            detections_list = detections_output
        
        if not isinstance(detections_list, list):
            return None

        print(f"📏 Resim Boyutu: {image_width}x{image_height} ({image_width*image_height} px)")
        print(f"📊 İşlenecek Tespit Sayısı: {len(detections_list)}")
        
        candidates = []

        for det in detections_list:
            if not isinstance(det, dict): continue
            
            bbox = det.get('bbox') or det.get('box')
            score = det.get('confidence') or det.get('score') or 0.0
            label = det.get('label', 'unknown')

            if not bbox: continue

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

        # 2. ADIM: SIRALA VE SEÇ (Skor Öncelikli ve Alan Kontrollü)
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

        if not selected_candidate and candidates:
            print("⚠️ Uygun boyutta kutu yok, mecburen en yüksek skorlu alınıyor.")
            selected_candidate = candidates[0]

        if not selected_candidate:
            return None

        # 3. ADIM: PADDING (Kenar Payı Ekle)
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


    @staticmethod
    def detect_design_coordinates(image_url, api_key, image_width, image_height):
        print("🦕 DINO ile analiz ediliyor...")
        client = UniversalAIClient(api_key=api_key)
        model_id = "grounding-dino"
        
        try:
            # 1. Model ayarlarını Registry'den dinamik olarak çek
            config = ModelRegistry.get(model_id)
            if not config:
                print(f"❌ Hata: '{model_id}' model konfigürasyonu bulunamadı!")
                return None

            schema = config["schema"]
            model_version = config["endpoint"]
            
            # 2. Varsayılan parametreleri al (box_threshold, text_threshold)
            input_data = config["default_params"].copy()
            
            # 3. Prompt'u merkezi prompt sözlüğünden çek
            query_prompt = DEFAULT_USER_PROMPTS.get(model_id, "printed graphic design")

            # 4. Şemadaki anahtarlara göre input_data'yı dinamik doldur
            input_data[schema["image_key"]] = image_url
            input_data[schema["prompt_key"]] = query_prompt
            
            # 5. API'yi eski ve güvenilir run_detection metoduyla tetikle
            output = client.run_detection(model_version, input_data)
            
            if not output:
                print("⚠️ DINO API'den boş yanıt döndü.")
                return None
                
            # 6. Çıktıyı ayrıştırıp koordinatları al
            crop_box = DetectService.get_optimized_bounding_box(output, image_width, image_height)
            return crop_box
            
        except Exception as e:
            print(f"❌ DINO Hatası: {e}")
            return None