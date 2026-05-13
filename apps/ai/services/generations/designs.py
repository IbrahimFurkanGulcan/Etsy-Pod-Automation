import logging
from apps.ai.services.client import UniversalAIClient
from apps.common.services.file_helper import FileService
from apps.common.services.thread_helper import ThreadService
from apps.ai.models import DesignVariation

# Konfigürasyon dosyalarını içe aktarıyoruz
from apps.ai.services.config.model_registry import ModelRegistry
from apps.ai.services.config.user_prompts import DEFAULT_USER_PROMPTS

logger = logging.getLogger(__name__)

class DesignGeneratorService:
    """
    Tasarım varyasyonlarını merkezi konfigürasyona göre üreten,
    paralel çalışan ve sonuçları DB'ye mühürleyen servis.
    """

    @staticmethod
    def generate_single_design(task_info):
        """
        Tek bir AI modelini merkezi şemaya göre çalıştırır.
        task_info: { 'product': obj, 'model_id': str, 'prompt': str, 'crop_path': str, 'api_key': str }
        """
        model_id = task_info['model_id']
        product = task_info['product']
        user_prompt = task_info.get('prompt')
        crop_path = task_info['crop_path']
        api_key = task_info['api_key']

        # 1. Model ayarlarını Registry'den çek
        config = ModelRegistry.get(model_id)
        if not config:
            logger.error(f"❌ Model '{model_id}' registry içinde bulunamadı!")
            return None

        # 2. Eğer özel prompt gelmediyse varsayılan prompt'u kütüphaneden çek
        if not user_prompt or not user_prompt.strip():
            user_prompt = DEFAULT_USER_PROMPTS.get(model_id, "")
            # Eğer ürün başlığı prompt içinde kullanılmak isteniyorsa ({title} etiketi)
            if "{title}" in user_prompt:
                user_prompt = user_prompt.format(title=product.title)

        print(f"🎨 [{model_id}] Üretim başlatılıyor...")
        ai_client = UniversalAIClient(api_key=api_key, platform=config["platform"])

        try:
            # 3. Evrensel Motoru Çalıştır (execute metodu artık şemaya göre her şeyi halleder)
            image_url = ai_client.execute(
                model_id=model_id, 
                prompt=user_prompt, 
                file_path=crop_path
            )

            # API bazen liste döndürebilir (Seedream gibi), ilk URL'yi al
            if isinstance(image_url, list) and len(image_url) > 0:
                image_url = image_url[0]

            if not image_url or not str(image_url).startswith("http"):
                logger.warning(f"⚠️ {model_id} için geçerli bir URL dönmedi: {image_url}")
                return None

            # 4. Veritabanında Kaydı Oluştur
            variation = DesignVariation.objects.create(
                product=product,
                ai_model_name=model_id,
                prompt_used=user_prompt,
                status="completed"
            )

            # 5. Resmi İndir ve Kaydet (FileService Kullanarak)
            content_file = FileService.download_image_as_contentfile(image_url)
            
            if content_file:
                file_name = f"{model_id}_{product.id}_{variation.id}.png"
                variation.generated_image.save(file_name, content_file, save=True)
                print(f"✅ BAŞARILI: {model_id} varyasyonu kaydedildi.")
                return variation
            else:
                variation.status = "failed"
                variation.save()
                return None

        except Exception as e:
            logger.error(f"❌ Design Generation Hatası ({model_id}): {e}")
            return None

    @classmethod
    def generate_multiple_designs_parallel(cls, product, models_config, crop_path, api_key):
        """
        Gelen model listesini paralel olarak işler.
        models_config: view'dan gelen seçili modeller listesi.
        """
        tasks = []
        for m_info in models_config:
            tasks.append({
                "product": product,
                "model_id": m_info['model'],
                "prompt": m_info.get('prompt'),
                "crop_path": crop_path,
                "api_key": api_key
            })

        # Ortak ThreadService üzerinden paralel tetikle
        print(f"🔥 {len(tasks)} farklı AI modeli paralel olarak göreve başladı...")
        results = ThreadService.run_parallel(
            target_function=cls.generate_single_design, 
            tasks=tasks, 
            max_workers=3 # Aynı anda 3 API isteği (Replicate limiti için güvenli sınır)
        )
        
        return results