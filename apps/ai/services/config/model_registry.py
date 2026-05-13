# =====================================================================
# MODEL REGISTRY (DataStore)
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
            "default_params": { "size": "2K", "max_images": 1, "sequential_image_generation": "disabled", "aspect_ratio": "1:1" }
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
            "endpoint": "adirik/grounding-dino:efd10a8ddc57ea28773327e881ce95e20cc1d734c589f7dd01d2036921ed78aa",
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
        },

        # --- VİZYON / GÖRSEL ANALİZ MODELLERİ ---
        "gpt-4o-vision": {
            "platform": "replicate",
            "endpoint": "openai/gpt-4o", # Replicate'te gpt-4o görsel destekler
            "schema": {
                "prompt_key": "prompt",
                "system_prompt_key": "system_prompt",
                "image_key": "image_input",        # Evrensel motorumuz bu key'i görünce resmi gönderecek!
                "image_is_list": True,
                "output_type": "stream",                
            },
            "default_params": { "temperature": 0.3, "max_tokens": 512 } # Analiz için temperature düşük tutuldu
        },
    }

    @classmethod
    def get(cls, model_id):
        return cls.MODELS.get(model_id)