from apps.accounts.models import UserSettings # Yeni modüler model yolu
import logging

logger = logging.getLogger(__name__)

class ConfigService:
    """
    Kullanıcının AI konfigürasyonlarını (API Key, Pipeline ayarları) 
    Session veya DB'den güvenle çeken ortak servis.
    """
    @staticmethod
    def get_ai_config(user, session_data=None):
        try:
            # 1. Önce Session'da var mı diye bak (Hızlı)
            config_data = session_data.get('ai_config') if session_data else None
            
            # 2. Session'da yoksa DB'den çek (Yavaş ama garanti)
            if not config_data:
                user_settings = UserSettings.objects.get(user=user)
                config_data = {
                    "api": {"key": user_settings.replicate_api_key},
                    "pipeline": user_settings.pipeline_config
                }
            
            # 3. Veri bütünlüğünü doğrula
            api_key = config_data.get('api', {}).get('key', '').strip()
            pipeline = config_data.get('pipeline', [])
            
            if not api_key:
                return None, None, "API Key bulunamadı. Lütfen Config sayfasından ayarlarınızı kaydedin."
                
            return api_key, pipeline, None

        except UserSettings.DoesNotExist:
            return None, None, "Kullanıcı ayarları bulunamadı."
        except Exception as e:
            logger.error(f"Config çekme hatası: {str(e)}")
            return None, None, "Ayarlar okunurken sistemsel bir hata oluştu."