from django.core.management.base import BaseCommand
from manager.models import DesignVariation
from manager.generation_services import ReplicateSimpleGenerator
from django.core.files.base import ContentFile
import requests
import os
import time
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed # <--- Paralel işlem kütüphanesi

class Command(BaseCommand):
    help = 'Mevcut tasarımları Upscale et ve Arka Planlarını temizle (PARALEL MOD)'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, help='Sadece belirli bir varyasyon ID işle')
        parser.add_argument('--force', action='store_true', help='Daha önce yapılmış olsa bile tekrar yap')

    def handle(self, *args, **kwargs):
        load_dotenv()

        # 1. TOKEN KONTROLÜ
        api_token = os.getenv("REPLICATE_API_TOKEN")
        if not api_token:
            self.stdout.write("❌ HATA: 'REPLICATE_API_TOKEN' bulunamadı! .env dosyasını kontrol et.")
            return
        
        self.stdout.write(f"🔑 API Token Algılandı: {api_token[:5]}...")
        
        # 2. İŞLENECEK TASARIMLARI SEÇ
        if kwargs['id']:
            variations = DesignVariation.objects.filter(id=kwargs['id'])
        elif kwargs['force']:
            variations = DesignVariation.objects.exclude(generated_image='')
        else:
            # İşlenmemiş olanlar (no_bg_image boş olanlar)
            variations = DesignVariation.objects.exclude(generated_image='').filter(no_bg_image='')

        if not variations.exists():
            self.stdout.write("❌ İşlenecek tasarım bulunamadı.")
            return

        # ==============================================================================
        # 🛠️ AI MODÜLLERİ (Tek sefer tanımlanır, tüm threadler ortak kullanır)
        # ==============================================================================
        
        # 1. UPSCALE (Recraft)
        upscaler = ReplicateSimpleGenerator(
            model_endpoint="recraft-ai/recraft-crisp-upscale",
            model_name_tag="Upscaler",
            image_input_key="image",
            input_config={} 
        )

        # 2. BG REMOVER (Bria)
        bg_remover = ReplicateSimpleGenerator(
            model_endpoint="bria/remove-background",
            model_name_tag="BG-Remover",
            image_input_key="image",
            input_config={
                "preserve_alpha": True,
                "content_moderation": False,
                "preserve_partial_alpha": True
            } 
        )
        # ==============================================================================

        # --- İŞÇİ FONKSİYONU (Tek bir resmi baştan sona işler) ---
        def process_single_variation(v):
            try:
                # Veritabanı bağlantısı kopmaması için tazeleyelim (opsiyonel ama güvenli)
                # Thread içinde print karışabilir, o yüzden logları biriktirip return edeceğiz.
                logs = []
                logs.append(f"▶️ ID: {v.id} Başladı...")

                # Dosya Kontrolü
                if not v.generated_image or not os.path.exists(v.generated_image.path):
                    v.status = 'failed'
                    v.save()
                    return f"❌ ID: {v.id} - Dosya diskte yok."

                # Durumu 'processing' yap
                v.status = 'processing'
                v.save()

                current_process_path = v.generated_image.path

                # --- ADIM 1: UPSCALE ---
                upscale_success = False
                
                # Eğer zaten varsa ve force yoksa atla
                if v.upscaled_image and not kwargs['force'] and os.path.exists(v.upscaled_image.path):
                    current_process_path = v.upscaled_image.path
                    upscale_success = True
                    logs.append(f"   ℹ️ ID: {v.id} - Upscale zaten var.")
                else:
                    # Yoksa Upscale Et
                    upscale_url = upscaler.process_image(current_process_path)
                    if upscale_url:
                        resp = requests.get(upscale_url)
                        if resp.status_code == 200:
                            file_name = f"upscaled_{v.product.id}_{v.id}.png"
                            # save() metodu veritabanını günceller
                            v.upscaled_image.save(file_name, ContentFile(resp.content), save=True)
                            current_process_path = v.upscaled_image.path
                            upscale_success = True
                            logs.append(f"   ✅ ID: {v.id} - Upscale Tamam.")
                        else:
                            logs.append(f"   ❌ ID: {v.id} - Upscale indirilemedi.")
                    else:
                        logs.append(f"   ❌ ID: {v.id} - Upscale API hatası.")

                # Eğer Upscale başarısızsa BG Removal'a geçme
                if not upscale_success:
                    v.status = 'failed'
                    v.save()
                    return "\n".join(logs)

                # --- ADIM 2: BACKGROUND REMOVAL ---
                # Rembg'ye upscaled resmi veriyoruz
                bg_url = bg_remover.process_image(current_process_path)
                if bg_url:
                    resp = requests.get(bg_url)
                    if resp.status_code == 200:
                        file_name = f"nobg_{v.product.id}_{v.id}.png"
                        v.no_bg_image.save(file_name, ContentFile(resp.content), save=False)
                        
                        v.status = 'completed'
                        v.save()
                        logs.append(f"   🎉 ID: {v.id} - FİNAL İŞLEM TAMAMLANDI!")
                        return "\n".join(logs)
                    else:
                        v.status = 'failed'
                        v.save()
                        logs.append(f"   ❌ ID: {v.id} - BG Remover indirilemedi.")
                else:
                    v.status = 'failed'
                    v.save()
                    logs.append(f"   ❌ ID: {v.id} - BG Remover API hatası.")

                return "\n".join(logs)

            except Exception as e:
                return f"🔥 ID: {v.id} KRİTİK HATA: {str(e)}"

        # --- ANA ÇALIŞTIRMA BLOĞU (PARALEL) ---
        
        self.stdout.write(f"🚀 {len(variations)} adet tasarım AYNI ANDA işlenmeye başlıyor...")
        
        # max_workers=5: Aynı anda en fazla 5 tasarım işlensin (API limitlerine takılmamak için ideal)
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Görevleri havuza at
            future_to_variation = {executor.submit(process_single_variation, v): v for v in variations}
            
            # Tamamlananları yakala
            for future in as_completed(future_to_variation):
                result_log = future.result()
                self.stdout.write("\n" + "-"*30)
                self.stdout.write(result_log)
                self.stdout.write("-"*30)

        self.stdout.write("\n✅ TÜM İŞLEMLER BİTTİ.")