import os
import json
import replicate
from .models import EtsyProduct, SeoOptimization
from dotenv import load_dotenv

load_dotenv()

def generate_seo_for_product(product_id, niche="Graphic T-Shirt"):
    """
    EtsyProduct verilerini alarak Replicate (GPT-4o) üzerinden yeni SEO verileri üretir
    ve SeoOptimization tablosuna kaydeder.
    """
    print(f"\n🔍 SEO Üretimi Başlatılıyor... (Ürün ID: {product_id})")

    try:
        product = EtsyProduct.objects.get(id=product_id)
    except EtsyProduct.DoesNotExist:
        print("❌ Hata: Ürün veritabanında bulunamadı.")
        return None

    original_title = product.title or "Belirtilmemiş"
    original_tags = product.tags or "Belirtilmemiş"

    print(f"📦 Referans Alınan Başlık: {original_title[:50]}...")
    
    # 1. GPT-4o MODELİNİ ÇAĞIR
    ai_response = _call_gpt4o_for_seo(original_title, original_tags, niche)

    if not ai_response:
        print("⚠️ AI'dan geçerli bir SEO verisi alınamadı.")
        return None

    # 2. VERİTABANINA KAYDET / GÜNCELLE
    try:
        seo_record, created = SeoOptimization.objects.update_or_create(
            product=product,
            defaults={
                'generated_title': ai_response.get('new_title', ''),
                'generated_tags': ai_response.get('new_tags', ''),
                'target_keywords': ai_response.get('focus_keyword', '')
            }
        )
        
        islem_tipi = "Oluşturuldu" if created else "Güncellendi"
        print(f"💾 SEO Verileri Başarıyla Kaydedildi ({islem_tipi})")
        return seo_record

    except Exception as e:
        print(f"❌ Veritabanı Kayıt Hatası: {e}")
        return None

def _call_gpt4o_for_seo(title, tags, niche):
    """
    Replicate üzerinden OpenAI GPT-4o modeline prompt gönderir ve JSON yanıtı ayrıştırır.
    """
    print("🧠 GPT-4o API'sine bağlanılıyor...")

    # İngilizce dilinde, katı kurallarla yazılmış System Prompt
    system_prompt = """
You are an expert e-commerce and Etsy SEO consultant. Your objective is to maximize search visibility based on the provided original listing data.

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
    
    prompt = f"""
Original Listing Title: '{title}'
Original Tags: '{tags}'

Based on these details, generate the SEO data for a new '{niche}' design following all the system prompt rules.
"""

    try:
        # Replicate OpenAI GPT-4o endpoint
        output = replicate.run(
            "openai/gpt-4o",
            input={
                "prompt": prompt,
                "system_prompt": system_prompt,
                "max_completion_tokens": 512,
                "temperature": 0.5, # Tutarlılık için biraz daha düşürdüm
            }
        )
        
        # Çıktıyı birleştir (Stream olarak gelebileceği için)
        full_response = "".join(output)
        
        # LLM'ler her şeye rağmen markdown ekleyebilir, temizleyelim
        clean_json_string = full_response.strip()
        if clean_json_string.startswith("```json"):
            clean_json_string = clean_json_string[7:]
        if clean_json_string.endswith("```"):
            clean_json_string = clean_json_string[:-3]
            
        clean_json_string = clean_json_string.strip()

        # JSON Parse işlemi
        response_data = json.loads(clean_json_string)
        print("✅ JSON verisi GPT-4o'dan başarıyla çözümlendi.")
        return response_data

    except json.JSONDecodeError:
        print("❌ Hata: AI modeli JSON formatında düzgün bir çıktı vermedi.")
        print(f"Ham Çıktı: {full_response}")
        return None
    except Exception as e:
        print(f"❌ Replicate API Hatası (GPT-4o): {e}")
        return None