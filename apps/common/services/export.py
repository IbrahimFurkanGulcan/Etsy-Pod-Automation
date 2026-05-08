import os
from django.conf import settings
from django.utils.text import slugify

# Önceden yazdığın modüler servisler
from apps.common.services.zip_helper import ZipExportService
from apps.common.services.db_helpers import DatabaseService
from apps.common.services.thread_helper import ThreadService

# Modeller
from apps.etsy.models import EtsyProduct
from apps.products.models import ManualUpload
from apps.ai.models import DesignVariation
from apps.image_processor.models import MockupResult

class ProjectExportService:
    
    @classmethod
    def export_pipeline1_rows(cls, user, design_ids):
        """Pipeline 1: Seçilen her tasarımı (row) kendi klasöründe (Resim, Mockup, SEO) toplar."""
        if not design_ids:
            return {"success": False, "error": "Dışa aktarılacak tasarım seçilmedi."}

        # ZIP nesnesini RAM'de başlat
        zip_service = ZipExportService(filename_prefix="Etsy_Pipeline1_Export")

        # Tasarımları veritabanından çek (Güvenlik için kullanıcı kontrolüyle)
        variations = DesignVariation.objects.filter(id__in=design_ids, product__user=user)

        for var in variations:
            # 1. Klasör adını belirle (Design_ID_Title)
            folder_name = f"Design_{var.id}"
            if hasattr(var, 'seo') and var.seo.generated_title:
                safe_title = slugify(var.seo.generated_title)[:30]
                folder_name += f"_{safe_title}"

            # 2. Ana Tasarımı (PNG) Ekle
            # Öncelik transparan (no_bg) olanda, yoksa üretilen resmi al
            design_file = var.no_bg_image if var.no_bg_image else var.generated_image
            if design_file and os.path.exists(design_file.path):
                ext = os.path.splitext(design_file.name)[1]
                zip_service.add_file_from_disk(f"{folder_name}/Primary_Design{ext}", design_file.path)

            # 3. SEO Dosyasını (TXT) Klasör İçine Ekle
            seo_content = f"--- SEO DATA FOR DESIGN {var.id} ---\n\n"
            if hasattr(var, 'seo'):
                seo_content += f"TITLE:\n{var.seo.generated_title}\n\n"
                seo_content += f"TAGS:\n{var.seo.generated_tags}\n\n"
            seo_content += f"Original Product: {var.product.url}\n"
            zip_service.add_text_file(f"{folder_name}/SEO_Details.txt", seo_content)

            # 4. Bu Tasarıma Ait Üretilmiş Mockupları Bul ve Klasöre Ekle
            # MockupResult modelinizdeki klasörleme yapısına göre ayarlanmalıdır
            # Genel mantık: O tasarıma ait tüm sonuç dosyalarını bulup ekliyoruz
            mockup_results = MockupResult.objects.filter(design_variation=var)
            
            for idx, m_res in enumerate(mockup_results):
                if m_res.result_image and os.path.exists(m_res.result_image.path):
                    m_ext = os.path.splitext(m_res.result_image.name)[1]
                    zip_service.add_file_from_disk(
                        f"{folder_name}/Mockups/Mockup_{idx+1}{m_ext}", 
                        m_res.result_image.path
                    )

        return {"success": True, "response": zip_service.get_http_response()}

    @staticmethod
    def _read_file_to_ram(task):
        """
        Thread içinde çalışacak fonksiyon.
        Sadece dosyayı diskten (veya buluttan) RAM'e okur, ZIP'e yazmaz!
        """
        try:
            with open(task["physical_path"], "rb") as f:
                return {
                    "zip_path": task["zip_path"],
                    "file_bytes": f.read()
                }
        except Exception as e:
            print(f"⚠️ Dosya okuma hatası ({task['physical_path']}): {e}")
            return None

    @classmethod
    def export_pipeline2_rows(cls, user, upload_ids):
        """Pipeline 2: ThreadService ile hızlandırılmış dışa aktarım."""
        if not upload_ids:
            return {"success": False, "error": "İndirilecek tasarım seçilmedi."}

        uploads = ManualUpload.objects.filter(id__in=upload_ids, group__user=user)
        if not uploads.exists():
            return {"success": False, "error": "Seçilen tasarımlar bulunamadı veya yetkisiz erişim."}

        zip_service = ZipExportService(filename_prefix="Etsy_Batch_Export")
        
        # 1. OKUNACAK DOSYALARIN LİSTESİNİ (GÖREVLERİ) HAZIRLA
        read_tasks = []
        
        for upload in uploads:
            folder_name = f"Design_{upload.id}"
            if hasattr(upload, 'seo') and upload.seo and upload.seo.generated_title:
                safe_title = slugify(upload.seo.generated_title)[:50]
                folder_name = safe_title if safe_title else folder_name

            # A. Orijinal Tasarım Görevi
            if upload.image and hasattr(upload.image, 'path'):
                ext = os.path.splitext(upload.image.name)[1]
                read_tasks.append({
                    "physical_path": upload.image.path, 
                    "zip_path": f"{folder_name}/Original_Design{ext}"
                })

            # B. SEO Metnini Doğrudan ZIP'e Ekle (Metin olduğu için I/O beklemesi yapmaz, thread'e gerek yok)
            seo_content = f"--- AI DESIGN ANALYSIS & SEO ---\n\n"
            vision_analysis = getattr(upload, 'vision_analysis', getattr(upload.seo, 'vision_analysis', None) if hasattr(upload, 'seo') else None)
            if vision_analysis:
                seo_content += f"VISION AI ANALYSIS:\n{vision_analysis}\n\n"
            if hasattr(upload, 'seo') and upload.seo:
                seo_content += f"TARGET TITLE:\n{upload.seo.generated_title}\n\n"
                seo_content += f"TARGET TAGS:\n{upload.seo.generated_tags}\n\n"
            
            zip_service.add_text_file(f"{folder_name}/SEO_Data.txt", seo_content)

            mockup_results = MockupResult.objects.filter(manual_upload=upload)
            
            for idx, m_res in enumerate(mockup_results):
                if m_res.result_image and hasattr(m_res.result_image, 'path') and os.path.exists(m_res.result_image.path):
                    m_ext = os.path.splitext(m_res.result_image.name)[1]
                    read_tasks.append({
                        "physical_path": m_res.result_image.path,
                        "zip_path": f"{folder_name}/Mockups/Mockup_{idx+1}{m_ext}"
                    })

        # 2. DOSYALARI PARALEL (THREAD) OLARAK OKU
        # Diskten (veya S3'ten) tüm dosyaları aynı anda RAM'e çekiyoruz.
        print(f"⚡ {len(read_tasks)} adet dosya ThreadService ile RAM'e yükleniyor...")
        read_results = ThreadService.run_parallel(cls._read_file_to_ram, read_tasks, max_workers=5)

        # 3. RAM'DEKİ VERİLERİ ANA THREAD'DE (GÜVENLİCE) ZIP'E YAZ
        # zipfile yazma işlemi thread-safe olmadığı için bu kısmı sıralı (sequential) yapıyoruz.
        for result in read_results:
            # zip_service içindeki zip_file nesnesine writestr ile byte verisini doğrudan basıyoruz
            zip_service.zip_file.writestr(result["zip_path"], result["file_bytes"])

        return {"success": True, "response": zip_service.get_http_response()}