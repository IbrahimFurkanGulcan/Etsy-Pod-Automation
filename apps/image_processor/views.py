import json
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
# Model yollarını kendi projendeki klasör yapısına göre düzenle:
from apps.image_processor.models import MockupGroup, MockupItem 
from apps.image_processor.services.mockup_processor import MockupEngineService
from apps.common.services.thread_helper import ThreadService

@login_required(login_url='/accounts/login/')
def mockup_templates_page(request):
    """Kullanıcının kendi mockup gruplarını yönettiği sayfa (SPA destekli)"""
    groups = MockupGroup.objects.filter(user=request.user).prefetch_related('items').order_by('-id')
    
    groups_data = []
    for g in groups:
        items_data = []
        for item in g.items.all():
            items_data.append({
                "id": f"db_{item.id}", 
                "name": item.name,
                "url": item.mockup_image.url if item.mockup_image else "",
                "coordinates": item.placement_data
            })
        groups_data.append({
            "id": g.id,
            "name": g.name,
            "created_at": g.created_at.strftime("%d %b %Y"),
            "items": items_data
        })
        
    context = {
        'groups': groups,
        'groups_json': json.dumps(groups_data)
    }
    # html dosyasının konumuna göre burayı ayarlarsın
    return render(request, 'pages/app/settings/mockup_templates.html', context) 

@csrf_exempt
@login_required(login_url='/accounts/login/')
def save_mockups_action(request):
    """FormData ile gelen metinleri (POST) ve resimleri (FILES) veritabanına kaydeder."""
    if request.method == "POST":
        try:
            # FormData içinden grup bilgilerini al
            group_id = request.POST.get('group_id')
            group_name = request.POST.get('group_name', 'Yeni Koleksiyon')

            # 1. Grup İşlemleri
            if group_id and group_id != 'null':
                group = MockupGroup.objects.get(id=group_id, user=request.user)
                if group_name:
                    group.name = group_name
                    group.save()
            else:
                group = MockupGroup.objects.create(user=request.user, name=group_name)

            saved_count = 0

            # 2. ESKİ Resimleri Güncelleme (db_ takılı olanlar)
            # request.POST içindeki anahtarları (keys) gezerek kimlikleri buluyoruz
            db_item_ids = [key.split('_')[2] for key in request.POST.keys() if key.startswith('name_db_')]
            
            for item_id in set(db_item_ids):
                item = MockupItem.objects.get(id=item_id, group__user=request.user)
                item.name = request.POST.get(f'name_db_{item_id}')
                item.placement_data = json.loads(request.POST.get(f'coords_db_{item_id}'))
                item.save()
                saved_count += 1

            # 3. YENİ Resimleri Yükleme (mockup_ takılı olanlar ve FILES içinde gelenler)
            for file_key, uploaded_file in request.FILES.items():
                if file_key.startswith('file_mockup_'):
                    mockup_id = file_key.split('file_')[1] # file_mockup_1234 -> mockup_1234
                    
                    name = request.POST.get(f'name_{mockup_id}')
                    coords_str = request.POST.get(f'coords_{mockup_id}')

                    # Doğrudan Django'nun File/Image field'ına atıyoruz (En güvenli yol)
                    MockupItem.objects.create(
                        group=group,
                        name=name,
                        mockup_image=uploaded_file,
                        placement_data=json.loads(coords_str)
                    )
                    saved_count += 1

            return JsonResponse({"status": "success", "message": f"Koleksiyon başarıyla kaydedildi ({saved_count} görsel)."})
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Sadece POST metodu geçerlidir."}, status=405)


@csrf_exempt
@login_required(login_url='/accounts/login/')
def get_mockup_templates_api(request):
    """Kullanıcının veritabanındaki Mockup Gruplarını döner."""
    try:
        # 1. HATA ÇÖZÜMÜ: is_active yerine user kullanıyoruz. 
        # Böylece herkes sadece kendi eklediği grupları görür. (Veri izolasyonu)
        groups = MockupGroup.objects.filter(user=request.user).prefetch_related('items')
        
        data = []
        for g in groups:
            # 2. KAPAK FOTOĞRAFI BULMA:
            first_item = g.items.first()
            
            image_url = ""
            
            if first_item and hasattr(first_item, 'mockup_image') and first_item.mockup_image:
                image_url = first_item.mockup_image.url
            
            data.append({
                "id": g.id,
                "title": g.name,
                "image_url": image_url
            })
            
        return JsonResponse({"templates": data})
        
    except Exception as e:
        # Sunucu çökmesi yerine JS tarafına yakalanabilir bir hata dönüyoruz
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required(login_url='/accounts/login/')
def generate_mockups_api(request):
    """Frontend'den gelen tasarım-şablon eşleştirmelerini (mapping) alır ve paralel işler."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            mapping = data.get('mapping', {})
            force_recreate = data.get('force_recreate', False)

            tasks = []
            
            # mapping formatı: { "design_id": ["group_id_1", "group_id_2"] }
            for design_id_str, group_ids in mapping.items():
                design_id = int(design_id_str)
                # İlgili grupların içindeki koordinatı çizilmiş tüm itemleri bul
                items = MockupItem.objects.filter(
                    group__id__in=group_ids, 
                    placement_data__isnull=False
                ).exclude(placement_data={})
                
                for item in items:
                    tasks.append({
                        "design_id": design_id,
                        "item_id": item.id,
                        "group_id": item.group_id,
                        "force": force_recreate
                    })

            if not tasks:
                return JsonResponse({"status": "error", "message": "İşlenecek geçerli bir şablon koordinatı bulunamadı."}, status=400)

            # ThreadService'den dönen sonuçların hangi tasarıma ait olduğunu bilmek için
            # küçük bir sarmalayıcı (wrapper) yazıyoruz:
            def process_and_track(task):
                res = MockupEngineService.apply_design_to_mockup(task)
                res['design_id'] = str(task['design_id']) # Sonuca kimliğini ekle
                res['group_id'] = str(task['group_id'])
                return res

            print(f"🏭 Toplam {len(tasks)} görev paralel kuyruğa alındı...")
            results = ThreadService.run_parallel(process_and_track, tasks, max_workers=5)

            # Sonuçları Frontend'in okuyabileceği gibi grupla: { "design_id": [url1, url2] }
            grouped_results = {}
            for res in results:
                d_id = res.get('design_id')
                g_id = res.get('group_id')
                
                if d_id not in grouped_results:
                    grouped_results[d_id] = {}
                if g_id not in grouped_results[d_id]:
                    grouped_results[d_id][g_id] = []
                    
                if res.get('success') and res.get('url'):
                    grouped_results[d_id][g_id].append(res.get('url'))

            return JsonResponse({"status": "success", "results": grouped_results})
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
            
    return JsonResponse({"status": "error", "message": "POST gerekli"}, status=405)
        