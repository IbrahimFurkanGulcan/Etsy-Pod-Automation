import json
import logging
from apps.ai.services.client import UniversalAIClient
from apps.ai.services.config.model_registry import ModelRegistry
from apps.common.services.db_helpers import DatabaseService
from apps.ai.services.config.system_prompts import DEFAULT_SYSTEM_PROMPTS

# Kendi model yollarına göre düzenle
from apps.etsy.models import EtsyProduct
from apps.ai.models import SeoOptimization

logger = logging.getLogger(__name__)

class SeoEngineService:
    """Tasarım verilerini kullanarak AI destekli SEO (Title ve Tag) üretir."""

    # ─────────────────────────────────────────────
    # DOĞRULAMA (VALIDATION) KURALLARI
    # ─────────────────────────────────────────────
    @staticmethod
    def _validate_title(title: str) -> str:
        """Etsy Title kuralı: Maksimum 140 karakter. Aşarsa virgüllerden akıllıca kırpar."""
        while len(title) > 140:
            parts = title.rsplit(" ", 1)
            if len(parts) == 1:
                title = title[:140].strip()
                break
            title = parts[0].strip()
        return title

    @staticmethod
    def _validate_tags(tags_string: str) -> list[str]:
        """Etsy Tag kuralları: Maksimum 13 adet ve her biri max 20 karakter."""
        tags = [t.strip() for t in tags_string.split(",") if t.strip()]
        valid_tags = [t for t in tags if len(t) <= 20]
        return valid_tags[:13]

    # ─────────────────────────────────────────────
    # AI ÇAĞRI ADAPTÖRÜ
    # ─────────────────────────────────────────────
    @staticmethod
    def _call_ai_for_json(client: UniversalAIClient, model_id: str, prompt: str, system_prompt: str) -> dict | None:
        """LLM'den JSON yanıt dönmesini bekleyen güvenli istek metodu."""
        try:
            raw_response = client.execute(
                model_id=model_id,
                prompt=prompt,
                system_prompt=system_prompt
            )
            
            if not raw_response:
                return None

            full_response = str(raw_response).strip()
            
            # Markdown JSON bloklarını temizle
            if full_response.startswith("```json"):
                full_response = full_response[7:]
            if full_response.startswith("```"):
                full_response = full_response[3:]
            if full_response.endswith("```"):
                full_response = full_response[:-3]

            return json.loads(full_response.strip())

        except json.JSONDecodeError:
            logger.error(f"❌ SEO Üretimi: JSON çözümleme hatası. Ham Çıktı: {raw_response}")
            return None
        except Exception as e:
            logger.error(f"❌ SEO Üretimi: AI Çağrı Hatası ({model_id}): {e}")
            return None

    # ─────────────────────────────────────────────
    # MOTOR ÇEKİRDEĞİ
    # ─────────────────────────────────────────────
    @classmethod
    def generate_seo_for_design(cls, model_id, api_key, title_prompt, tags_prompt, user_prompt=None, niche="Graphic T-Shirt", design_variation=None, manual_upload=None, target="both"):
        """
        target: 'title', 'tags' veya 'both' alabilir.
        user_prompt: Eğer views'den formatlanmış prompt geldiyse bunu kullanır.
        """
        config = ModelRegistry.get(model_id)
        if not config:
            return {"success": False, "error": f"LLM Modeli '{model_id}' bulunamadı."}

        # --- KAYNAK BELİRLEME (Referans Metni Nereden Gelecek?) ---
        reference_text = ""
        db_filter_kwargs = {} 

        if design_variation:
            print(f"\n🔍 SEO Üretimi (Pipeline 1) Başlatılıyor... (Tasarım ID: {design_variation.id})")
            if user_prompt:
                reference_text = user_prompt
            else:
                product = design_variation.product
                reference_text = f"Original Listing Title: '{product.title}'\nOriginal Tags: '{product.tags}'"
            
            db_filter_kwargs = {"design_variation": design_variation}
            
        elif manual_upload:
            print(f"\n🔍 SEO Üretimi (Pipeline 2) Başlatılıyor... (Upload ID: {manual_upload.id})")
            existing_seo = DatabaseService.find_first_by_filter(SeoOptimization, manual_upload=manual_upload)
            if not existing_seo or not existing_seo.vision_analysis:
                return {"success": False, "error": "Önce Vision Analizi yapılmalıdır."}
                
            reference_text = f"Design Visual Analysis: '{existing_seo.vision_analysis}'\nNiche: {niche}"
            db_filter_kwargs = {"manual_upload": manual_upload}
            
        else:
            return {"success": False, "error": "SEO üretimi için kaynak verilmedi."}

        ai_client = UniversalAIClient(api_key=api_key, platform=config["platform"])
        final_title = ""
        final_tags = []

        # ── 1. SADECE İSTENİRSE TITLE ÜRET ──
        if target in ["both", "title"]:
            title_prompt_text = f"{reference_text}\n\nTask: Generate TITLE and return ONLY JSON with 'new_title' key."
            title_result = cls._call_ai_for_json(ai_client, model_id, title_prompt_text, title_prompt)
            
            if title_result and "new_title" in title_result:
                raw_title = title_result["new_title"]
                # GARANTİ: AI liste dönerse string'e çevir
                if isinstance(raw_title, list):
                    raw_title = " ".join(raw_title)
                
                # DOĞRULAMA (VALIDATION) FONKSİYONUNDAN GEÇİRİYORUZ
                final_title = cls._validate_title(str(raw_title))

        # ── 2. SADECE İSTENİRSE TAGS ÜRET ──
        if target in ["both", "tags"]:
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                needed = 13 - len(final_tags)
                if needed <= 0: break
                
                current_system_prompt = tags_prompt.replace("{needed_count}", str(needed))
                context = f"\nAlready accepted tags: {', '.join(final_tags)}\nGenerate {needed} NEW tags." if final_tags else ""
                
                tag_prompt_text = f"{reference_text}{context}\n\nTask: Generate exactly {needed} TAGS and return ONLY JSON with 'new_tags' key."

                tag_result = cls._call_ai_for_json(ai_client, model_id, tag_prompt_text, current_system_prompt)
                
                if tag_result and "new_tags" in tag_result:
                    raw_tags = tag_result["new_tags"]
                    # GARANTİ: AI virgüllü string yerine liste dönerse string'e çevir
                    if isinstance(raw_tags, list):
                        raw_tags = ", ".join(str(t) for t in raw_tags)
                    
                    # DOĞRULAMA (VALIDATION) FONKSİYONUNDAN GEÇİRİYORUZ
                    new_valid_tags = cls._validate_tags(str(raw_tags))
                    
                    existing_lower = {t.lower() for t in final_tags}
                    for tag in new_valid_tags:
                        if tag.lower() not in existing_lower:
                            final_tags.append(tag)
                            existing_lower.add(tag.lower())
                        if len(final_tags) == 13: break

        final_tags_str = ", ".join(final_tags)

        # ── 3. VERİTABANINA KAYIT ──
        if final_title or final_tags_str:
            update_data = {}
            if final_title: update_data["generated_title"] = final_title
            if final_tags_str: update_data["generated_tags"] = final_tags_str

            seo_record, created = DatabaseService.update_or_create_with_log(
                SeoOptimization,
                **db_filter_kwargs,
                defaults=update_data
            )
            return {"success": True, "title": seo_record.generated_title, "tags": seo_record.generated_tags, "design_id": getattr(design_variation, 'id', None)}

        return {"success": False, "error": "AI üretiminde hata oluştu."}