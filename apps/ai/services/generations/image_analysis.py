import logging
from apps.ai.services.client import UniversalAIClient
from apps.common.services.db_helpers import DatabaseService

# Konfigürasyonları ve Promptları import ediyoruz
from apps.ai.services.config.model_registry import ModelRegistry
from apps.ai.services.config.system_prompts import DEFAULT_SYSTEM_PROMPTS 
from apps.ai.services.config.user_prompts import DEFAULT_USER_PROMPTS 

from apps.ai.models import SeoOptimization

logger = logging.getLogger(__name__)

class VisionAnalysisService:
    """Yüklenen tasarımları Vision modelleri ile analiz eder."""

    @staticmethod
    def analyze_design(manual_upload, api_key, model_id="gpt-4o-vision", force_recreate=False):
        """
        Görseli GPT-4o-Vision gibi modellere analiz ettirir ve sonucu SeoOptimization tablosuna kaydeder.
        """
        # --- 1. CACHE KONTROLÜ ---
        existing_seo = DatabaseService.find_first_by_filter(
            SeoOptimization, 
            manual_upload=manual_upload
        )
        
        if existing_seo and existing_seo.vision_analysis and not force_recreate:
            print(f"♻️ CACHE: '{manual_upload.original_filename}' görseli zaten analiz edilmiş.")
            return {"success": True, "analysis": existing_seo.vision_analysis}

        # --- 2. KONFİGÜRASYON VE PROMPT ÇEKİMİ ---
        # Registry'den model ayarlarını al
        config = ModelRegistry.get(model_id)
        if not config:
            return {"success": False, "error": f"Model '{model_id}' kayıt defterinde bulunamadı."}

        # Merkezi prompt dosyalarından metinleri al
        system_prompt = DEFAULT_SYSTEM_PROMPTS.get(model_id, "")
        user_prompt = DEFAULT_USER_PROMPTS.get(model_id, "")

        if not system_prompt or not user_prompt:
            return {"success": False, "error": "Vision modeli için gerekli promptlar bulunamadı."}

        print(f"👁️ VİZYON: '{manual_upload.original_filename}' analiz ediliyor... (Model: {model_id})")

        # --- 3. AI İSTEĞİ ATMA ---
        # Config'ten gelen platform bilgisi ile istemciyi başlat[cite: 10]
        ai_client = UniversalAIClient(api_key=api_key, platform=config["platform"])
        
        try:
            raw_response = ai_client.execute(
                model_id=model_id,
                prompt=user_prompt,
                system_prompt=system_prompt,
                file_path=manual_upload.image.path
            )

            if not raw_response:
                return {"success": False, "error": "Vision modeli boş yanıt döndürdü."}

            analysis_text = str(raw_response).strip()

            # --- 4. VERİTABANINA KAYIT ---
            seo_record, created = DatabaseService.update_or_create_with_log(
                SeoOptimization,
                manual_upload=manual_upload,
                defaults={
                    "vision_analysis": analysis_text
                }
            )

            if seo_record:
                print(f"✅ VİZYON BAŞARILI: Analiz DB'ye kaydedildi (SEO ID: {seo_record.id})")
                return {"success": True, "analysis": analysis_text}
            
            return {"success": False, "error": "Analiz veritabanına kaydedilemedi."}

        except Exception as e:
            logger.error(f"Vision Analysis Hatası: {e}")
            return {"success": False, "error": str(e)}