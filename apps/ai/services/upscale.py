import logging
from apps.ai.services.client import UniversalAIClient
from apps.common.services.file_helper import FileService
from apps.ai.services.config.model_registry import ModelRegistry
from apps.ai.models import DesignVariation

logger = logging.getLogger(__name__)

class UpscaleService:
    @staticmethod
    def process(variation, model_id, api_key):
        """Tasarımın çözünürlüğünü artırır ve kaydeder."""
        config = ModelRegistry.get(model_id)
        if not config:
            logger.error(f"❌ Upscale modeli '{model_id}' bulunamadı!")
            return False

        # Zaten varsa atla (Hızlandırır)
        if variation.upscaled_image and variation.upscaled_image.name:
            print(f"ℹ️ [ID: {variation.id}] Upscale zaten mevcut, atlanıyor.")
            return True

        print(f"🚀 [ID: {variation.id}] {model_id} ile Upscale yapılıyor...")
        ai_client = UniversalAIClient(api_key=api_key, platform=config["platform"])

        try:
            # İşleniyor statüsüne çek
            variation.status = DesignVariation.Status.PROCESSING
            variation.save(update_fields=['status'])

            current_path = variation.no_bg_image.path if (variation.no_bg_image and variation.no_bg_image.name) else variation.generated_image.path
            up_url = ai_client.execute(model_id=model_id, file_path=current_path)

            if isinstance(up_url, list): up_url = up_url[0]

            if not up_url or not str(up_url).startswith("http"):
                logger.warning(f"⚠️ Upscale URL alınamadı: {up_url}")
                return False

            content_file = FileService.download_image_as_contentfile(up_url)
            if content_file:
                file_name = f"upscaled_{variation.product.id}_{variation.id}.png"
                # Veritabanına kaydet
                variation.upscaled_image.save(file_name, content_file, save=True)
                print(f"✅ BAŞARILI: [ID: {variation.id}] Upscale Tamam.")
                return True
            return False

        except Exception as e:
            logger.error(f"❌ Upscale Hatası (ID: {variation.id}): {e}")
            return False