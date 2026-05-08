import json, os, traceback
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from apps.accounts.models import ApiCredential
from apps.common.services.encryption import decrypt_text
from apps.products.services.orchestrator import Pipeline2Orchestrator
from apps.products.models import ManualUpload

@csrf_exempt
@login_required(login_url='/accounts/login/')
def upload_manual_designs_action(request):
    """Pipeline 2: Sürükle bırak ile yüklenen tasarımları karşılar."""
    if request.method == "POST":
        try:
            files = request.FILES.getlist('designs')
            group_name = request.POST.get('group_name', 'Adsız Yükleme Seti')

            if not files:
                return JsonResponse({"status": "error", "message": "Hiç dosya seçilmedi."}, status=400)

            # İşi servise devret
            result = Pipeline2Orchestrator.process_uploads(request.user, files, group_name)

            return JsonResponse({
                "status": "success", 
                "group_id": result["group_id"],
                "items": result["items"],
                "message": f"{len(files)} tasarım başarıyla işlendi."
            })
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
            
    return JsonResponse({"status": "error", "message": "POST gerekli"}, status=405)


@csrf_exempt
@login_required(login_url='/accounts/login/')
def process_batch_action(request):
    """Pipeline 2: Seçilen görevleri (Vision, SEO, Mockup) başlatır."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            upload_ids = data.get('upload_ids', [])
            do_seo = data.get('do_seo', False)
            do_mockup = data.get('do_mockup', False)
            mockup_mapping = data.get('mockup_mapping', {}) 
            seo_targets = data.get('seo_targets', {})
            action_type = data.get('action_type', 'use_existing')

            if not upload_ids:
                return JsonResponse({"status": "error", "message": "İşlenecek tasarım seçilmedi."}, status=400)

            # API Key Güvenliği
            creds = ApiCredential.objects.filter(user=request.user).first()
            if not creds or not creds.replicate_key:
                return JsonResponse({"status": "error", "message": "API Anahtarı bulunamadı."}, status=400)
            api_key = decrypt_text(creds.replicate_key)

            # İşi Orkestratöre devrederken:
            results = Pipeline2Orchestrator.process_batch_items(
                user=request.user,
                api_key=api_key,
                upload_ids=upload_ids,
                seo_targets=seo_targets,
                do_mockup=do_mockup,
                mockup_mapping=mockup_mapping, 
                action_type=action_type
            )

            return JsonResponse({"status": "success", "results": results})

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "POST gerekli"}, status=405)


@login_required(login_url='/accounts/login/')
def get_batch_mockups(request, upload_id):
    """Pipeline 2: İşlem bitince modal (galeri) açılması için üretilmiş Mockup URL'lerini döner."""
    if request.method == "GET":
        try:
            upload = ManualUpload.objects.get(id=upload_id, group__user=request.user)
            mockups_dir = os.path.join(settings.MEDIA_ROOT, 'generated_mockups', 'manual', str(upload.id))
            
            mockup_urls = []
            if os.path.exists(mockups_dir):
                for file_name in os.listdir(mockups_dir):
                    if file_name.endswith('.png') or file_name.endswith('.jpg'):
                        url = f"{settings.MEDIA_URL}generated_mockups/manual/{upload.id}/{file_name}"
                        mockup_urls.append(url)
            
            return JsonResponse({
                "status": "success",
                "urls": mockup_urls,
                "message": f"{len(mockup_urls)} adet mockup bulundu."
            })
            
        except ManualUpload.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Tasarım bulunamadı."}, status=404)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Sadece GET istekleri desteklenir."}, status=405)

@login_required(login_url='/accounts/login/')
def get_user_library(request):
    """Kullanıcının daha önce yüklediği tasarımları (Kütüphane) getirir."""
    if request.method == "GET":
        # Son 30 tasarımı getir (Mükerrerleri engellemek için)
        uploads = ManualUpload.objects.filter(group__user=request.user).order_by('-created_at')[:30]
        data = [
            {"id": u.id, "url": u.image.url, "name": u.original_filename} 
            for u in uploads
        ]
        return JsonResponse({"status": "success", "designs": data})
    return JsonResponse({"status": "error", "message": "GET gerekli"}, status=405)