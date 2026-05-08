import json
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .utils import get_default_pipeline_defaults
from apps.common.services.encryption import encrypt_text

from apps.accounts.models import ApiCredential, PipelineConfig
from apps.ai.services.config.system_prompts import DEFAULT_SYSTEM_PROMPTS
from apps.ai.services.config.user_prompts import DEFAULT_USER_PROMPTS
from apps.common.services.db_helpers import DatabaseService

# ==========================================
# AUTH VE KAYIT
# ==========================================
def register_view(request):
    if request.user.is_authenticated:
        return redirect('ui:app_home')

    if request.method == 'POST':
        kullanici_adi = request.POST.get('username')
        sifre = request.POST.get('password')
        
        yeni_kullanici = User.objects.create_user(username=kullanici_adi, password=sifre)
        
        # KULLANICIYA VARSAYILAN AYARLARI YARDIMCI SERVİS İLE YAZ:
        DatabaseService.get_or_create_with_log(ApiCredential, user=yeni_kullanici)
        DatabaseService.get_or_create_with_log(
            PipelineConfig,
            user=yeni_kullanici,
            defaults=get_default_pipeline_defaults()
        )

        login(request, yeni_kullanici)
        return redirect('ui:app_home') 
        
    return render(request, 'pages/visitor/login_register/register.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('ui:app_home')

    if request.method == 'POST':
        kullanici_adi = request.POST.get('username')
        sifre = request.POST.get('password')

        user = authenticate(request, username=kullanici_adi, password=sifre)
        
        if user is not None:
            login(request, user)

            remember_me = request.POST.get('remember_me')
            if remember_me:
                request.session.set_expiry(1209600) # 2 hafta
            else:
                request.session.set_expiry(0) # Tarayıcı kapanınca çık
            
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)

            # AKILLI YÖNLENDİRME KONTROLÜ
            try:
                # user.pipeline_config modelimizdeki dynamic_config dolu mu diye bakıyoruz
                has_config = hasattr(user, 'pipeline_config') and bool(user.pipeline_config.dynamic_config)
            except:
                has_config = False 
                
            if not has_config:
                # return redirect('ui:settings_pipeline') # Config tamamlanınca burayı açarsın
                return redirect('ui:app_home')
            else:
                return redirect('ui:app_home')

        else:
            messages.error(request, "Kullanıcı adı veya şifre hatalı!")
            return redirect('accounts:login') 

    return render(request, 'pages/visitor/login_register/login.html')

def logout_action(request):
    logout(request)
    return redirect('accounts:login') 

# ==========================================
# API: AYARLARI KAYDETME 
# ==========================================
@csrf_exempt
@login_required(login_url='/accounts/login/')
def save_config_action(request):
    """Arayüzden gelen veriyi veritabanındaki modele kaydeder."""
    if request.method == "POST":
        try:
            config_data = json.loads(request.body)
            
            # 1. API Key Kaydı / Şifrelemesi
            api_key = config_data['api']['key']
            if api_key and not api_key.endswith('********'):
                encrypted_key = encrypt_text(api_key)
                DatabaseService.update_or_create_with_log(
                    ApiCredential,
                    user=request.user,
                    defaults={'replicate_key': encrypted_key}
                )

            # 2. Pipeline Ayarları Kaydı (DÜZ VE TERTEMİZ)
            pipeline_data = config_data['pipeline']
            
            DatabaseService.update_or_create_with_log(
                PipelineConfig,
                user=request.user,
                defaults=pipeline_data  # Gelen sözlük direkt modele uyduğu için tek satır yeterli!
            )
            
            return JsonResponse({"status": "success", "message": "Konfigürasyon başarıyla kaydedildi!"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "error", "message": "POST gerekli"}, status=405)