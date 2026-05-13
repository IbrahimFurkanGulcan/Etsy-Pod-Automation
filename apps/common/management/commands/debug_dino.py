import os
import replicate
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# Test edilecek resim (Senin Tired Moms tişörtü)
IMAGE_URL = "https://i.etsystatic.com/47833597/r/il/e1bca9/6697435914/il_794xN.6697435914_i2ca.jpg"

print("\n🔍 DINO API Testi Başlıyor...")
api_token = os.getenv('REPLICATE_API_TOKEN')
print(f"🔑 API Anahtarı: {'Mevcut ✅' if api_token else 'YOK! ❌ (.env dosyasını kontrol et)'}")

if not api_token:
    print("❌ Lütfen .env dosyanı kontrol et.")
    exit()

try:
    print("⏳ Replicate'e istek gönderiliyor (Adirik Modeli)...")
    
    # Grounding DINO'yu çalıştır
    output = replicate.run(
        "adirik/grounding-dino:efd10a8ddc57ea28773327e881ce95e20cc1d09e39ec6f22339d44c6428cf93a",
        input={
            "image": IMAGE_URL,
            "prompt": "graphic design",
            "box_threshold": 0.20,
            "text_threshold": 0.20
        }
    )
    
    print("\n✅ API CEVABI GELDİ!")
    print("="*60)
    print(f"Veri Tipi (Type): {type(output)}")
    print("-" * 20)
    # Çıktıyı detaylı yazdır
    print(f"HAM VERİ:\n{output}")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ HATA OLUŞTU: {e}")