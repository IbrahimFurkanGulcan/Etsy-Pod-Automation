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