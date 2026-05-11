import json
import traceback
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .services.export import ProjectExportService 


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