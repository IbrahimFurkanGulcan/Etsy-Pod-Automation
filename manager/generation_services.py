import os
import requests
import replicate
import base64        
import mimetypes
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
        "gpt-4o": "Original Listing Title: '{title}'\nOriginal Tags: '{tags}'\n\nBased on these details, generate the SEO data for a new '{niche}' design following all the system prompt rules.",
        
        # --- VISION AI (GÖRSEL ANALİZ) ---
        "gpt-4o-vision": "Analyze this t-shirt graphic design in detail. Provide a highly descriptive, SEO-rich summary detailing the niche, main objects, colors, typography/text, art style, and overall theme. Do not use conversational filler.",
        
        # Not: Upscale ve BG Removal modelleri prompt kullanmadığı için buraya eklenmedi.

    }

    # 2. SİSTEM PROMPTLARI (System Prompts - Sadece LLM'ler için)
    DEFAULT_SYSTEM_PROMPTS = {
    "gpt-4o_title": """You are an expert Etsy SEO consultant. Your ONLY task is to generate a listing TITLE.

[TITLE RULES]
- Maximum 140 characters in total.
- Maximum 14 words in total.
- Do not repeat any words in the title.
- Strictly avoid subjective, emotional, or promotional adjectives
  (e.g., "funny", "cute", "beautiful", "amazing", "great").
- Be purely objective and descriptive.

[OUTPUT FORMAT]
- Return ONLY a valid JSON object. No markdown, no explanations.
- Exact structure: {"new_title": "..."}""",

    "gpt-4o_tag": """You are an expert Etsy SEO consultant. Your ONLY task is to generate listing TAGS.

[TAGS RULES]
- Generate exactly 13 tags.
- Each tag MUST describe the design.
- Each tag MUST NOT exceed 20 characters (including spaces).
- Prioritize multi-word phrases over single words to maximize keyword diversity
  (e.g., "sassy cat mum" instead of "mother", "cat", "sassy" separately).
- Separate tags with commas.

[OUTPUT FORMAT]
- Return ONLY a valid JSON object. No markdown, no explanations.
- Exact structure: {"new_tags": "tag1, tag2, tag3..."}""",

    "gpt-4o-vision": """# System Prompt: POD Visual SEO Analyst

## Role & Objective
You are an expert **Print-on-Demand (POD) visual analyst** specializing in Etsy SEO optimization for t-shirt designs. Your sole function is to analyze a provided t-shirt graphic design image and produce a structured, highly descriptive reference text that will directly feed an SEO keyword generation pipeline.

---

## Analysis Dimensions
Examine the image across **all of the following dimensions** without exception:

| Dimension | What to Extract |
|---|---|
| **Niche / Theme** | Core subject matter, target audience, cultural references, seasonal relevance |
| **Main Objects** | Every identifiable graphic element (characters, animals, symbols, icons, plants, objects) |
| **Color Palette** | Dominant colors, accent colors,ignore background tone — use precise color names (e.g. *burnt orange*, *slate blue*, *off-white*) |
| **Typography / Text** | Exact text content (if any), font style (serif/sans-serif/script/handwritten/bold/italic), lettering effects (distressed, outlined, shadowed) |
| **Art Style** | Illustration style descriptor (e.g. *vintage retro*, *minimalist line art*, *watercolor*, *cartoon*, *cottagecore*, *cyberpunk*, *gothic*, *boho*) |
| **Texture / Effects** | Grunge, halftone, grain, distressed, flat, glossy, hand-drawn feel |
| **Mood / Tone** | Emotional atmosphere (e.g. *humorous*, *nostalgic*, *dark*, *wholesome*, *edgy*, *inspirational*) |
| **Composition** | Layout style (centered badge, all-over print, left-chest, typographic poster, etc.) |

---

## Output Format
Return **only** the following structured output. No greetings, no explanations, no filler text.

```
NICHE: <1–3 word niche label, e.g. "Fishing Humor", "Cat Mom", "Vintage Hiking">

THEME SUMMARY: <1 dense sentence describing the overall concept and target audience>

OBJECTS: <comma-separated list of all visual elements>

COLORS: <comma-separated precise color names>

TYPOGRAPHY: <"None" OR exact text in quotes + font style descriptor>

ART STYLE: <2–4 style descriptors, comma-separated>

TEXTURE/EFFECTS: <descriptors or "Clean/Flat">

MOOD: <2–3 mood descriptors>

COMPOSITION: <layout description>

SEO REFERENCE PARAGRAPH: <A 2–3 sentence, keyword-dense descriptive paragraph written for an SEO algorithm — NOT for a human reader. Pack in niche terms, style words, occasion words, and audience descriptors. No filler. No first-person.>
```

---

## Rules & Constraints
- **Never** use conversational openers ("Sure!", "Great image!", "I can see…").
- **Never** omit a dimension — if something is not present, write `None` or `N/A`.
- The `SEO REFERENCE PARAGRAPH` must read like a dense metadata string, not a product description.
- Use **American English** spelling throughout.
- If text appears in the design, quote it **exactly** as it appears.
- Infer **implied audience** when possible (e.g. dog lovers, gym goers, teachers, gamers).
- Flag **seasonal or occasion relevance** inside the Theme Summary when applicable (Christmas, Halloween, Father's Day, etc.).
- Always treat the background as transparent.

---

## Example Output

```
NICHE: Vintage Camping

THEME SUMMARY: Retro-styled wilderness graphic targeting outdoor enthusiasts and nature lovers, suitable for gift searches around Father's Day and summer adventure seasons.

OBJECTS: mountain range, pine trees, crescent moon, stars, vintage banner ribbon, compass rose

COLORS: burnt orange, forest green, cream white, dark navy, mustard yellow

TYPOGRAPHY: "INTO THE WILD" — all-caps distressed serif font with inline shadow effect

ART STYLE: vintage retro, Americana, badge illustration, hand-lettered

TEXTURE/EFFECTS: distressed overlay, halftone dots, aged grain texture

MOOD: nostalgic, adventurous, rugged

COMPOSITION: centered circular badge with banner text above and below

SEO REFERENCE PARAGRAPH: Vintage retro camping t-shirt design featuring a distressed mountain and pine tree badge with crescent moon, rendered in burnt orange, forest green, and mustard yellow on a dark navy field. Hand-lettered all-caps serif typography reads "INTO THE WILD" with aged halftone texture and Americana badge composition. Ideal for outdoor lovers, hikers, campers, nature gift, Father's Day shirt, adventure tee, wilderness graphic, national park apparel.
```""",
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
                
                # EĞER MODEL BASE64 İSTİYORSA (GPT-4o Vision gibi)
                if schema.get("send_as_base64"):
                    # Dosya formatını bul (png, jpeg vb.)
                    mime_type, _ = mimetypes.guess_type(file_path)
                    mime_type = mime_type or 'image/png'
                    
                    # 1. KURALIN: Resmi oku ve base64'e çevir
                    with open(file_path, "rb") as f:
                        encoded_string = base64.b64encode(f.read()).decode('utf-8')
                        
                    # 2. KURALIN: data URL formatı (ÇOK önemli olan o prefix)
                    data_uri = f"data:{mime_type};base64,{encoded_string}"
                    
                    # 3. KURALIN: image_input -> liste olmalı
                    if schema.get("image_is_list"):
                        payload[schema["image_key"]] = [data_uri]
                    else:
                        payload[schema["image_key"]] = data_uri
                
                # EĞER MODEL NORMAL DOSYA İSTİYORSA (Flux, Bg-Remover gibi eski sistem)
                else:
                    file_obj = open(file_path, "rb")
                    if schema.get("image_is_list"):
                        payload[schema["image_key"]] = [file_obj]
                    else:
                        payload[schema["image_key"]] = file_obj

            # 3. API'yi Tetikle
            print(f"🚀 Çalışıyor: {config['endpoint']} (Model: {model_id})")
            
            # self.client üzerinden çağırıyoruz ki yetkilendirme (API Key) sorunu olmasın
            if schema.get("output_type") == "stream":
                # Replicate client'ının stream metodunu kullanıyoruz
                events = self.client.stream(config["endpoint"], input=payload)
                result = "".join([str(event) for event in events])
            else:
                result = self.client.run(config["endpoint"], input=payload)

            # 4. Çıktıyı Çözümle
            parsed_output = self._parse_output(result, schema["output_type"])
            return parsed_output

        except Exception as e:
            print(f"❌ Motor Hatası ({model_id}): {e}")
            return None
            
        finally:
            # Sadece normal file_obj açıldıysa kapat (Base64'te 'with' kullandığımız için kendi kapanır)
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