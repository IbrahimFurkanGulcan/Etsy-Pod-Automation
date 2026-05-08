import logging
from apps.ai.models import DesignVariation
from apps.common.services.thread_helper import ThreadService
from apps.ai.services.background_remove import BackgroundRemovalService
from apps.ai.services.upscale import UpscaleService

logger = logging.getLogger(__name__)

class ImageProcessingCoordinator:
    """
    Seçilen varyasyonlar için Arka Plan Silme ve Upscale işlemlerini,
    kullanıcının seçtiği sıralamaya göre paralel olarak yönetir.
    """

    @classmethod
    def process_single(cls, task):
        variation = task['variation']
        api_key = task['api_key']
        config = task['config']
        process_order = task['order']  # 'upscale_first' veya 'bg_first'

        # Modellerin aktiflik durumunu Config'den al
        up_model = config.upscale_model if getattr(config, 'enable_upscale', False) else None
        bg_model = config.bg_removal_model if getattr(config, 'enable_bg_removal', False) else None

        # 1. SENARYO: Önce Büyüt, Sonra Arka Planı Sil
        if process_order == 'upscale_first':
            if up_model:
                UpscaleService.process(variation, up_model, api_key)
            if bg_model:
                BackgroundRemovalService.process(variation, bg_model, api_key)
                
        # 2. SENARYO: Önce Arka Planı Sil, Sonra Büyüt
        else:
            if bg_model:
                BackgroundRemovalService.process(variation, bg_model, api_key)
            if up_model:
                UpscaleService.process(variation, up_model, api_key)

        # İşlem bitince durumu güncelle
        variation.status = DesignVariation.Status.COMPLETED
        variation.save(update_fields=['status'])
        
        return variation

    @classmethod
    def run_batch(cls, variation_ids, process_order, api_key, config):
        # DatabaseService mantığıyla varyasyonları güvenle çek
        variations = DesignVariation.objects.filter(id__in=variation_ids)
        
        tasks = [{
            "variation": v, 
            "api_key": api_key, 
            "order": process_order,
            "config": config
        } for v in variations]

        # Paralel işleme başlat (Maksimum 3 API isteği)
        print(f"⚙️ {len(tasks)} tasarım için işlem ({process_order}) başlatıldı...")
        results = ThreadService.run_parallel(
            target_function=cls.process_single,
            tasks=tasks,
            max_workers=3
        )
        return results