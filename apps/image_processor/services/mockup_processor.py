import cv2
import numpy as np
import logging
from django.core.files.base import ContentFile
from apps.common.services.thread_helper import ThreadService
from apps.common.services.db_helpers import DatabaseService

# Model yollarını kendi projene göre düzenle
from apps.image_processor.models import MockupResult, MockupItem
from apps.ai.models import DesignVariation
from django.conf import settings
import os
from apps.products.models import ManualUpload


logger = logging.getLogger(__name__)

class MockupEngineService:
    
    @staticmethod
    def apply_design_to_mockup(task):
        """
        OpenCV ile tasarımı şablona giydirir ve doğrudan RAM üzerinden
        MockupResult veritabanına kaydeder.
        """
        design_id = task['design_id']
        item_id = task['item_id']
        force = task['force']

        # Veritabanından objeleri çek
        variation = DatabaseService.get_object_or_none(DesignVariation, id=design_id)
        mockup_item = DatabaseService.get_object_or_none(MockupItem, id=item_id)

        if not variation or not mockup_item:
            return {"success": False, "error": "Tasarım veya Şablon bulunamadı."}

        # --- DB TABANLI CACHE KONTROLÜ ---
        # Dosya sisteminde aramıyoruz, doğrudan DB'de ilişki var mı bakıyoruz.
        existing_result = DatabaseService.find_first_by_filter(
            MockupResult, 
            design_variation=variation, 
            mockup_item=mockup_item
        )

        if existing_result and existing_result.result_image and not force:
            print(f"♻️ CACHE: [Var: {design_id} - Item: {item_id}] zaten mevcut.")
            return {"url": existing_result.result_image.url, "cached": True, "success": True}

        # Eğer DB'de varsa ama "force" edildiyse, eski kaydı silelim (şişmesin)
        if existing_result and force:
            existing_result.delete()

        try:
            # Yolları Al
            mockup_path = mockup_item.mockup_image.path
            design_path = variation.no_bg_image.path if (variation.no_bg_image and variation.no_bg_image.name) else variation.generated_image.path
            coords = mockup_item.placement_data

            # 1. GÖRSELLERİ YÜKLE
            bg_img = cv2.imread(mockup_path, cv2.IMREAD_UNCHANGED)
            design = cv2.imread(design_path, cv2.IMREAD_UNCHANGED)

            if bg_img is None or design is None:
                return {"error": "Görseller diskten okunamadı.", "success": False}

            if bg_img.shape[2] == 4: bg_img = cv2.cvtColor(bg_img, cv2.COLOR_BGRA2BGR)
            if design.shape[2] != 4: design = cv2.cvtColor(design, cv2.COLOR_BGR2BGRA)

            # 2. KOORDİNAT HESAPLAMALARI
            canvas_scale = coords.get('canvas_scale', 1.0)
            real_x = int(coords['left'] / canvas_scale)
            real_y = int(coords['top'] / canvas_scale)
            real_w = int((coords['width'] * coords.get('scaleX', 1.0)) / canvas_scale)
            real_h = int((coords['height'] * coords.get('scaleY', 1.0)) / canvas_scale)
            angle = coords.get('angle', 0)
            is_circle = coords.get('is_circle', False)

            # 3. YENİDEN BOYUTLANDIRMA VE DÖNDÜRME
            design_resized = cv2.resize(design, (real_w, real_h), interpolation=cv2.INTER_AREA)

            if is_circle:
                circle_mask = np.zeros((real_h, real_w), dtype=np.uint8)
                center = (real_w // 2, real_h // 2)
                radius = min(center[0], center[1])
                cv2.circle(circle_mask, center, radius, 255, -1)
                design_resized[:, :, 3] = cv2.bitwise_and(design_resized[:, :, 3], circle_mask)

            if angle != 0:
                center = (real_w // 2, real_h // 2)
                M = cv2.getRotationMatrix2D(center, -angle, 1.0)
                design_resized = cv2.warpAffine(design_resized, M, (real_w, real_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))

            # 4. HEDEF ALAN (ROI) VE GÜVENLİK
            bg_h, bg_w = bg_img.shape[:2]
            start_y, end_y = max(0, real_y), min(bg_h, real_y + real_h)
            start_x, end_x = max(0, real_x), min(bg_w, real_x + real_w)
            
            ds_start_y = 0 if real_y >= 0 else -real_y
            ds_end_y = real_h - ((real_y + real_h) - bg_h) if (real_y + real_h) > bg_h else real_h
            ds_start_x = 0 if real_x >= 0 else -real_x
            ds_end_x = real_w - ((real_x + real_w) - bg_w) if (real_x + real_w) > bg_w else real_w

            roi = bg_img[start_y:end_y, start_x:end_x]
            design_crop = design_resized[ds_start_y:ds_end_y, ds_start_x:ds_end_x]

            # 5. GERÇEKÇİLİK ALGORİTMASI (Senin harika kodun)
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            blur_map = cv2.GaussianBlur(roi_gray, (35, 35), 0)

            sobel_x = cv2.Sobel(blur_map, cv2.CV_64F, 1, 0, ksize=5)
            sobel_y = cv2.Sobel(blur_map, cv2.CV_64F, 0, 1, ksize=5)
            map_x = np.tile(np.arange(design_crop.shape[1]), (design_crop.shape[0], 1)).astype(np.float32)
            map_y = np.tile(np.arange(design_crop.shape[0]).reshape(-1, 1), (1, design_crop.shape[1])).astype(np.float32)

            displacement_intensity = 0.005 * (bg_w / 1000.0)
            map_x += (sobel_x * displacement_intensity).astype(np.float32)
            map_y += (sobel_y * displacement_intensity).astype(np.float32)

            displaced_design = cv2.remap(design_crop, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_TRANSPARENT)

            alpha_mask = displaced_design[:, :, 3] / 255.0
            design_rgb = displaced_design[:, :, :3].astype(np.float32)
            mean_gray = np.mean(blur_map)
            illumination_map = (blur_map / (mean_gray + 1e-5)) 
            illumination_map_3d = cv2.cvtColor(illumination_map.astype(np.float32), cv2.COLOR_GRAY2BGR)

            blended_design = np.clip(design_rgb * illumination_map_3d, 0, 255).astype(np.uint8)

            for c in range(0, 3):
                roi[:, :, c] = (alpha_mask * blended_design[:, :, c] + (1 - alpha_mask) * roi[:, :, c])

            bg_img[start_y:end_y, start_x:end_x] = roi

            # 6. OPENCV GÖRSELİNİ DOĞRUDAN DB'YE KAYDET (Diskte dolaşmadan RAM'den)
            # cv2 görüntüsünü byte dizisine (png) çevir
            is_success, buffer = cv2.imencode(".png", bg_img)
            if not is_success:
                return {"error": "OpenCV görseli encode edemedi.", "success": False}

            # Byte dizisini Django'nun anlayacağı ContentFile objesine çevir
            content_file = ContentFile(buffer.tobytes())
            file_name = f"result_{variation.id}_{mockup_item.id}.png"

            # DB'ye MockupResult Olarak Kaydet
            new_result = MockupResult(
                mockup_item=mockup_item,
                design_variation=variation
            )
            # save metodu, ImageField'a upload_to kurallarına göre diske yazar
            new_result.result_image.save(file_name, content_file, save=True)

            print(f"🚀 ÜRETİM: [Var: {design_id} - Item: {item_id}] başarıyla işlendi ve DB'ye mühürlendi.")
            return {"url": new_result.result_image.url, "cached": False, "success": True}

        except Exception as e:
            logger.error(f"Mockup Engine Hatası: {e}")
            return {"error": str(e), "success": False}

    @classmethod
    def generate_batch_parallel(cls, design_ids, mockup_item_ids, force_recreate):
        """View'dan gelen ID listelerini kombinasyonlara çevirir ve paralel işler."""
        tasks = []
        
        # Her bir tasarım için her bir şablonu eşleştir
        for d_id in design_ids:
            for item_id in mockup_item_ids:
                tasks.append({
                    "design_id": d_id,
                    "item_id": item_id,
                    "force": force_recreate
                })

        print(f"🏭 Toplam {len(tasks)} mockup işlemi paralel olarak başlatılıyor...")
        results = ThreadService.run_parallel(cls.apply_design_to_mockup, tasks, max_workers=5)
        return results

    @staticmethod
    def apply_upload_to_mockup(task):
        """Pipeline 2: Manuel Yüklemeyi (ManualUpload) OpenCV ile şablona giydirir ve diske kaydeder."""
        

        upload_id = task['upload_id']
        item_id = task['item_id']
        force = task['force']

        upload = DatabaseService.get_object_or_none(ManualUpload, id=upload_id)
        mockup_item = DatabaseService.get_object_or_none(MockupItem, id=item_id)

        if not upload or not mockup_item:
            return {"success": False, "error": "Upload veya Şablon bulunamadı."}

        # --- DB TABANLI CACHE KONTROLÜ (Fiziksel dosya kontrolü yerine DB'ye bakıyoruz) ---
        existing_result = DatabaseService.find_first_by_filter(
            MockupResult, 
            manual_upload=upload, 
            mockup_item=mockup_item
        )

        if existing_result and existing_result.result_image and not force:
            print(f"♻️ CACHE: [Upload: {upload_id} - Item: {item_id}] zaten DB'de mevcut.")
            return {"url": existing_result.result_image.url, "path": existing_result.result_image.path, "cached": True, "success": True}

        if existing_result and force:
            existing_result.delete()

        try:
            mockup_path = mockup_item.mockup_image.path
            design_path = upload.image.path
            coords = mockup_item.placement_data

            # 1. GÖRSELLERİ YÜKLE
            with open(mockup_path, "rb") as f:
                bg_img = cv2.imdecode(np.frombuffer(f.read(), np.uint8), cv2.IMREAD_UNCHANGED)
            with open(design_path, "rb") as f:
                design = cv2.imdecode(np.frombuffer(f.read(), np.uint8), cv2.IMREAD_UNCHANGED)

            if bg_img is None or design is None:
                return {"error": "Görseller diskten okunamadı.", "success": False}

            if bg_img.shape[2] == 4: bg_img = cv2.cvtColor(bg_img, cv2.COLOR_BGRA2BGR)
            if design.shape[2] != 4: design = cv2.cvtColor(design, cv2.COLOR_BGR2BGRA)

            # 2. KOORDİNAT VE 3. DÖNDÜRME
            canvas_scale = coords.get('canvas_scale', 1.0)
            real_x = int(coords['left'] / canvas_scale)
            real_y = int(coords['top'] / canvas_scale)
            real_w = int((coords['width'] * coords.get('scaleX', 1.0)) / canvas_scale)
            real_h = int((coords['height'] * coords.get('scaleY', 1.0)) / canvas_scale)
            angle = coords.get('angle', 0)

            design_resized = cv2.resize(design, (real_w, real_h), interpolation=cv2.INTER_AREA)

            if angle != 0:
                center = (real_w // 2, real_h // 2)
                M = cv2.getRotationMatrix2D(center, -angle, 1.0)
                design_resized = cv2.warpAffine(design_resized, M, (real_w, real_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))

            # 4. HEDEF ALAN (ROI) VE 5. BLENDING
            bg_h, bg_w = bg_img.shape[:2]
            start_y, end_y = max(0, real_y), min(bg_h, real_y + real_h)
            start_x, end_x = max(0, real_x), min(bg_w, real_x + real_w)
            
            ds_start_y = 0 if real_y >= 0 else -real_y
            ds_end_y = real_h - ((real_y + real_h) - bg_h) if (real_y + real_h) > bg_h else real_h
            ds_start_x = 0 if real_x >= 0 else -real_x
            ds_end_x = real_w - ((real_x + real_w) - bg_w) if (real_x + real_w) > bg_w else real_w

            roi = bg_img[start_y:end_y, start_x:end_x]
            design_crop = design_resized[ds_start_y:ds_end_y, ds_start_x:ds_end_x]

            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            blur_map = cv2.GaussianBlur(roi_gray, (35, 35), 0)
            
            alpha_mask = design_crop[:, :, 3] / 255.0
            design_rgb = design_crop[:, :, :3]
            
            for c in range(0, 3):
                roi[:, :, c] = (alpha_mask * design_rgb[:, :, c] + (1 - alpha_mask) * roi[:, :, c])

            bg_img[start_y:end_y, start_x:end_x] = roi

            # 6. OPENCV GÖRSELİNİ DOĞRUDAN DB'YE KAYDET (Eski hardcoded diske yazma kodu silindi)
            is_success, buffer = cv2.imencode(".png", bg_img)
            if not is_success:
                return {"error": "OpenCV görseli encode edemedi.", "success": False}

            content_file = ContentFile(buffer.tobytes())
            file_name = f"result_manual_{upload_id}_{item_id}.png"

            new_result = MockupResult(
                mockup_item=mockup_item,
                manual_upload=upload
            )
            # save metodu, ImageField'a upload_to kurallarına göre diske yazar
            new_result.result_image.save(file_name, content_file, save=True)

            print(f"🚀 ÜRETİM: [Upload: {upload_id} - Item: {item_id}] DB'ye yazıldı.")
            return {"url": new_result.result_image.url, "path": new_result.result_image.path, "cached": False, "success": True}

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e), "success": False}

    @classmethod
    def generate_upload_batch_parallel(cls, upload_ids, mockup_item_ids, force_recreate=True):
        """Pipeline 2 ID listelerini ThreadService ile paralel işler."""
        tasks = [{"upload_id": u_id, "item_id": i_id, "force": force_recreate} 
                 for u_id in upload_ids for i_id in mockup_item_ids]

        print(f"🏭 Pipeline 2: Toplam {len(tasks)} mockup işlemi paralel olarak başlatılıyor...")
        return ThreadService.run_parallel(cls.apply_upload_to_mockup, tasks, max_workers=5)