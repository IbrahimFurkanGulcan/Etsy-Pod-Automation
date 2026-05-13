import json
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import traceback

from apps.etsy.models import EtsyProduct 
from apps.accounts.models import PipelineConfig, ApiCredential 
from apps.common.services.db_helpers import DatabaseService 
from apps.common.services.encryption import decrypt_text 
from apps.common.services.file_helper import FileService 
from apps.common.services.thread_helper import ThreadService
from apps.ai.services.generations.designs import DesignGeneratorService 
from apps.ai.services.detect import DetectService 
from apps.image_processor.services.crop import CropService 
from .models import DesignVariation, SeoOptimization
from apps.ai.services.generations.processor import ImageProcessingCoordinator
from apps.ai.services.generations.seo import SeoEngineService
from apps.ai.services.config.system_prompts import DEFAULT_SYSTEM_PROMPTS
from apps.ai.services.config.user_prompts import DEFAULT_USER_PROMPTS


@csrf_exempt
@login_required(login_url='/accounts/login/')
def generate_designs_action(request):
    """
    Kullanıcının Accounts altındaki Config ayarlarını okur.
    Seçilen ürünleri önce DINO ile kırpar, ardından aktif edilen 
    tüm modellere paralel (ThreadService) olarak gönderir.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            product_ids = data.get('product_ids', [])
            
            # 1. API Key ve Config Ayarlarını Güvenle Çek
            creds = DatabaseService.get_object_or_none(ApiCredential, user=request.user)
            config = DatabaseService.get_object_or_none(PipelineConfig, user=request.user)
            
            if not creds or not creds.replicate_key:
                return JsonResponse({"status": "error", "message": "API Anahtarı bulunamadı. Lütfen Ayarlar sayfasından kaydedin."}, status=400)
            
            if not config or not config.enable_generation:
                return JsonResponse({"status": "error", "message": "Üretim (Generation) ayarları kapalı veya yapılandırılmamış."}, status=400)

            # Şifreli anahtarı çözüyoruz
            api_key = decrypt_text(creds.replicate_key)

            # 2. Hangi modeller aktif? (Veritabanındaki Config'den Dinamik Liste)
            active_models = []
            if getattr(config, 'gen_model_1_enabled', False):
                active_models.append({"model": config.gen_model_1_id, "prompt": config.gen_model_1_prompt})
            if getattr(config, 'gen_model_2_enabled', False):
                active_models.append({"model": config.gen_model_2_id, "prompt": config.gen_model_2_prompt})
            if getattr(config, 'gen_model_3_enabled', False):
                active_models.append({"model": config.gen_model_3_id, "prompt": config.gen_model_3_prompt})

            if not active_models:
                return JsonResponse({"status": "error", "message": "Ayarlar sayfasında aktif edilmiş hiçbir AI modeli bulunamadı."}, status=400)

            all_results = {}

            for p_id in product_ids:
                product = DatabaseService.get_object_or_none(EtsyProduct, id=p_id, user=request.user)
                if not product:
                    continue

                p_results = []
                models_to_trigger = []

                # --- ADIM 1: DB KONTROLÜ (CACHE SİSTEMİ) ---
                for m in active_models:
                    model_id = m["model"]
                    existing_variation = DatabaseService.get_object_or_none(
                        DesignVariation,
                        product=product,
                        ai_model_name=model_id,
                        status="completed"
                    )
                    
                    if existing_variation and existing_variation.generated_image:
                        # KRİTİK EKLENTİ: İşlenmiş mi? Şeffaf resmi var mı?
                        has_nobg = bool(existing_variation.no_bg_image)
                        
                        p_results.append({
                            "id": existing_variation.id,
                            # Ekrana eğer varsa şeffaf olanı, yoksa normali bas
                            "src": existing_variation.no_bg_image.url if has_nobg else existing_variation.generated_image.url,
                            "model": model_id,
                            "cached": True,
                            "is_processed": has_nobg, # JS buraya bakacak
                            "no_bg_src": existing_variation.no_bg_image.url if has_nobg else None
                        })
                    else:
                        models_to_trigger.append(m)


                # --- ADIM 2: SADECE EKSİKLER İÇİN AI ÇALIŞTIR ---
                if models_to_trigger:
                    
                    # AI'ya göndereceğimiz için mecburen kırpma (Crop) yapmalıyız
                    if not product.cropped_image:
                        img_pil = FileService.download_image_as_pil(product.image_url)
                        if img_pil:
                            w, h = img_pil.size
                            crop_box = DetectService.detect_design_coordinates(product.image_url, api_key, w, h)
                            if crop_box:
                                CropService.crop_and_save_product_design(product.id, crop_box)
                                product.refresh_from_db()

                    crop_path = product.cropped_image.path if product.cropped_image else product.image_url

                    new_designs = DesignGeneratorService.generate_multiple_designs_parallel(product.id, 
                                                                                            models_to_trigger, 
                                                                                            crop_path, 
                                                                                            api_key
                    )

                    for d in new_designs:
                        if d and d.generated_image:
                            has_nobg = bool(d.no_bg_image)
                            p_results.append({
                                "id": d.id, 
                                "src": d.no_bg_image.url if has_nobg else d.generated_image.url, 
                                "model": d.ai_model_name,
                                "cached": False,
                                "is_processed": has_nobg,
                                "no_bg_src": d.no_bg_image.url if has_nobg else None
                            })

                    # Yeni üretilenleri sonuç listesine ekle
                    for d in new_designs:
                        if d and d.generated_image:
                            p_results.append({
                                "id": d.id, 
                                "src": d.generated_image.url, 
                                "model": d.ai_model_name,
                                "cached": False
                            })

                # Ürünün tüm sonuçlarını (DB + Yeni) paketle
                all_results[p_id] = p_results

            return JsonResponse({"status": "success", "data": all_results})

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
            
    return JsonResponse({"status": "error", "message": "Geçersiz metod."}, status=405)

@csrf_exempt
@login_required(login_url='/accounts/login/')
def process_selected_designs_action(request):
    """Kullanıcının seçtiği AI görsellerini işler (Upscale & BG Removal)."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            selected_ids = data.get('selected_ids', [])
            process_order = data.get('process_order', 'upscale_first') # Varsayılan: Önce büyüt
            
            if not selected_ids:
                return JsonResponse({"status": "error", "message": "İşlenecek görsel seçilmedi."}, status=400)

            # API Key ve Ayarları DB'den çek
            creds = DatabaseService.get_object_or_none(ApiCredential, user=request.user)
            config = DatabaseService.get_object_or_none(PipelineConfig, user=request.user)

            if not creds or not creds.replicate_key:
                return JsonResponse({"status": "error", "message": "API Anahtarı eksik."}, status=400)

            api_key = decrypt_text(creds.replicate_key)

            # Koordinatörü çalıştır (DB Cache mekanizmaları otomatik devreye girecek)
            processed_variations = ImageProcessingCoordinator.run_batch(
                variation_ids=selected_ids,
                process_order=process_order,
                api_key=api_key,
                config=config
            )

            # Ekrana basmak için başarılı sonuçları dön
            results = []
            for v in processed_variations:
                if v:
                    # En son oluşan nihai görseli (no_bg veya upscaled) UI'a dönüyoruz
                    final_image_url = v.no_bg_image.url if v.no_bg_image else (v.upscaled_image.url if v.upscaled_image else v.generated_image.url)
                    results.append({
                        "id": v.id,
                        "src": final_image_url,
                        "status": "İşlendi"
                    })

            return JsonResponse({"status": "success", "images": results})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Geçersiz metod."}, status=405)




@csrf_exempt
@login_required(login_url='/accounts/login/')
def generate_seo_batch_api(request):
    print("\n" + "="*50)
    print("🚀 [DEBUG] SEO BATCH API TETİKLENDİ!")
    print("="*50 + "\n")
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            tasks_data = data.get('tasks', [])
            niche = data.get('niche', 'Graphic T-Shirt')
            force_recreate = data.get('force_recreate', False) 

            if not tasks_data:
                return JsonResponse({"status": "error", "message": "İşlenecek görev bulunamadı."}, status=400)

            # API Key Ayarlarını Al
            user_settings = ApiCredential.objects.get(user=request.user)
            api_key = decrypt_text(user_settings.replicate_key)
            model_id = "gpt-4o"
            
            # Sistem ve Kullanıcı Promptları
            title_prompt = DEFAULT_SYSTEM_PROMPTS.get("gpt-4o_title", "")
            tags_prompt = DEFAULT_SYSTEM_PROMPTS.get("gpt-4o_tag", "")
            user_prompt_template = DEFAULT_USER_PROMPTS.get("gpt-4o", "")

            response_data = {}
            tasks_to_run = []

            for t in tasks_data:
                # 1. ADIM: Frontend'den gelen ID, DesignVariation ID'sidir. Onu buluyoruz.
                try:
                    variation = DesignVariation.objects.get(id=t['design_id'], product__user=request.user)
                except DesignVariation.DoesNotExist:
                    print(f"⚠️ [HATA] ID'si {t['design_id']} olan DesignVariation bulunamadı!")
                    continue
                
                # 2. ADIM (KÖPRÜ): Varyasyon üzerinden ORİJİNAL ETSY ÜRÜNÜNE geçiş yapıyoruz!
                # İşte senin aradığın orijinal Scrape verileri burada (EtsyProduct)
                product = variation.product 
                d_id = str(variation.id)

                # 3. ADIM: CACHE KONTROLÜ (SEO tablosunda zaten üretilmiş mi?)
                if not force_recreate and hasattr(variation, 'seo') and variation.seo:
                    seo = variation.seo
                    if seo.generated_title or seo.generated_tags:
                        print(f"⚡ CACHE: [Tasarım ID: {d_id}] SEO DB'den hızlıca getirildi.")
                        response_data[d_id] = {
                            "title": seo.generated_title,
                            "tags": seo.generated_tags
                        }
                        continue 

                # 4. ADIM: Prompt'u Orijinal Etsy Ürünü (product) verileriyle doldur
                # product.title ve product.tags doğrudan EtsyProduct tablosundan gelir!
                formatted_user_prompt = user_prompt_template.format(
                    title=product.title, 
                    tags=product.tags,
                    niche=niche
                )

                tasks_to_run.append({
                    "design_variation": variation,
                    "target": t['target'],
                    "model_id": model_id,
                    "api_key": api_key,
                    "title_prompt": title_prompt,
                    "tags_prompt": tags_prompt,
                    "user_prompt": formatted_user_prompt,
                    "niche": niche
                })

            if tasks_to_run:
                print(f"🏭 Toplam {len(tasks_to_run)} eksik SEO görevi AI ile üretiliyor...")
                
                def process_seo(task):
                    return SeoEngineService.generate_seo_for_design(
                        model_id=task['model_id'],
                        api_key=task['api_key'],
                        title_prompt=task['title_prompt'],
                        tags_prompt=task['tags_prompt'],
                        user_prompt=task['user_prompt'],
                        niche=task['niche'],
                        design_variation=task['design_variation'],
                        target=task['target']
                    )

                results = ThreadService.run_parallel(process_seo, tasks_to_run, max_workers=5)

                for res in results:
                    if res and res.get('success'):
                        d_id = str(res.get('design_id'))
                        response_data[d_id] = {
                            "title": res.get("title", ""),
                            "tags": res.get("tags", "")
                        }

            return JsonResponse({"status": "success", "results": response_data})
            
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)