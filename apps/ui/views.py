from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.accounts.models import UserProfile
from apps.accounts.models import ApiCredential, PipelineConfig
from apps.accounts.utils import get_default_pipeline_defaults
from apps.common.services.db_helpers import DatabaseService
from apps.common.services.encryption import decrypt_text
from apps.ai.services.config.system_prompts import DEFAULT_SYSTEM_PROMPTS
from apps.ai.services.config.user_prompts import DEFAULT_USER_PROMPTS
import json


def landing_view(request):
    return render(request, 'pages/visitor/landing.html')

# ==========================================
#  UYGULAMA İÇİ EKRANLAR (Sadece Giriş Yapanlar)
# ==========================================
@login_required(login_url='/login/')
def app_home_view(request):
    return render(request, 'pages/app/home.html')

@login_required(login_url='/login/')
def tshirt_category_view(request):
    return render(request, 'pages/app/category_tshirt.html')

@login_required(login_url='/login/')
def tshirt_pipeline1_view(request):
    return render(request, 'pipelines/tshirt_pipeline1.html')

@login_required(login_url='/login/')
def tshirt_pipeline2_view(request):
    return render(request, 'pipelines/tshirt_pipeline2.html')

@login_required(login_url='/login/')
def tshirt_history_view(request):
    return render(request, 'pages/app/settings/history/tshirt_history.html')

@login_required(login_url='/login/')
def settings_hub_view(request):
    """Genişletilmiş Ayarlar ve Yönetim Merkezi (Hub)"""
    return render(request, 'pages/app/settings/settings_home.html')

@login_required(login_url='/login/')
def asset_library_view(request):
    """Tüm Tasarımların Yönetildiği Kütüphane Ekranı"""
    return render(request, 'pages/app/settings/asset_library.html')

@login_required(login_url='/accounts/login/')
def settings_pipeline_view(request):
    api_creds, _ = DatabaseService.get_or_create_with_log(ApiCredential, user=request.user)

    decrypted_key = decrypt_text(api_creds.replicate_key) if api_creds.replicate_key else ""
    masked_key = f"{decrypted_key[:3]}********" if decrypted_key else ""
    
    pipeline_conf, _ = DatabaseService.get_or_create_with_log(
        PipelineConfig, 
        user=request.user,
        defaults=get_default_pipeline_defaults()
    )

    # O "Hardcoded" Uzun Listeyi Dinamik Döngüye Çevirdik
    generation_models = []
    for i in range(1, 4):
        model_id = getattr(pipeline_conf, f'gen_model_{i}_id')
        generation_models.append({
            "dom_id": i, 
            "id": model_id, 
            "name": model_id.replace('-', ' ').title(), 
            "enabled": getattr(pipeline_conf, f'gen_model_{i}_enabled'), 
            "prompt": getattr(pipeline_conf, f'gen_model_{i}_prompt')
        })

    pipeline_ui_data = {
        "detection": {"enabled": pipeline_conf.enable_detection, "model_id": pipeline_conf.detection_model, "prompt": pipeline_conf.detection_prompt},
        "generation": {"enabled": pipeline_conf.enable_generation, "models": generation_models},
        "upscale": {"enabled": pipeline_conf.enable_upscale, "model_id": pipeline_conf.upscale_model},
        "bg_removal": {"enabled": pipeline_conf.enable_bg_removal, "model_id": pipeline_conf.bg_removal_model},
        "vision": {"enabled": pipeline_conf.enable_vision, "model_id": pipeline_conf.vision_model, "system_prompt": pipeline_conf.vision_system_prompt, "user_prompt": pipeline_conf.vision_user_prompt},
        "seo": {"enabled": pipeline_conf.enable_seo, "model_id": pipeline_conf.seo_model, "title_system_prompt": pipeline_conf.seo_title_system_prompt, "tags_system_prompt": pipeline_conf.seo_tags_system_prompt, "user_prompt": pipeline_conf.seo_user_prompt}
    }

    context = {
        "saved_api_key": masked_key,
        "pipeline_data": pipeline_ui_data,
        "default_prompts_json": json.dumps(get_default_pipeline_defaults()),
    }
    return render(request, 'pages/app/settings/config.html', context)

