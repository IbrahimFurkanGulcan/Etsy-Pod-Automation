# seo_service.py

import json
from .models import EtsyProduct, SeoOptimization, ManualUpload
from .generation_services import UniversalAIClient


# ─────────────────────────────────────────────
# DOĞRULAMA YARDIMCILARI
# ─────────────────────────────────────────────

def _parse_tags(tags_string: str) -> list[str]:
    return [t.strip() for t in tags_string.split(",") if t.strip()]


def _validate_tags(tags: list[str]) -> list[str]:
    valid = [t for t in tags if len(t) <= 20]
    return valid[:13] if len(valid) > 13 else valid


def _validate_title(title: str) -> str:
    while len(title) > 140:
        parts = title.rsplit(",", 1)
        if len(parts) == 1:
            title = title[:140].strip()
            break
        title = parts[0].strip()
    return title


# ─────────────────────────────────────────────
# EVRENSEL AI ÇAĞRI ADAPTÖRÜ
# ─────────────────────────────────────────────

def _call_ai(
    client: UniversalAIClient,
    system_prompt: str,
    user_prompt: str,
    model_id: str,
) -> dict | None:
    try:
        raw = client.execute(
            model_id=model_id,
            prompt=user_prompt,
            system_prompt=system_prompt,
        )
        if raw is None:
            return None

        full_response = str(raw).strip()

        if full_response.startswith("```json"):
            full_response = full_response[7:]
        if full_response.startswith("```"):
            full_response = full_response[3:]
        if full_response.endswith("```"):
            full_response = full_response[:-3]

        return json.loads(full_response.strip())

    except json.JSONDecodeError:
        print(f"❌ JSON çözümleme hatası. Ham çıktı: {raw}")
        return None
    except Exception as e:
        print(f"❌ AI Çağrı Hatası ({model_id}): {e}")
        return None


# ─────────────────────────────────────────────
# ÜRETİM FONKSİYONLARI
# ─────────────────────────────────────────────

def _generate_title(
    client: UniversalAIClient,
    model_id: str,
    reference_text: str, # <-- DEĞİŞTİ (Eski original_title ve tags yerine tek referans)
    niche: str,
    system_prompt: str, 
) -> str | None:
    print("🔤 Title üretiliyor...")
    prompt = (
        f"{reference_text}\n\n"
        f"Generate an SEO-optimized TITLE for a '{niche}' design based on the details above."
    )
    result = _call_ai(client, system_prompt, prompt, model_id)
    return result.get("new_title") if result else None



def _generate_tags(
    client: UniversalAIClient,
    model_id: str,
    reference_text: str, # <-- DEĞİŞTİ
    niche: str,
    system_prompt: str,  
    needed_count: int = 13,
    existing_tags: list[str] | None = None,
) -> list[str] | None:
    print(f"🏷️  {needed_count} adet tag üretiliyor...")
    final_system = system_prompt.replace("{needed_count}", str(needed_count))
    context_line = ""
    if existing_tags:
        context_line = (
            f"\nAlready accepted tags (DO NOT repeat these): {', '.join(existing_tags)}\n"
            f"Generate {needed_count} NEW tags that complement the existing ones."
        )
    prompt = (
        f"{reference_text}\n"
        f"Niche: '{niche}'{context_line}\n\n"
        f"Generate exactly {needed_count} tags following all system rules."
    )
    result = _call_ai(client, final_system, prompt, model_id)
    if not result or "new_tags" not in result:
        return None
    return _parse_tags(result["new_tags"])
    

def _generate_focus_keyword(
    client: UniversalAIClient,
    model_id: str,
    original_title: str,
    niche: str,
) -> str:
    prompt = (
        f"Title: '{original_title}', Niche: '{niche}'\n"
        'Return ONLY: {"focus_keyword": "..."}'
    )
    result = _call_ai(
        client,
        'Return only a JSON object {"focus_keyword": "..."} '
        "with the single most important SEO keyword.",
        prompt,
        model_id,
    )
    return result.get("focus_keyword", "") if result else ""


def _build_valid_tags(
    client: UniversalAIClient,
    model_id: str,
    reference_text: str,         # <-- DEĞİŞTİ: Artık 2 ayrı parametre yerine tek referans metni var
    niche: str,                  # <-- Artık doğru sırasına oturdu
    system_prompt: str,          # DB'den gelir, zorunlu
    max_retries: int = 3,
) -> list[str]:
    final_tags: list[str] = []

    for attempt in range(1, max_retries + 1):
        needed = 13 - len(final_tags)
        print(f"  ↪ Deneme {attempt}: {needed} tag üretilecek (mevcut: {len(final_tags)})")

        # İçerideki _generate_tags çağrısı da artık yeni yapıya uygun
        new_raw = _generate_tags(
            client, model_id,
            reference_text, niche, 
            system_prompt=system_prompt,
            needed_count=needed,
            existing_tags=final_tags or None,
        )

        if not new_raw:
            print(f"  ⚠️  Deneme {attempt} başarısız, tekrar deneniyor...")
            continue

        valid_new = _validate_tags(new_raw)
        existing_lower = {t.lower() for t in final_tags}

        for tag in valid_new:
            if tag.lower() not in existing_lower:
                final_tags.append(tag)
                existing_lower.add(tag.lower())
            if len(final_tags) == 13:
                break

        print(f"  ✅ Geçerli tag sayısı: {len(final_tags)}/13")
        if len(final_tags) == 13:
            break

    if len(final_tags) < 13:
        print(f"⚠️  {max_retries} denemeden sonra yalnızca {len(final_tags)} geçerli tag üretilebildi.")

    return final_tags[:13]


# ─────────────────────────────────────────────
# ANA FONKSİYON
# ─────────────────────────────────────────────

def generate_seo_for_product(
    ai_client: UniversalAIClient,
    model_id: str,
    title_system_prompt: str,
    tags_system_prompt: str,
    target: str = "both",
    niche: str = "Graphic T-Shirt",
    product_id: int = None,
    upload_id: int = None
):
    print(f"\n🔍 SEO Üretimi Başlatılıyor... (Hedef: {target} | Model: {model_id})")

    product = None
    upload = None
    existing_seo = None
    reference_text = ""

    # DİNAMİK VERİ KAYNAĞI SEÇİMİ
    if product_id:
        try:
            product = EtsyProduct.objects.get(id=product_id)
            existing_seo = getattr(product, 'seo', None)
            reference_text = f"Original Listing Title: '{product.title}'\nOriginal Tags: '{product.tags}'"
        except EtsyProduct.DoesNotExist:
            print("❌ Hata: Ürün bulunamadı.")
            return None
    elif upload_id:
        try:
            upload = ManualUpload.objects.get(id=upload_id)
            existing_seo = getattr(upload, 'seo', None)
            # YENİ: Vision AI'dan gelen analizi referans olarak veriyoruz!
            reference_text = f"Design Visual Analysis: '{upload.vision_analysis}'"
        except ManualUpload.DoesNotExist:
            print("❌ Hata: Upload bulunamadı.")
            return None
    else:
        print("❌ Hata: Ne Product ID ne de Upload ID verildi.")
        return None

    final_title    = existing_seo.generated_title if existing_seo else ""
    final_tags_str = existing_seo.generated_tags  if existing_seo else ""
    focus_keyword  = existing_seo.target_keywords  if existing_seo else ""

    # ── 1. TITLE ────────────────────────────────────────────────
    if target in ('title', 'both'):
        raw_title = None
        for attempt in range(1, 4):
            raw_title = _generate_title(
                ai_client, model_id,
                reference_text, niche, # <-- YENİ REFERANS METNİ
                system_prompt=title_system_prompt,
            )
            if raw_title: break
            print(f"  ⚠️  Title denemesi {attempt} başarısız, tekrar deneniyor...")

        if raw_title:
            final_title = _validate_title(raw_title)
            print(f"✅ Title ({len(final_title)} karakter): {final_title}")
        else:
            print("❌ Title üretilemedi.")

    # ── 2. TAGS ─────────────────────────────────────────────────
    if target in ('tags', 'both'):
        final_tag_list = _build_valid_tags(
            ai_client, model_id,
            reference_text, niche, # <-- YENİ REFERANS METNİ
            system_prompt=tags_system_prompt,
        )
        final_tags_str = ", ".join(final_tag_list)
        print(f"✅ Tags ({len(final_tag_list)} adet): {final_tags_str}")

    # ── 3. KAYDET ───────────────────────────────────────────────
    try:
        if product_id:
            # PIPELINE 1 İÇİN (Etsy Ürünleri)
            seo_record, created = SeoOptimization.objects.update_or_create(
                product=product,
                defaults={"generated_title": final_title, "generated_tags": final_tags_str}
            )
            print(f"💾 [Pipeline 1] SEO Kaydedildi ({'Oluşturuldu' if created else 'Güncellendi'})")
            return seo_record

        elif upload_id:
            # PIPELINE 2 İÇİN (Manuel Yüklemeler)
            seo_record, created = SeoOptimization.objects.update_or_create(
                manual_upload=upload, # <--- KRİTİK NOKTA: manual_upload nesnesini veriyoruz
                defaults={"generated_title": final_title, "generated_tags": final_tags_str}
            )
            print(f"💾 [Pipeline 2] SEO Kaydedildi ({'Oluşturuldu' if created else 'Güncellendi'})")
            return seo_record
            
        else:
            print("❌ Kayıt Hatası: Ne product_id ne de upload_id var.")
            return None

    except Exception as e:
        print(f"❌ Veritabanı Kayıt Hatası: {e}")
        import traceback
        traceback.print_exc()
        return None
