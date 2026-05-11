import json
import traceback, hashlib
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .services.export import ProjectExportService 
from apps.ai.models import DesignVariation
from apps.products.models import ManualUpload, UploadGroup

from apps.accounts.models import ApiCredential, PipelineConfig
from apps.common.services.encryption import decrypt_text
from apps.ai.services.background_remove import BackgroundRemovalService


@csrf_exempt
@login_required(login_url='/accounts/login/')
def export_pipeline1_action(request):
    """Pipeline 1 için toplu indirme isteğini karşılar."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            design_ids = data.get('design_ids', [])
            
            if not design_ids:
                return JsonResponse({"status": "error", "message": "İndirilecek veri seçilmedi."}, status=400)

            # Servis üzerinden ZIP oluştur
            export_result = ProjectExportService.export_pipeline1_rows(request.user, design_ids)
            
            if export_result.get("success"):
                return export_result["response"]
            else:
                return JsonResponse({"status": "error", "message": export_result.get("error")}, status=400)

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
            
    return JsonResponse({"status": "error", "message": "POST metodu gereklidir."}, status=405)

@csrf_exempt
@login_required(login_url='/accounts/login/')
def export_pipeline2_action(request):
    """Pipeline 2 için toplu indirme (ZIP) isteğini karşılar."""
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            upload_ids = data.get('upload_ids', [])
            
            if not upload_ids:
                return JsonResponse({"status": "error", "message": "İndirilecek veri seçilmedi."}, status=400)

            # Servis üzerinden ZIP oluştur
            export_result = ProjectExportService.export_pipeline2_rows(request.user, upload_ids)
            
            if export_result.get("success"):
                return export_result["response"]
            else:
                return JsonResponse({"status": "error", "message": export_result.get("error")}, status=400)

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
            
    return JsonResponse({"status": "error", "message": "POST metodu gereklidir."}, status=405)



@login_required(login_url='/accounts/login/')
def get_history_api(request):
    """Pipeline 1 veya 2 için sayfalama destekli geçmiş verisi döner."""
    from apps.ai.models import DesignVariation
    from apps.products.models import ManualUpload
    from django.db.models import Q

    try:
        # Parametreleri al (Varsayılan: İlk 50 kayıt)
        p_type = request.GET.get('type', 'p1') # 'p1' veya 'p2'
        offset = int(request.GET.get('offset', 0))
        limit = int(request.GET.get('limit', 50))
        
        data_list = []
        has_more = False

        if p_type == 'p1':
            qs = DesignVariation.objects.filter(
                Q(seo__isnull=False) | Q(mockup_results__isnull=False),
                product__user=request.user
            ).select_related('product', 'seo').prefetch_related('mockup_results').distinct().order_by('-created_at')
            
            # Sayfalama uygula
            total_count = qs.count()
            current_batch = qs[offset : offset + limit]
            has_more = offset + limit < total_count

            for var in current_batch:
                design_url = var.no_bg_image.url if var.no_bg_image else (var.generated_image.url if var.generated_image else "")
                mockups = [m.result_image.url for m in var.mockup_results.all() if m.result_image]
                source_img = getattr(var.product, 'image_url', "") if var.product else ""
                
                data_list.append({
                    "id": var.id,
                    "source_url": var.product.url if var.product else "",
                    "source_image": source_img,
                    "design_image": design_url,
                    "mockups": mockups,
                    "seo": {"title": var.seo.generated_title, "tags": var.seo.generated_tags} if hasattr(var, 'seo') and var.seo else None,
                })

        else: # p_type == 'p2'
            qs = ManualUpload.objects.filter(
                Q(seo__isnull=False) | Q(mockup_results__isnull=False),
                group__user=request.user
            ).select_related('seo').prefetch_related('mockup_results').distinct().order_by('-created_at')
            
            total_count = qs.count()
            current_batch = qs[offset : offset + limit]
            has_more = offset + limit < total_count

            for up in current_batch:
                mockups = [m.result_image.url for m in up.mockup_results.all() if m.result_image]
                data_list.append({
                    "id": up.id,
                    "original_image": up.image.url if up.image else "",
                    "filename": up.original_filename,
                    "mockups": mockups,
                    "seo": {"title": up.seo.generated_title, "tags": up.seo.generated_tags} if hasattr(up, 'seo') and up.seo else None,
                })

        return JsonResponse({
            "status": "success", 
            "items": data_list, 
            "has_more": has_more, 
            "next_offset": offset + limit
        })

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required(login_url='/accounts/login/')
def get_asset_library_api(request):
    """AI ve Manuel tasarımları birleştirip sayfalama (pagination) ile hızlıca döner."""
    from apps.ai.models import DesignVariation
    from apps.products.models import ManualUpload

    try:
        # Frontenden gelen sayfalama parametreleri
        offset = int(request.GET.get('offset', 0))
        limit = int(request.GET.get('limit', 24)) # Tek seferde maksimum 24 resim
        filter_type = request.GET.get('type', 'all')

        assets = []

        # 1. AI ÜRETIMLERI
        if filter_type in ['all', 'ai']:
            ai_qs = DesignVariation.objects.filter(product__user=request.user).exclude(generated_image='', no_bg_image='').select_related('product')
            # Hızlandırma: Tüm DB'yi tarama, sadece gereken havuzu al
            ai_qs = ai_qs.order_by('-created_at')[:offset+limit]
            
            for var in ai_qs:
                img_url = var.no_bg_image.url if var.no_bg_image else (var.generated_image.url if var.generated_image else "")
                if img_url:
                    assets.append({
                        "id": f"ai_{var.id}",
                        "real_id": var.id,
                        "type": "ai",
                        "url": img_url,
                        "has_bg": not bool(var.no_bg_image),
                        "source": var.product.url if var.product else "Bilinmeyen Kaynak",
                        "timestamp": var.created_at.timestamp()
                    })

        # 2. MANUEL YÜKLEMELER
        if filter_type in ['all', 'manual']:
            manual_qs = ManualUpload.objects.filter(group__user=request.user).order_by('-created_at')[:offset+limit]
            for up in manual_qs:
                if up.image:
                    assets.append({
                        "id": f"manual_{up.id}",
                        "real_id": up.id,
                        "type": "manual",
                        "url": up.image.url,
                        "has_bg": False,
                        "source": up.original_filename,
                        "timestamp": up.created_at.timestamp()
                    })

        # Listeyi en yeniden en eskiye sırala ve sadece talep edilen 'sayfayı' kes
        assets.sort(key=lambda x: x['timestamp'], reverse=True)
        paginated_assets = assets[offset : offset + limit]
        
        # Eğer kesilen parça tam limit kadarsa, muhtemelen daha veri vardır
        has_more = len(paginated_assets) == limit 

        return JsonResponse({
            "status": "success", 
            "assets": paginated_assets, 
            "has_more": has_more
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='/accounts/login/')
def upload_asset_api(request):
    """Kütüphaneden çoklu dosya yükleme işlemini karşılar ve yinelenenleri engeller."""
    import hashlib
    from django.db import IntegrityError
    from apps.products.models import UploadGroup, ManualUpload

    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Geçersiz istek yöntemi."}, status=400)

    files = request.FILES.getlist('files')
    if not files:
        return JsonResponse({"status": "error", "message": "Hiç dosya seçilmedi."}, status=400)

    try:
        # Kütüphane yüklemeleri için varsayılan bir grup bul veya oluştur
        group, _ = UploadGroup.objects.get_or_create(
            user=request.user, 
            name="Kütüphane Yüklemeleri"
        )

        new_assets = []
        for f in files:
            # 1. Dosyanın Hash (MD5) değerini hesapla
            md5 = hashlib.md5()
            for chunk in f.chunks():
                md5.update(chunk)
            file_hash = md5.hexdigest()

            # 2. Veritabanına kaydet (Duplicate kontrolü ile)
            try:
                upload = ManualUpload.objects.create(
                    group=group,
                    image=f,
                    original_filename=f.name,
                    file_hash=file_hash
                )
                
                # Frontend'in beklediği formatta listeye ekle
                new_assets.append({
                    "id": f"manual_{upload.id}",
                    "real_id": upload.id,
                    "type": "manual",
                    "url": upload.image.url,
                    "has_bg": False,
                    "source": upload.original_filename,
                    "timestamp": upload.created_at.timestamp()
                })
            except IntegrityError:
                # Bu dosya (hash) daha önce yüklenmiş, tekrar yükleme atla.
                continue

        return JsonResponse({"status": "success", "uploaded_assets": new_assets})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required(login_url='/accounts/login/')
def delete_asset_api(request):
    """Bir tasarımı, ona bağlı SEO, Mockup geçmişini ve FİZİKSEL dosyalarını tamamen siler."""
    import os
    from apps.ai.models import DesignVariation
    from apps.products.models import ManualUpload

    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Geçersiz istek yöntemi."}, status=400)

    try:
        data = json.loads(request.body)
        asset_id = data.get('id') # Örn: "ai_45" veya "manual_12"

        if not asset_id:
            return JsonResponse({"status": "error", "message": "Eksik parametre."}, status=400)

        # Dosya silme yardımcı fonksiyonu (Hard diskten fiziksel silme)
        def delete_file(file_field):
            if file_field and hasattr(file_field, 'path') and os.path.exists(file_field.path):
                try:
                    os.remove(file_field.path)
                except Exception:
                    pass

        type_prefix, real_id = asset_id.split('_')

        if type_prefix == 'ai':
            var = DesignVariation.objects.filter(id=real_id, product__user=request.user).first()
            if not var:
                return JsonResponse({"status": "error", "message": "Tasarım bulunamadı veya yetkisiz erişim."}, status=404)
            
            # 1. İlişkili Mockup dosyalarını fiziksel olarak sil
            for mockup in var.mockup_results.all():
                delete_file(mockup.result_image)
            
            # 2. AI'ın ürettiği ana dosyaları fiziksel olarak sil
            delete_file(var.generated_image)
            delete_file(var.no_bg_image)
            delete_file(var.upscaled_image)
            
            # 3. Veritabanından satırı sil (CASCADE sayesinde bağlı SEO ve Mockup satırları da otomatik silinir)
            var.delete()

        elif type_prefix == 'manual':
            upload = ManualUpload.objects.filter(id=real_id, group__user=request.user).first()
            if not upload:
                return JsonResponse({"status": "error", "message": "Tasarım bulunamadı veya yetkisiz erişim."}, status=404)

            # 1. İlişkili Mockup dosyalarını fiziksel olarak sil
            for mockup in upload.mockup_results.all():
                delete_file(mockup.result_image)

            # 2. Yüklenen ana dosyayı fiziksel olarak sil
            delete_file(upload.image)

            # 3. Veritabanından satırı sil
            upload.delete()
        else:
            return JsonResponse({"status": "error", "message": "Geçersiz tasarım tipi."}, status=400)

        return JsonResponse({"status": "success", "message": "Tasarım ve bağlı tüm veriler kalıcı olarak silindi."})

    except Exception as e:        
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required(login_url='/accounts/login/')
def route_assets_api(request):
    """Tasarımları hedefine göre işler (P2 için şeffaflaştırır) ve yönlendirir."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Geçersiz istek."}, status=400)

    try:
        data = json.loads(request.body)
        routes = data.get('routes', {}) 

        if not routes:
            return JsonResponse({"status": "error", "message": "Seçili tasarım bulunamadı."}, status=400)

        creds = ApiCredential.objects.filter(user=request.user).first()
        config = PipelineConfig.objects.filter(user=request.user).first()
        api_key = decrypt_text(creds.replicate_key) if creds and creds.replicate_key else None

        pipeline1_ids = []
        pipeline2_ids = []
        lib_group, _ = UploadGroup.objects.get_or_create(user=request.user, name="Kütüphane Transferleri")

        for asset_id, target_pipeline in routes.items():
            item_type, real_id = asset_id.split('_')

            if item_type == 'ai':
                var = DesignVariation.objects.filter(id=real_id, product__user=request.user).first()
                if not var: continue

                if target_pipeline == 'p1':
                    # P1'in kendi içinde arkaplan silme aracı var, direkt gönder
                    pipeline1_ids.append(str(var.id))
                else:
                    # P2 İÇİN ZORUNLU KONTROL: Arka plan silinmemişse ŞİMDİ SİL
                    if not var.no_bg_image:
                        if not api_key:
                            return JsonResponse({"status": "error", "message": f"Arka plan silmek için API anahtarı eksik! (ID: {var.id})"}, status=400)
                        
                        # BackgroundRemovalService sonucu otomatik olarak var.no_bg_image'e kaydeder
                        success = BackgroundRemovalService.process(var, config.bg_removal_model, api_key)
                        if not success:
                            return JsonResponse({"status": "error", "message": f"{var.id} ID'li görselin arka planı silinemedi."}, status=500)
                        var.refresh_from_db()
                    
                    # P2'ye hazır, şeffaf (.png) görseli (no_bg_image) Kütüphaneye kopyala
                    source_file = var.no_bg_image
                    file_hash = hashlib.md5(source_file.read()).hexdigest()
                    source_file.seek(0) # İmleci başa sar
                    
                    existing_upload = ManualUpload.objects.filter(group__user=request.user, file_hash=file_hash).first()
                    if existing_upload:
                        pipeline2_ids.append(str(existing_upload.id))
                    else:
                        new_upload = ManualUpload.objects.create(
                            group=lib_group,
                            original_filename=f"AI_Transfer_{real_id}.png",
                            file_hash=file_hash
                        )
                        new_upload.image.save(f"transfer_{real_id}.png", source_file.file, save=True)
                        pipeline2_ids.append(str(new_upload.id))

            elif item_type == 'manual':
                pipeline2_ids.append(str(real_id))

        return JsonResponse({
            "status": "success", 
            "redirect_p1": f"/app/tshirt/pipeline1/?load_variations={','.join(pipeline1_ids)}" if pipeline1_ids else None,
            "redirect_p2": f"/app/tshirt/pipeline2/?load_uploads={','.join(pipeline2_ids)}" if pipeline2_ids else None
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)