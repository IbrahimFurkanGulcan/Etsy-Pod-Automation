import base64
import logging
from django.core.files.base import ContentFile
from apps.common.services.db_helpers import DatabaseService
from django.utils.text import slugify

from apps.image_processor.models import MockupGroup, MockupItem 

logger = logging.getLogger(__name__)

class MockupTemplateService:
    """
    Kullanıcının yüklediği mockup şablonlarını (Base64) ve koordinatlarını 
    veritabanına kaydeder veya günceller.
    """
    
    @staticmethod
    def save_collection(user, mockups_data, group_name=None, group_id=None):
        saved_count = 0
        
        # 1. Grup İşlemleri (DatabaseService Kullanarak)
        if group_id:
            group = DatabaseService.get_object_or_none(MockupGroup, id=group_id, user=user)
            if not group:
                raise ValueError("Güncellenmek istenen grup bulunamadı veya yetkiniz yok.")
            
            if group_name and group.name != group_name:
                group.name = group_name
                group.save(update_fields=['name'])
        else:
            # Yeni grup oluştur
            final_name = group_name if group_name else "Yeni Koleksiyon"
            group = MockupGroup.objects.create(user=user, name=final_name)
            logger.info(f"Yeni MockupGroup oluşturuldu: {group.name} (ID: {group.id})")

        # 2. Şablon (Item) İşlemleri
        for mockup in mockups_data:
            mockup_id_str = str(mockup.get('id'))
            
            # DURUM A: Mevcut Şablonun Koordinatlarını Güncelle
            if mockup_id_str.startswith('db_'):
                real_id = mockup_id_str.split('_')[1]
                item = DatabaseService.get_object_or_none(MockupItem, id=real_id, group__user=user)
                
                if item:
                    item.name = mockup['name']
                    item.placement_data = mockup['coordinates']
                    item.save(update_fields=['name', 'placement_data'])
                    saved_count += 1
                    
            # DURUM B: Yeni Yüklenen Şablonu (Base64) Kaydet
            elif mockup_id_str.startswith('mockup_'):
                try:
                    format, imgstr = mockup['url'].split(';base64,') 
                    ext = format.split('/')[-1]
                    file_name = f"{mockup['name'].replace(' ', '_')}_{user.id}.{ext}"
                    img_data = ContentFile(base64.b64decode(imgstr), name=file_name)

                    MockupItem.objects.create(
                        group=group,
                        name=mockup['name'],
                        mockup_image=img_data,
                        placement_data=mockup['coordinates']
                    )
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Şablon Base64 çözme hatası: {e}")

        return {"group_id": group.id, "saved_count": saved_count}