import logging
from apps.ai.services.client import UniversalAIClient
from apps.common.services.file_helper import FileService
from apps.ai.services.config.model_registry import ModelRegistry
from apps.ai.models import DesignVariation

logger = logging.getLogger(__name__)

class BackgroundRemovalService:
    @staticmethod
    def process(variation, model_id, api_key):
        """Tasarımın arka planını siler ve kaydeder."""
        config = ModelRegistry.get(model_id)
        if not config:
            logger.error(f"❌ BG Remover modeli '{model_id}' bulunamadı!")
            return False

        if variation.no_bg_image and variation.no_bg_image.name:
            print(f"ℹ️ [ID: {variation.id}] Arka plansız resim zaten mevcut, atlanıyor.")
            return True

        print(f"✂️ [ID: {variation.id}] {model_id} ile Arka Plan siliniyor...")
        ai_client = UniversalAIClient(api_key=api_key, platform=config["platform"])

        try:
            # İşleniyor statüsüne çek
            variation.status = DesignVariation.Status.PROCESSING
            variation.save(update_fields=['status'])

            # Hangi resim verilecek? (Dinamik sıra için upscaled varsa onu, yoksa orijinali kullan)
            current_path = variation.upscaled_image.path if (variation.upscaled_image and variation.upscaled_image.name) else variation.generated_image.path

            bg_url = ai_client.execute(model_id=model_id, file_path=current_path)

            if isinstance(bg_url, list): bg_url = bg_url[0]

            if not bg_url or not str(bg_url).startswith("http"):
                logger.warning(f"⚠️ BG Remover URL alınamadı: {bg_url}")
                return False

            content_file = FileService.download_image_as_contentfile(bg_url)
            if content_file:
                file_name = f"nobg_{variation.product.id}_{variation.id}.png"
                # Veritabanına kaydet
                variation.no_bg_image.save(file_name, content_file, save=True)
                print(f"🎉 BAŞARILI: [ID: {variation.id}] BG Removal Tamam.")
                return True
            return False

        except Exception as e:
            logger.error(f"❌ BG Remover Hatası (ID: {variation.id}): {e}")
            return False