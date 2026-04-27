import re
import io
import zipfile
import os
import json
import requests
import traceback
import base64
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from .scraper import scrape_etsy_product
from .models import EtsyProduct, DesignVariation, UserSettings, SeoOptimization, MockupGroup, MockupItem, UploadGroup, ManualUpload
from .detect_crop import crop_and_save_product_design
from .generation_services import UniversalAIClient, PromptManager, ModelRegistry
from concurrent.futures import ThreadPoolExecutor, as_completed
from .seo_service import generate_seo_for_product
from django.conf import settings
from django.utils.text import slugify
from django.core.files.storage import FileSystemStorage
from .mockup_processor import process_single_mockup




@csrf_exempt
@login_required(login_url='/login/') # Güvenlik: Sadece giriş yapanlar ayar kaydedebilir
def save_config_action(request):
    if request.method == "POST":
        try:
            config_data = json.loads(request.body)
            
            # 1. Session'a Kaydet (Uygulama içi hızlı erişim için)
            request.session['ai_config'] = config_data
            
            # 2. Veritabanına Kaydet (Tarayıcı kapansa bile unutulmaması için)
            # get_or_create: Kullanıcının ayar profili yoksa yaratır, varsa getirir
            user_settings, created = UserSettings.objects.get_or_create(user=request.user)
            user_settings.replicate_api_key = config_data['api']['key']
            user_settings.pipeline_config = config_data['pipeline']
            user_settings.save()
            
            print(f"🟢 [{request.user.username}] kullanıcısının ayarları kalıcı olarak DB'ye mühürlendi!")
            
            return JsonResponse({"status": "success", "message": "Konfigürasyon kaydedildi."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
            
    return JsonResponse({"status": "error", "message": "POST gerekli"}, status=405)


@login_required(login_url='/login/')
def config_page(request):
    # 1. Kullanıcının daha önce kaydettiği ayarları veritabanından çekelim
    user_settings, created = UserSettings.objects.get_or_create(user=request.user)
    saved_api_key = user_settings.replicate_api_key or ""

    saved_pipeline = user_settings.pipeline_config if user_settings.pipeline_config else []

    # =========================================================
    # 🚀 Veri temizleme (Double Encoding Koruması)
    # Eğer veritabanına yanlışlıkla metin (string) olarak kaydedildiyse:
    if isinstance(saved_pipeline, str):
        try:
            saved_pipeline = json.loads(saved_pipeline) # Metni gerçek Python listesine çevir
        except json.JSONDecodeError:
            saved_pipeline = [] # Hatalıysa boş liste yap
    # =========================================================

    # 2. Generation Modellerini Python'dan Çekiyoruz
    generation_models = [
        {
            "id": "flux-2-pro",
            "name": "Flux 2.0 Pro",
            "price": "En Yüksek Kalite",
            "defaultPrompt": PromptManager.get_prompt("flux-2-pro")[0]
        },
        {
            "id": "seedream-4.5",
            "name": "Seedream 4.5",
            "price": "2K Çözünürlük",
            "defaultPrompt": PromptManager.get_prompt("seedream-4.5")[0]
        },
        {
            "id": "nano-banana",
            "name": "Nano Banana",
            "price": "Hızlı / Optimize",
            "defaultPrompt": PromptManager.get_prompt("nano-banana")[0]
        }
    ]

    # 3. Diğer Varsayılan Promptları Çekiyoruz
    default_prompts = {
        "detection": {
            "grounding-dino": PromptManager.get_prompt("grounding-dino")[0]
        },
        "seo": {
            "gpt-4o": {
                "user_prompt": PromptManager.get_prompt("gpt-4o")[0],
                "title_system_prompt": PromptManager.get_prompt("gpt-4o_title")[1],
                "tags_system_prompt": PromptManager.get_prompt("gpt-4o_tag")[1]
            }
        }
    }

    # Context Paketi
    context = {
        "generation_models_json": json.dumps(generation_models),
        "default_prompts_json": json.dumps(default_prompts),
        "saved_api_key": saved_api_key,
        "saved_pipeline_json": json.dumps(saved_pipeline),
    }
    return render(request, 'manager/config.html', context)


@login_required(login_url='/login/')
def mockup_templates_page(request):
    """Kullanıcının kendi mockup gruplarını yönettiği sayfa (SPA destekli)"""
    
    groups = MockupGroup.objects.filter(user=request.user).prefetch_related('items').order_by('-id')
    
    # 🚀 JavaScript'in (SPA) okuyabilmesi için verileri JSON formatına paketliyoruz
    groups_data = []
    for g in groups:
        items_data = []
        for item in g.items.all():
            items_data.append({
                "id": f"db_{item.id}", # Frontend'e bunun DB'den geldiğini söylemek için 'db_' ekliyoruz
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
        'groups_json': json.dumps(groups_data) # Paketi HTML'e gönder
    }
    return render(request, 'manager/mockup_templates.html', context)


@login_required(login_url='/login/')
def dashboard(request):
    recent_products = EtsyProduct.objects.filter(user=request.user).order_by('-id')[:5]
    # Kullanıcının mockup koleksiyonlarını çekiyoruz
    mockup_groups = MockupGroup.objects.filter(user=request.user).order_by('-id')
    
    return render(request, 'manager/dashboard.html', {
        'recent_products': recent_products,
        'mockup_groups': mockup_groups
    })



@csrf_exempt
@login_required(login_url='/login/')
def save_mockups_action(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            group_name = data.get('group_name')
            mockups = data.get('mockups', [])
            group_id = data.get('group_id') # Eğer mevcut bir grubu güncelliyorsak

            if not mockups:
                return JsonResponse({"status": "error", "message": "Kaydedilecek resim bulunamadı."}, status=400)

            # 1. Grup İşlemleri (Yeni mi oluşturulacak, var olan mı güncellenecek?)
            if group_id:
                # Mevcut grubu bul
                group = MockupGroup.objects.get(id=group_id, user=request.user)
                # İstersen grup adını da güncelleyebilirsin
                if group_name:
                    group.name = group_name
                    group.save()
            else:
                # Yeni Grup Oluştur
                if not group_name:
                    group_name = "Yeni Koleksiyon"
                group = MockupGroup.objects.create(user=request.user, name=group_name)

            # 2. Resim (Item) İşlemleri
            saved_count = 0
            for mockup in mockups:
                # Eğer resim daha önceden veritabanındaysa (ID'si varsa) sadece koordinatlarını güncelle
                if str(mockup.get('id')).startswith('db_'):
                    real_id = mockup['id'].split('_')[1]
                    item = MockupItem.objects.get(id=real_id, group__user=request.user)
                    item.name = mockup['name']
                    item.placement_data = mockup['coordinates']
                    item.save()
                    saved_count += 1
                
                # Eğer yeni yüklenmiş bir resimse (Base64) sıfırdan oluştur
                elif str(mockup.get('id')).startswith('mockup_'):
                    format, imgstr = mockup['url'].split(';base64,') 
                    ext = format.split('/')[-1]
                    file_name = f"{mockup['name'].replace(' ', '_')}_{request.user.id}.{ext}"
                    img_data = ContentFile(base64.b64decode(imgstr), name=file_name)

                    MockupItem.objects.create(
                        group=group,
                        name=mockup['name'],
                        mockup_image=img_data,
                        placement_data=mockup['coordinates']
                    )
                    saved_count += 1

            return JsonResponse({"status": "success", "message": f"Koleksiyon kaydedildi ({saved_count} görsel)."})
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Sadece POST"}, status=405)

# ==========================================
# AUTH (GİRİŞ & KAYIT) SİSTEMİ
# ==========================================
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        kullanici_adi = request.POST.get('username')
        sifre = request.POST.get('password')
        sifre_tekrar = request.POST.get('password_confirm')

        if sifre != sifre_tekrar:
            messages.error(request, "Şifreler uyuşmuyor!")
            return redirect('register')
        
        if User.objects.filter(username=kullanici_adi).exists():
            messages.error(request, "Bu kullanıcı adı zaten alınmış!")
            return redirect('register')

        # Yeni Kullanıcıyı Yarat
        yeni_kullanici = User.objects.create_user(username=kullanici_adi, password=sifre)
        
        # Boş bir Ayar Profili (UserSettings) oluştur
        UserSettings.objects.create(user=yeni_kullanici)

        # Otomatik giriş yaptır
        login(request, yeni_kullanici)
        
        # 🚀 YENİ KAYIT: Ayarları olmadığı için DİREKT CONFIG sayfasına yolla
        return redirect('config_page') 

    return render(request, 'manager/register.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        kullanici_adi = request.POST.get('username')
        sifre = request.POST.get('password')

        user = authenticate(request, username=kullanici_adi, password=sifre)
        
        if user is not None:
            login(request, user)

            remember_me = request.POST.get('remember_me')
            if remember_me:
                # Eğer kutu işaretliyse, oturumu 2 hafta (1209600 saniye) boyunca hafızada tut
                request.session.set_expiry(1209600)
            else:
                # Kutu işaretli değilse, tarayıcı penceresi kapandığı an hesaptan çık (Güvenlik)
                request.session.set_expiry(0)
            
            # URL'de "next" parametresi varsa önce oraya git (Örn: Yetkisiz girilen bir linkten atıldıysa)
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)

            # 🚀 AKILLI YÖNLENDİRME KONTROLÜ
            try:
                # Kullanıcının ayarlarını kontrol et
                user_settings = user.settings 
                has_config = bool(user_settings.pipeline_config) # Ayar yapmış mı? (True/False)
            except:
                has_config = False # Ayar dosyası bile yoksa False say
                
            if not has_config:
                # Eğer daha önce hiç "Kaydet" butonuna basmamışsa (Pipeline boşsa)
                return redirect('config_page')
            else:
                # Eğer daha önce ayarını yapıp kaydettiyse direkt ana sayfaya al
                return redirect('dashboard')

        else:
            messages.error(request, "Kullanıcı adı veya şifre hatalı!")
            return redirect('login')

    return render(request, 'manager/login.html')


def logout_action(request):
    logout(request)
    return redirect('login')


@csrf_exempt
@login_required(login_url='/login/')
def scrape_action(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            url = data.get('url')
            
            if not url:
                return JsonResponse({"status": "error", "message": "URL eksik!"}, status=400)

            # --- AKILLI ID ARAMA BAŞLIYOR ---
            product = None
            
            # URL'nin içinden "listing/" sonrasındaki numaraları yakalıyoruz
            match = re.search(r'listing/(\d+)', url)
            
            if match:
                listing_id = match.group(1)
                print(f"🔍 URL'den yakalanan ID: {listing_id}")
                
                # Veritabanında, URL'sinin içinde bu ID geçen ürünü arıyoruz (__contains)
                product = EtsyProduct.objects.filter(url__contains=f"listing/{listing_id}", user=request.user).first()
            else:
                # Eğer URL standart listing formatında değilse, düz arama yap
                product = EtsyProduct.objects.filter(url=url, user=request.user).first()

            if product:
                print(f"⚡ BAŞARILI: {product.id} ID'li ürün veritabanından saniyeler içinde çekildi!")
            else:
                print("🐌 Ürün bulunamadı, Scraper sıfırdan çalıştırılıyor...")
                product = scrape_etsy_product(url)

                if product:
                    product.user = request.user # Ürünü giriş yapmış kullanıcıya zimmetle
                    product.save()
            # --- AKILLI ARAMA BİTTİ ---

            if product:
                return JsonResponse({
                    "status": "success",
                    "id": product.id,
                    "title": product.title,
                    "price": product.price,
                    "image_url": product.image_url,
                    "description": product.description,
                    "tags": product.tags.split(',') if product.tags else [],
                    "views": product.views or 0,
                    "favorited": product.favorites_count or 0, # Senin modelindeki doğru isim
                })
            else:
                return JsonResponse({"status": "error", "message": "Scraper veriyi çekemedi."}, status=500)
        
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Sadece POST desteklenir."}, status=405)


@csrf_exempt
@login_required(login_url='/login/')
def generate_designs_action(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            force_recreate = data.get('force_recreate', False)

            if not product_id:
                return JsonResponse({"status": "error", "message": "Ürün ID eksik."}, status=400)

            product = EtsyProduct.objects.get(id=product_id, user=request.user)

            # ========================================================
            # 1. KULLANICININ DİNAMİK AYARLARINI ÇEK
            # ========================================================
            config_data = request.session.get('ai_config')
            user_settings = UserSettings.objects.get(user=request.user)

            if not config_data and user_settings.pipeline_config:
                config_data = {
                    "api": {"key": user_settings.replicate_api_key},
                    "pipeline": user_settings.pipeline_config
                }
            
            if not config_data or not config_data.get('api', {}).get('key'):
                return JsonResponse({"status": "error", "message": "API Key bulunamadı. Lütfen 'Config' sayfasından ayarlarınızı kaydedin."}, status=400)

            api_key = config_data['api']['key']
            pipeline = config_data.get('pipeline', [])
            
            gen_config = next((step for step in pipeline if step['step'] == 'generation'), None)

            if not gen_config or not gen_config.get('models'):
                return JsonResponse({"status": "error", "message": "Konfigürasyonda hiçbir üretim modeli seçilmemiş!"}, status=400)

            # ========================================================
            # 2. KATI HAFIZA KONTROLÜ (HAYALETLERİ GÖRMEZDEN GELİR)
            # ========================================================
            if not force_recreate:
                # SADECE içinde gerçekten görsel olanları filtrele (Boş olanları atla)
                existing_variations = DesignVariation.objects.filter(
                    product=product
                ).exclude(generated_image__isnull=True).exclude(generated_image__exact='').order_by('-id')
                
                if existing_variations.exists():
                    print(f"⚡ [{product.id}] Zaten üretilmiş resimler DB'den getiriliyor...")
                    generated_images = []
                    for var in existing_variations[:len(gen_config['models'])]: 
                        generated_images.append({
                            "id": var.id,
                            "src": var.generated_image.url, 
                            "label": f"{var.ai_model_name} (Kayıtlı)"
                        })
                    
                    # Eğer cidden resim bulduysa dön, bulamadıysa (sadece boş satır varsa) üretmeye devam et!
                    if generated_images:
                        return JsonResponse({"status": "success", "images": generated_images, "cached": True})

            # ========================================================
            # 3. KIRPMA İŞLEMİ (DINO)
            # ========================================================
            crop_path = None
            if product.cropped_image and os.path.exists(product.cropped_image.path):
                crop_path = product.cropped_image.path
            else:
                crop_and_save_product_design(product.id)
                product.refresh_from_db()
                if product.cropped_image and os.path.exists(product.cropped_image.path):
                    crop_path = product.cropped_image.path

            if not crop_path:
                return JsonResponse({"status": "error", "message": "Kırpılmış görsel bulunamadı."}, status=500)

            # ========================================================
            # 4. PARALEL İŞLEME (UNIVERSAL AI CLIENT)
            # ========================================================
            ai_client = UniversalAIClient(api_key=api_key, platform="replicate")

            def run_single_model(model_info):
                model_id = model_info['model']
                custom_prompt = model_info.get('prompt')
                try:
                    print(f"🎨 [{model_id}] API'ye gönderiliyor...")
                    
                    # Motor URL'yi getirir
                    # Motor URL'yi getirir
                    image_url = ai_client.execute(
                        model_id=model_id, 
                        prompt=custom_prompt, 
                        file_path=crop_path
                    )
                    
                    # Eğer sonuç bir Liste (Array) ise, ilk elemanını al!
                    if isinstance(image_url, list) and len(image_url) > 0:
                        image_url = image_url[0]
                    
                    if image_url and str(image_url).startswith("http"):
                        variation = DesignVariation.objects.create(
                            product=product,
                            ai_model_name=model_id,
                            prompt_used=custom_prompt,
                            status="completed"
                        )
                        
                        response = requests.get(image_url)
                        if response.status_code == 200:
                            file_name = f"{model_id}_{product.id}_{variation.id}.png"
                            variation.generated_image.save(file_name, ContentFile(response.content))
                            print(f"✅ BAŞARILI: {file_name} kaydedildi!")
                        else:
                            print(f"❌ İndirme Hatası ({model_id}): HTTP {response.status_code}")
                    else:
                        print(f"⚠️ Geçerli bir URL dönmedi ({model_id}): {image_url}")

                except Exception as e:
                    print(f"❌ Motor Hatası ({model_id}): {e}")

            # Eşzamanlı başlat
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(run_single_model, m_info) for m_info in gen_config['models']]
                for future in as_completed(futures):
                    future.result() 

            # ========================================================
            # 5.SONUÇLARI ARAYÜZE GÖNDERME
            # ========================================================
            new_variations = DesignVariation.objects.filter(
                product=product
            ).exclude(generated_image__isnull=True).exclude(generated_image__exact='').order_by('-id')[:len(gen_config['models'])]
            
            generated_images = []
            for var in new_variations:
                generated_images.append({
                    "id": var.id,
                    "src": var.generated_image.url, 
                    "label": var.ai_model_name
                })

            return JsonResponse({"status": "success", "images": generated_images, "cached": False})

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Sadece POST"}, status=405)

@csrf_exempt
@login_required(login_url='/login/')
def process_selected_designs_action(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            selected_ids = data.get('selected_ids', [])
            product_id = data.get('product_id')

            if not selected_ids or not product_id:
                return JsonResponse({"status": "error", "message": "ID veya seçim eksik."}, status=400)

            product = EtsyProduct.objects.get(id=product_id, user=request.user)

            # ========================================================
            # 1. KULLANICI AYARLARINI VE API ANAHTARINI ÇEK
            # ========================================================
            user_settings = UserSettings.objects.get(user=request.user)
            config_data = request.session.get('ai_config')

            if not config_data and user_settings.pipeline_config:
                config_data = {
                    "api": {"key": user_settings.replicate_api_key},
                    "pipeline": user_settings.pipeline_config
                }
            
            if not config_data or not config_data.get('api', {}).get('key'):
                return JsonResponse({"status": "error", "message": "API Key bulunamadı."}, status=400)

            api_key = config_data['api']['key']
            pipeline = config_data.get('pipeline', [])
            
            # Kullanıcının seçtiği modelleri pipeline'dan bulalım
            upscale_step = next((s for s in pipeline if s['step'] == 'upscale'), None)
            bg_step = next((s for s in pipeline if s['step'] == 'bg_removal'), None)

            # Evrensel motoru başlat
            ai_client = UniversalAIClient(api_key=api_key, platform="replicate")

            # ========================================================
            # 2. İŞLEME FONKSİYONU (THREAD İÇİNDE ÇALIŞACAK)
            # ========================================================
            def process_variation(var_id):
                v = DesignVariation.objects.get(id=var_id)
                try:
                    # Zaten işlenmişse pas geç (Hız kazandırır)
                    if v.no_bg_image and v.no_bg_image.name:
                        return {"id": v.id, "src": v.no_bg_image.url, "success": True}

                    v.status = 'processing'
                    v.save()
                    
                    current_path = v.generated_image.path

                    # --- A. UPSCALE (Eğer aktifse) ---
                    if upscale_step:
                        model_id = upscale_step['model'] # Örn: 'recraft-crisp'
                        print(f"🚀 [ID: {v.id}] {model_id} ile Upscale yapılıyor...")
                        
                        up_url = ai_client.execute(model_id=model_id, file_path=current_path)
                        
                        if isinstance(up_url, list): up_url = up_url[0] # Liste gelirse temizle

                        if up_url:
                            resp = requests.get(up_url)
                            if resp.status_code == 200:
                                file_name = f"upscaled_{product.id}_{v.id}.png"
                                v.upscaled_image.save(file_name, ContentFile(resp.content), save=False)
                                v.save()
                                current_path = v.upscaled_image.path # Bir sonraki adım (BG) için yeni yolu kullan

                    # --- B. BACKGROUND REMOVAL (Eğer aktifse) ---
                    if bg_step:
                        model_id = bg_step['model'] # Örn: 'bria-rmbg'
                        print(f"✂️ [ID: {v.id}] {model_id} ile Arka Plan siliniyor...")
                        
                        bg_url = ai_client.execute(model_id=model_id, file_path=current_path)
                        
                        if isinstance(bg_url, list): bg_url = bg_url[0]

                        if bg_url:
                            resp = requests.get(bg_url)
                            if resp.status_code == 200:
                                file_name = f"nobg_{product.id}_{v.id}.png"
                                v.no_bg_image.save(file_name, ContentFile(resp.content), save=False)
                                v.status = 'completed'
                                v.save()
                                return {"id": v.id, "src": v.no_bg_image.url, "success": True}

                    # Eğer hiçbir adım aktif değilse sadece statüyü bitir
                    v.status = 'completed'
                    v.save()
                    return {"id": v.id, "success": True}

                except Exception as e:
                    print(f"❌ İşleme Hatası (ID {var_id}): {e}")
                    v.status = 'failed'
                    v.save()
                    return {"id": v.id, "error": str(e), "success": False}

            # ========================================================
            # 3. PARALEL ÇALIŞTIRMA
            # ========================================================
            processed_results = []
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(process_variation, v_id) for v_id in selected_ids]
                for future in as_completed(futures):
                    processed_results.append(future.result())

            success_images = [res for res in processed_results if res.get('success')]
            return JsonResponse({
                "status": "success",
                "images": success_images,
                "message": f"{len(success_images)} tasarım başarıyla işlendi."
            })

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "POST gerekli"}, status=405)


@csrf_exempt
@login_required(login_url='/login/')
def generate_seo_action(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST gerekli"}, status=405)

    try:
        data           = json.loads(request.body)
        product_id     = data.get('product_id')
        force_recreate = data.get('force_recreate', False)
        target         = data.get('target', 'both')
        niche          = data.get('niche', 'Graphic T-Shirt')

        if not product_id:
            return JsonResponse({"status": "error", "message": "Ürün ID eksik."}, status=400)

        product = EtsyProduct.objects.get(id=product_id, user=request.user)

        # ── 1. CACHE ─────────────────────────────────────────────
        if not force_recreate and hasattr(product, 'seo') and product.seo.generated_title:
            print(f"⚡ [ID: {product.id}] SEO verileri DB'den anında çekildi!")
            return JsonResponse({
                "status": "success",
                "title":  product.seo.generated_title,
                "tags":   product.seo.generated_tags,
                "cached": True,
            })

        # ── 2. KULLANICI AYARLARINI OKU ──────────────────────────
        user_settings = UserSettings.objects.get(user=request.user)
        config_data   = request.session.get('ai_config')

        if not config_data and user_settings.pipeline_config:
            config_data = {
                "api":      {"key": user_settings.replicate_api_key},
                "pipeline": user_settings.pipeline_config,
            }

        if not config_data:
            return JsonResponse(
                {"status": "error", "message": "Ayarlar bulunamadı. Lütfen önce Config sayfasını kaydedin."},
                status=400,
            )

        # ── 3. SEO ADIMINI PIPELINE'DAN ÇEK ─────────────────────
        seo_config = next(
            (s for s in config_data.get('pipeline', []) if s['step'] == 'seo'),
            None,
        )
        if not seo_config:
            return JsonResponse({"status": "error", "message": "SEO modülü aktif değil!"}, status=400)

        # ── 4. PROMPTLARI DB'DEN OKU ─────────────────────────────
        # Kullanıcı config sayfasında gördüğü default'u değiştirip kaydetmiş olabilir.
        # Her iki alan da DB'de dolu olmak zorunda.
        title_system_prompt = seo_config.get('title_system_prompt', '').strip()
        tags_system_prompt  = seo_config.get('tags_system_prompt',  '').strip()

        if not title_system_prompt:
            return JsonResponse(
                {"status": "error", "message": "Title sistem promptu eksik. Lütfen Config sayfasını kontrol edin."},
                status=400,
            )
        if not tags_system_prompt:
            return JsonResponse(
                {"status": "error", "message": "Tags sistem promptu eksik. Lütfen Config sayfasını kontrol edin."},
                status=400,
            )

        model_id = seo_config.get('model_id', 'gpt-4o')

        # ── 5. CLIENT'I HAZIRLA ──────────────────────────────────
        api_key = config_data['api'].get('key', '').strip()
        if not api_key:
            return JsonResponse({"status": "error", "message": "API anahtarı bulunamadı."}, status=400)

        ai_client = UniversalAIClient(api_key=api_key)

        # ── 6. SEO SERVİSİNİ ÇAĞIR ──────────────────────────────
        seo_record = generate_seo_for_product(
            product_id=product.id,
            ai_client=ai_client,
            model_id=model_id,
            title_system_prompt=title_system_prompt,
            tags_system_prompt=tags_system_prompt,
            target=target,
            niche=niche,
        )

        if not seo_record:
            return JsonResponse(
                {"status": "error", "message": "SEO üretilemedi. Lütfen tekrar deneyin."},
                status=500,
            )

        return JsonResponse({
            "status": "success",
            "title":  seo_record.generated_title,
            "tags":   seo_record.generated_tags,
            "cached": False,
        })

    except EtsyProduct.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Ürün bulunamadı."}, status=404)
    except UserSettings.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Kullanıcı ayarları bulunamadı."}, status=404)
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@login_required(login_url='/login/') # 1. GÜVENLİK: Giriş yapmayan indiremez
def export_project_action(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            
            if not product_id:
                return JsonResponse({"status": "error", "message": "Ürün ID eksik."}, status=400)
            
            # 1. GÜVENLİK: Sadece o anki kullanıcıya ait ürünü çekiyoruz
            # Bu sayede ID tahmini ile başkasının verisine ulaşılamaz.
            product = EtsyProduct.objects.get(id=product_id, user=request.user)
            
            # 2. Hafızada (RAM) sanal bir ZIP dosyası oluşturuyoruz
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                
                # 3. SEO Metin Dosyasını ZIP'e Ekle
                # OneToOneField olduğu için 'product.seo' üzerinden güvenle erişiyoruz
                if hasattr(product, 'seo') and product.seo.generated_title:
                    seo_content = (
                        f"--- ETSY SEO OPTIMIZATION ---\n\n"
                        f"TARGET TITLE:\n{product.seo.generated_title}\n\n"
                        f"TARGET TAGS:\n{product.seo.generated_tags}\n\n"
                        f"--- ORIGINAL DATA ---\n"
                        f"Source URL: {product.url}\n"
                    )
                    zip_file.writestr(f"Product_{product.id}_SEO.txt", seo_content)
                else:
                    zip_file.writestr(f"Product_{product.id}_SEO.txt", "SEO verisi henüz üretilmemiş.")

                # 4. İşlenmiş (PNG) Resimleri ZIP'e Ekle
                # Sadece durumu 'completed' olan ve transparan hali (no_bg_image) olanları al
                processed_vars = product.variations.filter(status='completed').exclude(no_bg_image='')
                
                for var in processed_vars:
                    try:
                        # .read() metodu hem local diskte hem de bulutta (AWS S3 vb.) çalışır
                        file_data = var.no_bg_image.read()
                        
                        # Dosya ismini model adıyla süsleyelim ki kullanıcı neyi indirdiğini bilsin
                        file_name = f"Design_{product.id}_{var.ai_model_name}_{var.id}.png"
                        zip_file.writestr(file_name, file_data)
                        
                    except Exception as e:
                        print(f"⚠️ Resim ZIP'e eklenemedi (ID: {var.id}): {e}")

            # 5. Üretilmiş Mockupları (varsa) ZIP'e Ekle
                mockups_dir = os.path.join(settings.MEDIA_ROOT, 'generated_mockups', str(product.id))
                if os.path.exists(mockups_dir):
                    for file_name in os.listdir(mockups_dir):
                        file_path = os.path.join(mockups_dir, file_name)
                        with open(file_path, 'rb') as f:
                            # ZIP içinde 'Mockups' adında bir klasöre koyuyoruz
                            zip_file.writestr(f"Mockups/{file_name}", f.read())
            
            # 6. ZIP dosyasını hazırlayıp tarayıcıya gönderiyoruz
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/zip')
            
            # Dosya adını ürün başlığına göre (varsa) özelleştirebiliriz
            clean_title = "".join([c for c in str(product.id) if c.isalnum()])
            response['Content-Disposition'] = f'attachment; filename="EtsyAI_Project_{clean_title}.zip"'
            
            print(f"📦 [{request.user.username}] için proje başarıyla paketlendi.")
            return response

        except EtsyProduct.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Ürün bulunamadı veya bu işleme yetkiniz yok."}, status=403)
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
    return JsonResponse({"status": "error", "message": "POST gerekli"}, status=405)

@login_required(login_url='/login/')
def custom_logout_view(request):
    logout(request) # Oturumu ve Session'ı (geçici hafızayı) temizler
    return redirect('/login/')


@login_required(login_url='/login/')
def history_page(request):
    # Kullanıcının ürünlerini en yeniden eskiye doğru çeker
    products = EtsyProduct.objects.filter(user=request.user).order_by('-id')
    return render(request, 'manager/history.html', {'products': products})

@csrf_exempt # Ajax isteklerinde csrf sorunu yaşamamak için
@login_required(login_url='/login/')
def delete_history_item(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        target = request.POST.get('target') # 'full', 'design', 'seo'
        
        try:
            product = EtsyProduct.objects.get(id=product_id, user=request.user)
            
            if target == 'full':
                product.delete() # Ürünü, resimleri ve SEO'yu toptan siler (CASCADE)
                return JsonResponse({'status': 'success', 'message': 'Tüm analiz silindi.'})
            
            elif target == 'design':
                product.variations.all().delete() # Sadece AI resimlerini siler
                return JsonResponse({'status': 'success', 'message': 'Tasarım verileri silindi.'})
            
            elif target == 'seo':
                if hasattr(product, 'seo'):
                    product.seo.delete() # Sadece SEO kaydını siler
                return JsonResponse({'status': 'success', 'message': 'SEO verileri silindi.'})
                
        except EtsyProduct.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Ürün bulunamadı veya size ait değil.'})

    return JsonResponse({'status': 'error', 'message': 'Geçersiz istek.'})


@csrf_exempt
@login_required(login_url='/login/')
def apply_mockups_action(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            design_ids = data.get('design_ids', []) # Seçili no_bg resim ID'leri
            group_id = data.get('group_id')
            
            # YENİ: Arayüzden kullanıcının "Zorla Yeniden Üret" deyip demediğini kontrol et
            force_recreate = data.get('force_recreate', False)

            if not product_id or not design_ids or not group_id:
                return JsonResponse({"status": "error", "message": "Eksik parametre (Ürün, Tasarım veya Grup seçilmedi)."}, status=400)

            group = MockupGroup.objects.get(id=group_id, user=request.user)
            # Koordinatı çizilmiş mockupları al
            mockup_items = group.items.filter(placement_data__isnull=False).exclude(placement_data={})

            if not mockup_items.exists():
                return JsonResponse({"status": "error", "message": "Seçilen grupta koordinatı belirlenmiş (mavi kutulu) mockup yok."}, status=400)

            output_urls = []
            cached_count = 0 # Kaç tanesinin klasörden geldiğini sayalım
            
            # Mockupların kaydedileceği klasörü hazırla
            output_dir = os.path.join(settings.MEDIA_ROOT, 'generated_mockups', str(product_id))
            os.makedirs(output_dir, exist_ok=True)

            # Seçilen her bir tasarım için, gruptaki tüm mockupları giydir
            for design_id in design_ids:
                var = DesignVariation.objects.get(id=design_id, product_id=product_id)
                design_path = var.no_bg_image.path

                for item in mockup_items:
                    file_name = f"mockup_{var.id}_{item.id}.png"
                    output_path = os.path.join(output_dir, file_name)
                    
                    # Frontend'e göstermek için URL'i oluştur
                    url = f"{settings.MEDIA_URL}generated_mockups/{product_id}/{file_name}"

                    # --- CACHE KONTROLÜ ---
                    # Eğer dosya klasörde ZATEN VARSA ve zorla yenileme istenmediyse:
                    if os.path.exists(output_path) and not force_recreate:
                        print(f"♻️ CACHE: {file_name} zaten mevcut, OpenCV atlandı.")
                        cached_count += 1
                        output_urls.append(url)
                    else:
                        # Eğer dosya YOKSA veya kullanıcı zorla yenile dediyse:
                        print(f"🚀 ÜRETİM: {file_name} OpenCV ile baştan oluşturuluyor...")
                        process_single_mockup(
                            mockup_path=item.mockup_image.path,
                            design_path=design_path,
                            coords=item.placement_data,
                            output_path=output_path
                        )
                        output_urls.append(url)

            # Eğer tüm sonuçlar Cache'den geldiyse frontend'i uyaralım (buton çıkartmak için)
            all_cached = (cached_count == len(design_ids) * mockup_items.count())

            return JsonResponse({
                "status": "success", 
                "mockups": output_urls,
                "cached": all_cached # Frontend'in haberi olsun
            })

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
            
    return JsonResponse({"status": "error", "message": "POST gerekli"}, status=405)


# ─────────────────────────────────────────────
# PIPELINE 2: MANUEL YÜKLEME VE TOPLU İŞLEM
# ─────────────────────────────────────────────

import os
from django.core.files.base import ContentFile

@csrf_exempt
@login_required(login_url='/login/')
def upload_manual_designs_action(request):
    """Kullanıcının bilgisayarından seçtiği resimleri topluca DB'ye kaydeder (Orijinal Dosya Adı kontrolü ile)."""
    if request.method == "POST":
        try:
            files = request.FILES.getlist('designs')
            group_name = request.POST.get('group_name', 'Adsız Yükleme Seti')

            if not files:
                return JsonResponse({"status": "error", "message": "Hiç dosya seçilmedi."}, status=400)

            upload_group = UploadGroup.objects.create(user=request.user, name=group_name)
            uploaded_items = []
            
            for file in files:
                # --- KESİN ÇÖZÜM: ORİJİNAL DOSYA ADI İLE CACHE KONTROLÜ ---
                # Kullanıcının daha önce yüklediği resimler içinde orijinal adı bu olan var mı?
                existing_upload = ManualUpload.objects.filter(
                    group__user=request.user,
                    original_filename=file.name # Django'nun değiştirdiği yola değil, bizim sabit metnimize bakıyor!
                ).first()

                if existing_upload:
                    # EĞER VARSA: Yeni dosya kaydetme, ESKİSİNİN ID'sini geri dön.
                    print(f"♻️ CACHE BAŞARILI: '{file.name}' zaten veritabanında var (ID: {existing_upload.id}). Eski kayıt kullanılıyor.")
                    
                    uploaded_items.append({
                        "id": existing_upload.id,
                        "url": existing_upload.image.url,
                        "name": file.name,
                        "cached": True
                    })
                    
                else:
                    # EĞER İLK DEFA YÜKLENİYORSA: Veritabanına kaydet ve orijinal adını da not et!
                    manual_upload = ManualUpload(
                        group=upload_group, 
                        image=file,
                        original_filename=file.name # Kullanıcının bilgisayarındaki dosya adını sabit olarak kaydediyoruz
                    )
                    manual_upload.save()
                    print(f"🆕 YENİ YÜKLEME: '{file.name}' başarıyla kaydedildi (ID: {manual_upload.id}).")
                    
                    uploaded_items.append({
                        "id": manual_upload.id,
                        "url": manual_upload.image.url,
                        "name": file.name,
                        "cached": False
                    })

            return JsonResponse({
                "status": "success", 
                "group_id": upload_group.id,
                "message": f"{len(files)} tasarım başarıyla işlendi.",
                "items": uploaded_items
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "POST gerekli"}, status=405)

@csrf_exempt
@login_required(login_url='/login/')
def process_batch_action(request):
    """Yüklenen resimleri döngüye sokup Vision AI, SEO ve Mockup uygular (Granular Cache ile)."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            upload_ids = data.get('upload_ids', [])
            do_seo = data.get('do_seo', False)
            do_mockup = data.get('do_mockup', False)
            mockup_group_id = data.get('mockup_group_id', None)
            
            # YENİ: Arayüzden gelen kullanıcı seçimi (Aksiyon Tipi)
            action_type = data.get('action_type', 'use_existing')

            if not upload_ids:
                return JsonResponse({"status": "error", "message": "İşlenecek tasarım seçilmedi."}, status=400)

            # API Key ve Ayarları Çek
            user_settings = UserSettings.objects.get(user=request.user)
            config_data = request.session.get('ai_config')
            if not config_data and user_settings.pipeline_config:
                config_data = {"api": {"key": user_settings.replicate_api_key}, "pipeline": user_settings.pipeline_config}

            api_key = config_data.get('api', {}).get('key') if config_data else None
            if not api_key:
                return JsonResponse({"status": "error", "message": "API anahtarı bulunamadı. Lütfen Config'i ayarlayın."}, status=400)

            ai_client = UniversalAIClient(api_key=api_key)
            seo_config = next((s for s in config_data.get('pipeline', []) if s['step'] == 'seo'), None) if config_data else None
            
            results = []

            # ── DÖNGÜ BAŞLIYOR (Toplu İşlem) ──
            for uid in upload_ids:
                item_result = {"id": uid, "status": "success", "seo": None, "mockup": None}
                
                try:
                    upload = ManualUpload.objects.get(id=uid, group__user=request.user)
                except ManualUpload.DoesNotExist:
                    print(f"⚠️ Hata: Upload ID {uid} bulunamadı.")
                    item_result["status"] = "error"
                    results.append(item_result)
                    continue

                # 1. SEO VE VİZYON AŞAMASI (Sinyal ve DB Kontrollü)
                if do_seo and seo_config:
                    try:
                        # Eğer force_seo veya force_all geldiyse, VISION ve SEO'yu ez geç (Zorla yenile)
                        should_recreate_seo = action_type in ['force_seo', 'force_all']
                        
                        # --- CACHE KONTROLÜ (SEO DB'DE VAR MI?) ---
                        if not should_recreate_seo and hasattr(upload, 'seo') and upload.seo and upload.seo.generated_title:
                            # KULLANICI MEVCUTLARI İSTEDİYSE VE DB'DE SEO VARSA: API'yi yorma, direkt DB'den al!
                            print(f"♻️ CACHE BAŞARILI: Upload {uid} için SEO verileri veritabanından alındı.")
                            item_result["seo"] = {
                                "title": upload.seo.generated_title, 
                                "tags": upload.seo.generated_tags
                            }
                            upload.status_seo = True
                            upload.save()
                            
                        else:
                            # --- SIFIRDAN ÜRETİM (VEYA YENİDEN ÜRETİM ZORLANDIYSA) ---
                            if should_recreate_seo:
                                print(f"🚀 ZORUNLU YENİLEME: Upload {uid} için SEO baştan üretiliyor.")
                                
                            if not upload.vision_analysis:
                                vision_user_prompt, vision_sys_prompt = PromptManager.get_prompt("gpt-4o-vision")
                                vision_raw = ai_client.execute(model_id="gpt-4o-vision", prompt=vision_user_prompt, system_prompt=vision_sys_prompt, file_path=upload.image.path)
                                if vision_raw:
                                    upload.vision_analysis = str(vision_raw)
                                    upload.save()

                            # Vision analizi var mı diye kontrol et, varsa SEO motorunu çağır
                            if upload.vision_analysis:
                                # DİKKAT: Hata veren 'force_recreate' parametresini sildik.
                                # Artık buraya sadece gerçekten üretilmesi gerektiğinde giriyoruz.
                                seo_record = generate_seo_for_product(
                                    ai_client=ai_client, 
                                    model_id=seo_config.get('model_id', 'gpt-4o'),
                                    title_system_prompt=seo_config.get('title_system_prompt', ''),
                                    tags_system_prompt=seo_config.get('tags_system_prompt', ''),
                                    target='both', 
                                    upload_id=upload.id
                                )
                                if seo_record:
                                    upload.status_seo = True
                                    upload.save()
                                    item_result["seo"] = {"title": seo_record.generated_title, "tags": seo_record.generated_tags}
                    except Exception as seo_err:
                        print(f"⚠️ Upload {uid} SEO Hatası: {seo_err}")
                        item_result["seo_error"] = str(seo_err)

                # 2. MOCKUP AŞAMASI (Sinyal Kontrollü)
                if do_mockup and mockup_group_id:
                    try:
                        output_dir = os.path.join(settings.MEDIA_ROOT, 'generated_mockups', 'manual', str(upload.id))
                        first_mockup_url = None
                        
                        # Eğer force_mockup veya force_all geldiyse, klasörü temizlemeliyiz (veya üzerine yazmalıyız)
                        should_recreate_mockup = action_type in ['force_mockup', 'force_all']
                        
                        # --- CACHE KONTROLÜ (Aksiyon Tipine Göre Karar Ver) ---
                        if os.path.exists(output_dir) and any(f.endswith('.png') for f in os.listdir(output_dir)) and not should_recreate_mockup:
                            # KULLANICI "MEVCUTLARI KULLAN" DEDİYSE VE KLASÖR DOLUYSA (Klasörden Oku)
                            print(f"♻️ CACHE BAŞARILI: Upload {uid} için mockuplar zaten klasörde mevcut, OpenCV atlandı.")
                            
                            for f in os.listdir(output_dir):
                                if f.endswith('.png'):
                                    first_mockup_url = f"{settings.MEDIA_URL}generated_mockups/manual/{upload.id}/{f}"
                                    break
                                    
                            upload.mockup_image_url = first_mockup_url
                            upload.status_mockup = True
                            upload.save()
                            item_result["mockup"] = first_mockup_url
                            
                        else:
                            # --- SIFIRDAN ÜRETİM (VEYA YENİDEN ÜRETİM ZORLANDIYSA) ---
                            if should_recreate_mockup:
                                print(f"🚀 ZORUNLU YENİLEME: Upload {uid} için Mockuplar baştan üretiliyor (Kullanıcı İsteği).")
                            
                            group = MockupGroup.objects.get(id=mockup_group_id, user=request.user)
                            mockup_items = group.items.filter(placement_data__isnull=False).exclude(placement_data={})
                            
                            if mockup_items.exists():
                                os.makedirs(output_dir, exist_ok=True)
                                
                                for item in mockup_items:
                                    file_name = f"mockup_man_{upload.id}_{item.id}.png"
                                    output_path = os.path.join(output_dir, file_name)
                                    process_single_mockup(mockup_path=item.mockup_image.path, design_path=upload.image.path, coords=item.placement_data, output_path=output_path)
                                    
                                    if not first_mockup_url: 
                                        first_mockup_url = f"{settings.MEDIA_URL}generated_mockups/manual/{upload.id}/{file_name}"

                                upload.mockup_image_url = first_mockup_url
                                upload.status_mockup = True
                                upload.save()
                                item_result["mockup"] = first_mockup_url
                    
                    except Exception as mockup_err:
                        print(f"⚠️ Upload {uid} Mockup Hatası: {mockup_err}")
                        item_result["mockup_error"] = str(mockup_err)

                # Döngü sonu, sonuçları listeye ekle
                results.append(item_result)

            return JsonResponse({"status": "success", "results": results})

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "POST gerekli"}, status=405)


@csrf_exempt
@login_required(login_url='/login/')
def export_batch_action(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            upload_ids = data.get('upload_ids', [])
            
            if not upload_ids:
                return JsonResponse({"status": "error", "message": "İndirilecek tasarım seçilmedi."}, status=400)
            
            # 1. Hafızada (RAM) Ana ZIP dosyasını oluşturuyoruz
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                
                # 2. Seçili her bir upload için döngüye gir
                for uid in upload_ids:
                    try:
                        upload = ManualUpload.objects.get(id=uid, group__user=request.user)
                        
                        folder_name = f"Design_{upload.id}"
                        if hasattr(upload, 'seo') and upload.seo and upload.seo.generated_title:
                            safe_title = slugify(upload.seo.generated_title)[:50] 
                            if safe_title:
                                folder_name = safe_title
                        
                        # A. ORİJİNAL TASARIMI ZIP'e EKLE (I/O Hatası Düzeltmesi)
                        if upload.image and upload.image.name:
                            try:
                                ext = os.path.splitext(upload.image.name)[1]
                                # .read() yerine Django'nun file objesinin kendisini veya path'ini kullanmak I/O hatasını önler.
                                # En güvenlisi, dosya yolunu alıp sıfırdan "rb" (read binary) modunda açmaktır.
                                with open(upload.image.path, 'rb') as f:
                                    zip_file.writestr(f"{folder_name}/Original_Design{ext}", f.read())
                            except Exception as img_err:
                                print(f"⚠️ Orijinal resim eklenemedi (ID: {uid}): {img_err}")
                        
                        # B. SEO BİLGİLERİNİ (TXT) ZIP'e EKLE
                        if hasattr(upload, 'seo') or upload.vision_analysis:
                            seo_content = f"--- AI DESIGN ANALYSIS & SEO ---\n\n"
                            
                            if upload.vision_analysis:
                                seo_content += f"VISION AI ANALYSIS:\n{upload.vision_analysis}\n\n"
                            
                            if hasattr(upload, 'seo') and upload.seo:
                                seo_content += f"TARGET TITLE:\n{upload.seo.generated_title}\n\n"
                                seo_content += f"TARGET TAGS:\n{upload.seo.generated_tags}\n\n"
                            
                            zip_file.writestr(f"{folder_name}/SEO_Data.txt", seo_content)
                        
                        # C. MOCKUPLARI ZIP'e EKLE (I/O Düzeltmesi ile)
                        mockups_dir = os.path.join(settings.MEDIA_ROOT, 'generated_mockups', 'manual', str(upload.id))
                        if os.path.exists(mockups_dir):
                            for idx, file_name in enumerate(os.listdir(mockups_dir)):
                                file_path = os.path.join(mockups_dir, file_name)
                                if os.path.isfile(file_path): # Alt klasör değil dosya olduğundan emin ol
                                    try:
                                        with open(file_path, 'rb') as f:
                                            mockup_ext = os.path.splitext(file_name)[1]
                                            zip_file.writestr(f"{folder_name}/Mockup_{idx+1}{mockup_ext}", f.read())
                                    except Exception as m_err:
                                         print(f"⚠️ Mockup eklenemedi: {file_path} - {m_err}")

                    except ManualUpload.DoesNotExist:
                        print(f"⚠️ Upload {uid} bulunamadı veya yetkisiz erişim.")
                        continue
                    except Exception as loop_err:
                        print(f"⚠️ Upload {uid} ZIP işleminde hata: {loop_err}")
                        continue
            
            # 3. ZIP dosyasını hazırlayıp tarayıcıya gönderiyoruz
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/zip')
            
            from datetime import datetime
            date_str = datetime.now().strftime("%Y%m%d_%H%M")
            response['Content-Disposition'] = f'attachment; filename="Etsy_Batch_Export_{date_str}.zip"'
            
            return response

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": f"ZIP Oluşturma Hatası: {str(e)}"}, status=500)
    
    return JsonResponse({"status": "error", "message": "POST gerekli"}, status=405)


@login_required(login_url='/login/')
def get_batch_mockups(request, upload_id):
    """
    Belirli bir Manual Upload ID'sine ait üretilmiş tüm mockupların URL'lerini döndürür.
    Javascript tarafında modal (galeri) açmak için kullanılır.
    """
    if request.method == "GET":
        try:
            # GÜVENLİK: Kullanıcı gerçekten bu resmin sahibi mi?
            upload = ManualUpload.objects.get(id=upload_id, group__user=request.user)
            
            # Mockupların bulunduğu klasör yolu
            mockups_dir = os.path.join(settings.MEDIA_ROOT, 'generated_mockups', 'manual', str(upload.id))
            
            mockup_urls = []
            
            if os.path.exists(mockups_dir):
                # Klasördeki tüm .png dosyalarını bul
                for file_name in os.listdir(mockups_dir):
                    if file_name.endswith('.png') or file_name.endswith('.jpg'):
                        # Medya URL'sini oluştur
                        url = f"{settings.MEDIA_URL}generated_mockups/manual/{upload.id}/{file_name}"
                        mockup_urls.append(url)
            
            return JsonResponse({
                "status": "success",
                "urls": mockup_urls,
                "message": f"{len(mockup_urls)} adet mockup bulundu."
            })
            
        except ManualUpload.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Bu tasarım bulunamadı veya yetkiniz yok."}, status=404)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Sadece GET istekleri desteklenir."}, status=405)