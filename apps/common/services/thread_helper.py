from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

class ThreadService:
    """
    Sistem genelinde paralel (eşzamanlı) işlemleri yöneten ortak servis.
    """
    
    @staticmethod
    def run_parallel(target_function, tasks, max_workers=3):
        """
        Verilen hedef fonksiyonu, görev listesindeki (tasks) her bir eleman için
        paralel olarak çalıştırır.
        """
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Görevleri havuza at
            future_to_task = {executor.submit(target_function, task): task for task in tasks}
            
            # Tamamlananları topla
            for future in as_completed(future_to_task):
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Thread İşlem Hatası: {e}")
                    
        return results