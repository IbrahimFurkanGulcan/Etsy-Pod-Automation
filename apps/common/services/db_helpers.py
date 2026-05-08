from django.core.exceptions import ObjectDoesNotExist
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    """
    Tüm uygulamaların kullanabileceği jenerik veritabanı yardımcı servisi.
    """

    @staticmethod
    def get_object_or_none(model, **kwargs):
        """
        Verilen model ve filtrelere göre objeyi arar.
        Bulursa objeyi, bulamazsa None döndürür.
        Kullanım: DatabaseService.get_object_or_none(EtsyProduct, url=my_url)
        """
        try:
            return model.objects.get(**kwargs)
        except ObjectDoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Veritabanı okuma hatası ({model.__name__}): {str(e)}")
            return None

    @staticmethod
    def find_first_by_filter(model, **kwargs):
        """
        Geniş filtrelemeler (örn: __contains, __in) için ilk eşleşen kaydı getirir.
        Bulamazsa None döner.
        Kullanım: DatabaseService.find_first_by_filter(EtsyProduct, url__contains="12345")
        """
        try:
            return model.objects.filter(**kwargs).first()
        except Exception as e:
            logger.error(f"DB Filtreleme Hatası ({model.__name__}): {str(e)}")
            return None

    @staticmethod
    def exists(model, **kwargs):
        """
        Verilen filtrelere uyan bir kaydın olup olmadığını Boolean (True/False) döndürür.
        Kullanım: if DatabaseService.exists(ManualUpload, id=5): ...
        """
        return model.objects.filter(**kwargs).exists()

    @staticmethod
    def get_or_create_with_log(model, defaults=None, **kwargs):
        """
        Kaydı arar, yoksa oluşturur ve işlemi loglar.
        (Özellikle AI Varyasyonları ve Mockup Template'leri oluştururken faydalı)
        """
        try:
            obj, created = model.objects.get_or_create(defaults=defaults, **kwargs)
            if created:
                logger.info(f"Yeni kayıt oluşturuldu: {model.__name__} (ID: {obj.id})")
            return obj, created
        except Exception as e:
            logger.error(f"Kayıt oluşturma hatası ({model.__name__}): {str(e)}")
            return None, False

    @staticmethod
    def update_or_create_with_log(model, defaults=None, **kwargs):
        """
        Kayıt varsa günceller (update), yoksa yeni oluşturur (create).
        (Scraper'dan gelen güncel verileri veya SEO çıktılarını kaydetmek için idealdir).
        """
        try:
            obj, created = model.objects.update_or_create(defaults=defaults, **kwargs)
            action = "oluşturuldu" if created else "güncellendi"
            logger.info(f"Kayıt {action}: {model.__name__} (ID: {obj.id})")
            return obj, created
        except Exception as e:
            logger.error(f"Kayıt güncelleme/oluşturma hatası ({model.__name__}): {str(e)}")
            return None, False

    @staticmethod
    def delete_object(model, **kwargs):
        """
        Verilen filtrelere uyan kaydı (veya kayıtları) güvenli bir şekilde siler.
        (Örn: Kullanıcı bir Mockup Template'ini veya Manuel Tasarımı sildiğinde).
        """
        try:
            objects_to_delete = model.objects.filter(**kwargs)
            if objects_to_delete.exists():
                count, _ = objects_to_delete.delete()
                logger.info(f"{count} adet {model.__name__} kaydı silindi.")
                return True
            return False
        except Exception as e:
            logger.error(f"Kayıt silme hatası ({model.__name__}): {str(e)}")
            return False