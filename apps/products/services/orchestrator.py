import hashlib
from django.conf import settings
from apps.products.models import UploadGroup
from apps.ai.services.generations.image_analysis import VisionAnalysisService
from apps.ai.services.generations.seo import SeoEngineService
from apps.image_processor.services.mockup_processor import MockupEngineService
from apps.image_processor.models import MockupGroup
import os
from apps.common.services.thread_helper import ThreadService
from apps.ai.services.config.system_prompts import DEFAULT_SYSTEM_PROMPTS 

class Pipeline2Orchestrator:
    
    @staticmethod
    def _generate_file_hash(file_obj):
        """Dosyanın içeriğini (pikselleri/byte'ları) okuyarak eşsiz bir MD5 üretir."""
        import hashlib
        hasher = hashlib.md5()
        for chunk in file_obj.chunks():
            hasher.update(chunk)
        file_obj.seek(0) # ÇOK ÖNEMLİ: Dosya imlecini başa sar ki Django boş dosya kaydetmesin
        return hasher.hexdigest()

    @classmethod
    def process_uploads(cls, user, files, group_name):
        """Piksel taraması yaparak sadece benzersiz dosyaları kaydeder."""
        from apps.products.models import ManualUpload
        uploaded_items = []
        new_files_to_save = []
        
        for file in files:
            file_hash = cls._generate_file_hash(file)
            # Sadece isme değil, DİREKT olarak piksellerin hash koduna bak!
            existing = ManualUpload.objects.filter(group__user=user, file_hash=file_hash).first()
            
            if existing:
                print(f"♻️ PIXEL CACHE: '{file.name}' içeriği zaten DB'de var. Yeniden yüklenmedi.")
                uploaded_items.append({
                    "id": existing.id, "url": existing.image.url, 
                    "name": existing.original_filename, "cached": True
                })
            else:
                new_files_to_save.append({'file': file, 'hash': file_hash})

        if new_files_to_save:
            from apps.products.models import UploadGroup, ManualUpload
            upload_group = UploadGroup.objects.create(user=user, name=group_name)
            for item in new_files_to_save:
                new_up = ManualUpload.objects.create(
                    group=upload_group, image=item['file'],
                    original_filename=item['file'].name, file_hash=item['hash']
                )
                uploaded_items.append({
                    "id": new_up.id, "url": new_up.image.url, 
                    "name": new_up.original_filename, "cached": False
                })

        return {"group_id": None, "items": uploaded_items}

    @classmethod
    def process_batch_items(cls, user, api_key, upload_ids, seo_targets, do_mockup, mockup_mapping, action_type):
        
        from apps.products.models import ManualUpload
        results = []
        uploads = ManualUpload.objects.filter(id__in=upload_ids, group__user=user)
        
        should_recreate_seo = action_type in ['force_seo', 'force_all']
        should_recreate_mockup = action_type in ['force_mockup', 'force_all']

        # 1. MOCKUP İŞLEMLERİ (Pipeline 1 Mantığına Birebir Uyumlu)
        mockup_grouped_urls = {} # Format: { upload_id: { group_id: [url1, url2] } }
        
        if do_mockup and mockup_mapping:
            try:
                from apps.image_processor.models import MockupItem
                tasks = []
                
                # mapping formatı: { "upload_id": ["group_id_1", "group_id_2"] }
                for u_id_str, group_ids in mockup_mapping.items():
                    u_id = int(u_id_str)
                    
                    # 🚀 ÇÖZÜM BURADA: Pipeline 1'deki gibi grubun içindeki koordinatları (MockupItem) buluyoruz
                    items = MockupItem.objects.filter(
                        group__id__in=group_ids, 
                        placement_data__isnull=False
                    ).exclude(placement_data={})
                    
                    for item in items:
                        tasks.append({
                            "upload_id": u_id,
                            "item_id": item.id,
                            "group_id": item.group_id, # Gruplama için saklıyoruz
                            "force": should_recreate_mockup
                        })
                
                def _run_mockup(task):
                    try:
                        res = MockupEngineService.apply_upload_to_mockup(task)
                        if not isinstance(res, dict):
                            res = {"success": False, "error": "Geçersiz yanıt."}
                        res['upload_id'] = task['upload_id']
                        res['group_id'] = task['group_id'] # Geriye Grup ID'sini de dönüyoruz
                        return res
                    except Exception as e:
                        return {"success": False, "error": str(e), "upload_id": task['upload_id']}

                print(f"🏭 Pipeline 2: Toplam {len(tasks)} özel mockup koordinatı işleniyor...")
                mockup_results = ThreadService.run_parallel(_run_mockup, tasks, max_workers=5)
                
                
                # Sonuçları Pipeline 1 formatında haritalandır!
                for res in mockup_results:
                    if not res: continue
                    uid = res.get('upload_id')
                    gid = str(res.get('group_id'))
                    
                    if uid not in mockup_grouped_urls:
                        mockup_grouped_urls[uid] = {}
                        
                    if res.get('success'):
                        if gid not in mockup_grouped_urls[uid]:
                            mockup_grouped_urls[uid][gid] = []
                            
                        # ARTIK DİREKT SERVİSTEN GELEN URL'Yİ KULLANIYORUZ
                        if 'url' in res:
                            mockup_grouped_urls[uid][gid].append(res['url'])
                    else:
                        print(f"❌ MOCKUP HATASI (Upload ID: {uid}): {res.get('error')}")
                        
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"⚠️ Toplu Mockup Motoru Hatası: {e}")

        # --- SEO PROMPTLARINI HAZIRLA ---
        title_prompt = DEFAULT_SYSTEM_PROMPTS.get("gpt-4o_title", "")
        tags_prompt = DEFAULT_SYSTEM_PROMPTS.get("gpt-4o_tag", "")

        # 2. VISION AI VE SEO İŞLEMLERİ (PARALEL YAPI)
        base_results = {}
        seo_tasks = []

        # Önce tüm tasarımların temel dönüş şablonunu oluştur ve SEO görevlerini topla
        for upload in uploads:
            target = seo_targets.get(str(upload.id), 'both')
            
            item_result = {
                "id": upload.id, 
                "status": "success", 
                "seo": None, 
                "mockups": mockup_grouped_urls.get(upload.id, {})
            }

            # DB'de varsa direkt getir (Cache)
            existing_seo = None
            if hasattr(upload, 'seo') and upload.seo and upload.seo.generated_title:
                existing_seo = {"title": upload.seo.generated_title, "tags": upload.seo.generated_tags}
                item_result["seo"] = existing_seo

            # DB'de yoksa ve "Pasif" seçilmediyse görev (Task) listesine ekle
            if not existing_seo or should_recreate_seo:
                if target != 'none':
                    seo_tasks.append({"upload": upload, "target": target})

            base_results[upload.id] = item_result

        # Eğer üretilecek SEO varsa ThreadService ile PARALEL çalıştır
        if seo_tasks:
            def _run_seo(task):
                up = task['upload']
                tgt = task['target']
                try:
                    vision_res = VisionAnalysisService.analyze_design(
                        manual_upload=up, api_key=api_key, force_recreate=should_recreate_seo
                    )
                    if vision_res.get("success"):
                        seo_res = SeoEngineService.generate_seo_for_design(
                            model_id="gpt-4o", api_key=api_key, title_prompt=title_prompt, 
                            tags_prompt=tags_prompt, manual_upload=up, target=tgt
                        )
                        if seo_res.get("success"):
                            return {"success": True, "upload_id": up.id, "seo": {"title": seo_res.get("title"), "tags": seo_res.get("tags")}}
                        return {"success": False, "upload_id": up.id, "error": seo_res.get("error")}
                    return {"success": False, "upload_id": up.id, "error": vision_res.get("error")}
                except Exception as e:
                    return {"success": False, "upload_id": up.id, "error": str(e)}

            print(f"🔍 Pipeline 2: Toplam {len(seo_tasks)} SEO/Vision işlemi paralel başlatılıyor...")
            seo_results_parallel = ThreadService.run_parallel(_run_seo, seo_tasks, max_workers=5)

            # Paralel sonuçları ana listeye eşle
            for res in seo_results_parallel:
                if not res: continue
                uid = res.get('upload_id')
                if res.get('success'):
                    base_results[uid]["seo"] = res.get("seo")
                else:
                    base_results[uid]["seo_error"] = res.get("error")

        # Sözlüğü listeye çevirip dön
        results = list(base_results.values())
        return results