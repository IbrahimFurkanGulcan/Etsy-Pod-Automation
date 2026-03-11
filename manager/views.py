import re
import io
import zipfile
import os
import json
import requests
import traceback
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from .scraper import scrape_etsy_product
from .models import EtsyProduct, DesignVariation, UserSettings, SeoOptimization
from .detect_crop import crop_and_save_product_design
from .generation_services import UniversalAIClient, PromptManager, ModelRegistry
from concurrent.futures import ThreadPoolExecutor, as_completed
from .seo_service import generate_seo_for_product



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
    # 🚀 YENİ EKLENEN KISIM: Veri temizleme (Double Encoding Koruması)
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
                "system_prompt": PromptManager.get_prompt("gpt-4o")[1]
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
def dashboard(request):
    # DİKKAT: Artık .all() kullanmıyoruz! Sadece o an giriş yapmış olan kullanıcının (.filter(user=request.user)) ürünlerini çekiyoruz.
    recent_products = EtsyProduct.objects.filter(user=request.user).order_by('-id')[:5]
    
    return render(request, 'manager/dashboard.html', {'recent_products': recent_products})



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
                    
                    # YENİ EKLENEN KISIM: Eğer sonuç bir Liste (Array) ise, ilk elemanını al!
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
            # 5. YENİ SONUÇLARI ARAYÜZE GÖNDERME
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
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            force_recreate = data.get('force_recreate', False)

            if not product_id:
                return JsonResponse({"status": "error", "message": "Ürün ID eksik."}, status=400)

            # Ürünün kullanıcıya ait olduğundan emin oluyoruz (Güvenlik)
            product = EtsyProduct.objects.get(id=product_id, user=request.user)

            # ========================================================
            # 1. KATI HAFIZA (CACHE) KONTROLÜ
            # ========================================================
            if not force_recreate:
                if hasattr(product, 'seo') and product.seo.generated_title:
                    print(f"⚡ [ID: {product.id}] SEO verileri DB'den anında çekildi!")
                    return JsonResponse({
                        "status": "success",
                        "title": product.seo.generated_title,
                        "tags": product.seo.generated_tags,
                        "cached": True
                    })

            # ========================================================
            # 2. KULLANICI AYARLARINI VE ÖZEL PROMPTLARI ÇEK
            # ========================================================
            user_settings = UserSettings.objects.get(user=request.user)
            config_data = request.session.get('ai_config')

            if not config_data and user_settings.pipeline_config:
                config_data = {
                    "api": {"key": user_settings.replicate_api_key},
                    "pipeline": user_settings.pipeline_config
                }
            
            if not config_data:
                return JsonResponse({"status": "error", "message": "Ayarlar bulunamadı. Lütfen önce Config sayfasını kaydedin."}, status=400)

            # Pipeline içinden SEO adımını bul
            seo_config = next((s for s in config_data.get('pipeline', []) if s['step'] == 'seo'), None)
            
            if not seo_config:
                return JsonResponse({"status": "error", "message": "SEO modülü aktif değil!"}, status=400)

            # ========================================================
            # 3. DİNAMİK PROMPT HAZIRLAMA (Placeholder Değişimi)
            # ========================================================
            # Kullanıcının Config sayfasında yazdığı taslakları alıyoruz
            raw_user_prompt = seo_config.get('prompt', '')
            system_prompt = seo_config.get('system_prompt', 'You are an Etsy SEO expert.')

            # {title}, {tags} gibi yer tutucuları gerçek ürün verileriyle dolduruyoruz
            final_user_prompt = raw_user_prompt.replace('{title}', product.title or "")
            final_user_prompt = final_user_prompt.replace('{tags}', product.tags or "")
            final_user_prompt = final_user_prompt.replace('{niche}', "Graphic T-Shirt") # İleride bunu da dinamik yapabiliriz

            # ========================================================
            # 4. EVRENSEL MOTOR İLE GPT-4o ATEŞLEME
            # ========================================================
            print(f"🧠 GPT-4o Tetikleniyor... [ID: {product.id}]")
            
            # API Key'i kullanıcıdan alıyoruz (SaaS Mimarisi)
            ai_client = UniversalAIClient(api_key=config_data['api']['key'])
            
            # Motor üzerinden isteği atıyoruz
            llm_response = ai_client.execute(
                model_id="gpt-4o", 
                prompt=final_user_prompt, 
                system_prompt=system_prompt
            )

            if not llm_response:
                raise ValueError("LLM'den yanıt alınamadı.")

            # ========================================================
            # 5. ÇIKTIYI ÇÖZÜMLE VE KAYDET
            # ========================================================
            # LLM'den genellikle JSON formatında bir metin bekliyoruz
            try:
                # Eğer yanıt string ise JSON'a çevir, zaten dict ise direkt kullan
                import json as json_lib
                seo_data = json_lib.loads(llm_response) if isinstance(llm_response, str) else llm_response
                
                new_title = seo_data.get('title', product.title)
                new_tags = seo_data.get('tags', product.tags)
                
                # Listeyi string'e çevirme (Eğer tags liste geldiyse)
                if isinstance(new_tags, list):
                    new_tags = ", ".join(new_tags)

                # Veritabanına kaydet veya güncelle (OneToOneField avantajı)
                from .models import SeoOptimization
                seo_record, created = SeoOptimization.objects.update_or_create(
                    product=product,
                    defaults={
                        'generated_title': new_title,
                        'generated_tags': new_tags
                    }
                )

                print(f"✅ SEO Başarıyla Kaydedildi: {product.id}")
                return JsonResponse({
                    "status": "success",
                    "title": seo_record.generated_title,
                    "tags": seo_record.generated_tags,
                    "cached": False
                })

            except Exception as parse_error:
                print(f"❌ JSON Ayrıştırma Hatası: {parse_error}\nYanıt: {llm_response}")
                return JsonResponse({"status": "error", "message": "Yapay zeka yanıtı anlaşılamadı (JSON formatı hatası)."}, status=500)

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "POST gerekli"}, status=405)


@csrf_exempt
@login_required(login_url='/login/') # 1. GÜVENLİK: Giriş yapmayan indiremez
def export_project_action(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            
            if not product_id:
                return JsonResponse({"status": "error", "message": "Ürün ID eksik."}, status=400)
            
            # 2. GÜVENLİK: Sadece o anki kullanıcıya ait ürünü çekiyoruz
            # Bu sayede ID tahmini ile başkasının verisine ulaşılamaz.
            product = EtsyProduct.objects.get(id=product_id, user=request.user)
            
            # 1. Hafızada (RAM) sanal bir ZIP dosyası oluşturuyoruz
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
            
            # 5. ZIP dosyasını hazırlayıp tarayıcıya gönderiyoruz
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