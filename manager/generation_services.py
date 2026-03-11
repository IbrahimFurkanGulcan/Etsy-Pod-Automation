import os
import requests
import replicate
from django.core.files.base import ContentFile
from .models import DesignVariation

# =====================================================================
# 1. SINIF: MODEL REGISTRY (DataStore)
# Tüm AI modellerinin kimlik kartlarının (Endpoint, Format vb.) tutulduğu yer.
# =====================================================================
class ModelRegistry:
    MODELS = {
        # --- GÖRSEL ÜRETİM MODELLERİ ---
        "nano-banana": {
            "platform": "replicate",
            "endpoint": "google/nano-banana",
            "schema": {
                "prompt_key": "prompt",
                "image_key": "image_input", # Nano banana böyle istiyor
                "image_is_list": True,      # List [] formatında istiyor
                "output_type": "url"        # Tek URL döner
            },
            "default_params": { "aspect_ratio": "1:1", "output_format": "png" }
        },
        "seedream-4.5": {
            "platform": "replicate",
            "endpoint": "bytedance/seedream-4.5",
            "schema": {
                "prompt_key": "prompt",
                "image_key": "image_input",          # Resim girdisi almıyor
                "image_is_list": True,
                "output_type": "url_list"   # Liste döner!
            },
            "default_params": { "size": "2K", "max_images": 1, "sequential_image_generation": "disabled", "aspect_ratio": "1:1", "width": 2048, "height": 2048, }
        },
        "flux-2-pro": {
            "platform": "replicate",
            "endpoint": "black-forest-labs/flux-2-pro",
            "schema": {
                "prompt_key": "prompt",
                "image_key": "input_images",
                "image_is_list": True,
                "output_type": "url"
            },
            "default_params": { "output_quality": 80, "resolution": "1 MP", "aspect_ratio": "1:1", "output_format": "png", "safety_tolerance": 2}
        },


        # --- UPSCALE MODELLERİ ---
        "recraft-crisp": {
            "platform": "replicate",
            "endpoint": "recraft-ai/recraft-crisp-upscale",
            "schema": {
                "prompt_key": None,         # Prompt almaz
                "image_key": "image",
                "image_is_list": False,
                "output_type": "url"
            },
            "default_params": {}
        },

        # --- İŞLEME VE TESPİT MODELLERİ ---
        "grounding-dino": {
            "platform": "replicate",
            "endpoint": "adirik/grounding-dino:efd10a8ddc57...",
            "schema": {
                "prompt_key": "query",      # Dino prompt'a "query" diyor
                "image_key": "image",
                "image_is_list": False,
                "output_type": "json"       # JSON Koordinat döner
            },
            "default_params": { "box_threshold": 0.2, "text_threshold": 0.2 }
        },
        "bria-rmbg": {
            "platform": "replicate",
            "endpoint": "bria/remove-background",
            "schema": {
                "prompt_key": None,
                "image_key": "image",
                "image_is_list": False,
                "output_type": "url"
            },
            "default_params": { "preserve_alpha": True,"content_moderation": False, "preserve_partial_alpha": True }
        },

        # --- METİN / LLM MODELLERİ ---
        "gpt-4o": {
            "platform": "replicate", # Replicate üzerinden çağrılan GPT
            "endpoint": "openai/gpt-4o",
            "schema": {
                "prompt_key": "prompt",
                "system_prompt_key": "system_prompt",
                "image_key": None,
                "output_type": "stream"     # Akış döner
            },
            "default_params": { "temperature": 0.5, "max_completion_tokens": 512 }
        }
    }

    @classmethod
    def get(cls, model_id):
        return cls.MODELS.get(model_id)


# =====================================================================
# 2. SINIF: PROMPT MANAGER
# Modeller için varsayılan sistem istemlerinin tutulduğu kütüphane.
# =====================================================================
# =====================================================================
# 2. SINIF: PROMPT MANAGER
# Modeller için varsayılan sistem ve kullanıcı istemlerinin kütüphanesi.
# =====================================================================
class PromptManager:
    # 1. STANDART KULLANICI PROMPTLARI (User Prompts)
    DEFAULT_PROMPTS = {
        # --- GÖRSEL ÜRETİM ---
        "flux-2-pro": "vector graphic design of the image, isolated on white background, clean lines, professional illustration style, flat colors, just design",
        "seedream-4.5": "vector graphic design of the image, isolated on white background, clean lines, professional illustration style, flat colors, just design",
        "nano-banana": "vector graphic design of the image, isolated on white background, clean lines, professional illustration style, flat colors, just design",
        
        # --- TESPİT (DETECTION) ---
        "grounding-dino": "printed graphic design",
        
        # --- SEO (LLM) ---
        "gpt-4o": "Original Listing Title: '{title}'\nOriginal Tags: '{tags}'\n\nBased on these details, generate the SEO data for a new '{niche}' design following all the system prompt rules."
        
        # Not: Upscale ve BG Removal modelleri prompt kullanmadığı için buraya eklenmedi.
    }

    # 2. SİSTEM PROMPTLARI (System Prompts - Sadece LLM'ler için)
    DEFAULT_SYSTEM_PROMPTS = {
        "gpt-4o": """You are an expert e-commerce and Etsy SEO consultant. Your objective is to maximize search visibility based on the provided original listing data.

Strictly adhere to the following rules:

[TITLE RULES]
- Maximum 140 characters in total.
- Maximum 14 words in total.
- Do not repeat any words in the title.
- Strictly avoid subjective, emotional, or promotional adjectives (e.g., "funny", "cute", "beautiful", "amazing", "great"). Be purely objective and descriptive.

[TAGS RULES]
- Generate exactly 13 tags.
- Each tag MUST be descriptive of the design.
- Each tag MUST NOT exceed 20 characters (including spaces).
- Prioritize multi-word phrases over single words to maximize keyword diversity within the 20-character limit (e.g., instead of using "mother", "cat", and "sassy" as three separate tags, combine them into one tag like "sassy cat mum").
- Separate the 13 tags with commas in the JSON output.

[OUTPUT FORMAT]
- You must return ONLY a valid JSON object. Do not include markdown formatting (like ```json), explanations, warnings, or conversational text.
- The JSON structure must be exactly:
{"new_title": "...", "new_tags": "tag1, tag2, tag3...", "focus_keyword": "..."}
"""
    }

    @classmethod
    def get_prompt(cls, model_id, custom_prompt=None):
        """
        Geriye (prompt, system_prompt) şeklinde ikili (tuple) döner.
        Kullanıcı arayüzden prompt girdiyse onu, girmediyse varsayılanı kullanır.
        """
        # Kullanıcı arayüzde bir şeyler yazdıysa onu al, yazmadıysa Default'u getir
        prompt = custom_prompt if custom_prompt and custom_prompt.strip() else cls.DEFAULT_PROMPTS.get(model_id, "")
        
        # Sistem promptları kullanıcının değiştirmemesi gereken katı kurallardır, o yüzden hep Default'tan çekilir
        system_prompt = cls.DEFAULT_SYSTEM_PROMPTS.get(model_id, None)

        return prompt, system_prompt

# =====================================================================
# 3. SINIF: UNIVERSAL AI CLIENT (Ana Motor)
# Platform bağımsız, dinamik API istekleri atan ve terminal loglarını tutan sınıf.
# =====================================================================
class UniversalAIClient:
    def __init__(self, api_key, platform="replicate"):
        self.platform = platform
        if self.platform == "replicate":
            self.client = replicate.Client(api_token=api_key)

    def execute(self, model_id, prompt=None, system_prompt=None, file_path=None, custom_params=None):
        """
        Tüm AI isteklerinin geçtiği tek evrensel fonksiyon.
        Artık tamamen ModelRegistry şemasına göre hareket eder.
        """
        
        config = ModelRegistry.get(model_id)
        if not config:
            raise ValueError(f"Model '{model_id}' bulunamadı!")

        schema = config["schema"]
        payload = config["default_params"].copy()
        
        if custom_params:
            payload.update(custom_params)

        # 1. Promptları Yerleştir
        if prompt and schema.get("prompt_key"):
            payload[schema["prompt_key"]] = prompt
        
        if system_prompt and schema.get("system_prompt_key"):
            payload[schema["system_prompt_key"]] = system_prompt

        file_obj = None
        try:
            # 2. Dosya Yönetimi (Şemaya göre dinamik paketleme)
            if file_path and os.path.exists(file_path) and schema.get("image_key"):
                file_obj = open(file_path, "rb")
                
                # Eğer model resmi [file] şeklinde liste olarak bekliyorsa (Seedream, Flux vb.)
                if schema.get("image_is_list"):
                    payload[schema["image_key"]] = [file_obj]
                else:
                    payload[schema["image_key"]] = file_obj

            # 3. API'yi Tetikle
            print(f"🚀 Çalışıyor: {config['endpoint']} (Model: {model_id})")
            
            # self.client senin Replicate client nesnen ise onu kullan, değilse direkt replicate.run
            if schema.get("output_type") == "stream":
                events = replicate.stream(config["endpoint"], input=payload)
                result = "".join([str(event) for event in events])
            else:
                result = replicate.run(config["endpoint"], input=payload)

            # 4. Çıktıyı Çözümle
            # NOT: Bir önceki hatada gördüğümüz liste gelme durumunu burada _parse_output içinde hallediyoruz.
            parsed_output = self._parse_output(result, schema["output_type"])
            return parsed_output

        except Exception as e:
            print(f"❌ Motor Hatası ({model_id}): {e}")
            return None
            
        finally:
            if file_obj and not file_obj.closed:
                file_obj.close()

    def _parse_output(self, raw_output, output_type):
        """Modelin cinsine göre çıktıyı standartlaştırır."""
        if output_type == "url":
            # Tekil URL (Nano-banana, flux)
            if hasattr(raw_output, 'url'): return raw_output.url
            if isinstance(raw_output, list): return raw_output[0].url if hasattr(raw_output[0], 'url') else str(raw_output[0])
            return str(raw_output)
            
        elif output_type == "url_list":
            # Liste URL (Seedream)
            return [item.url if hasattr(item, 'url') else str(item) for item in raw_output]
            
        elif output_type == "json":
            # Sözlük / JSON (Dino)
            return raw_output
            
        elif output_type == "stream":
            # Metin (LLM)
            return str(raw_output)
        
        return raw_output