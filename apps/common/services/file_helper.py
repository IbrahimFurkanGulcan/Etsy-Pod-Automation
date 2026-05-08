import requests
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import logging

logger = logging.getLogger(__name__)

class FileService:
    """
    Dosya indirme, Base64 çözme ve dosya kaydetme gibi ortak işlemler.
    """
    @staticmethod
    def download_image_as_contentfile(url):
        """
        Verilen URL'den resmi indirir ve Django modeline kaydedilebilir
        bir ContentFile objesi olarak döndürür. Başarısızsa None döner.
        """
        if not url or not str(url).startswith("http"):
            return None

        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                # ContentFile, Django'nun FileField'ına doğrudan kaydedilebilir.
                return ContentFile(response.content)
            else:
                logger.warning(f"Resim indirilemedi. HTTP Status: {response.status_code} - URL: {url}")
                return None
        except Exception as e:
            logger.error(f"Resim indirme hatası: {str(e)}")
            return None

    @staticmethod
    def download_image_as_pil(url):
        """
        Verilen URL'den resmi indirir ve kırpma işlemleri için PIL Image objesi döner.
        """
        if not url or not str(url).startswith("http"):
            return None
            
        print(f"📥 Resim indiriliyor: {url}")
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert("RGB")
            return image
        except Exception as e:
            logger.error(f"❌ Resim indirme hatası (PIL): {str(e)}")
            return None