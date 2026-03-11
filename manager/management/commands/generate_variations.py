from django.core.management.base import BaseCommand
from manager.detect_crop import crop_and_save_product_design
from manager.generation_services import ReplicateSimpleGenerator
from manager.models import EtsyProduct
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class Command(BaseCommand):
    help = 'Replicate API ile Tasarım Üretimi'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, help='İşlenecek Ürün ID')

    def handle(self, *args, **kwargs):
        # Ürün Seçimi
        if kwargs['id']:
            products = EtsyProduct.objects.filter(id=kwargs['id'])
        else:
            products = [EtsyProduct.objects.last()]

        if not products:
            self.stdout.write("❌ Ürün yok.")
            return

        # ==============================================================================
        # 🛠️ AYARLAR BURADA: İstediğin Modeli ve Inputu Burada Tanımla
        # ==============================================================================
        
        active_models = []

        # ÖRNEK 1: FLUX 2 PRO (Senin istediğin gelişmiş yapı)
        # Not: Flux 2 Pro genelde resim inputunu 'image_prompt' olarak ister.
        active_models.append(
            ReplicateSimpleGenerator(
                model_endpoint="black-forest-labs/flux-2-pro", 
                model_name_tag="Flux-2-Pro",
                input_is_list=True,
                image_input_key="input_images",  # <--- Burası önemli: Model resmi hangi isimle istiyor?
                
                # 👇 SENİN İSTEDİĞİN ÖZEL INPUT SÖZLÜĞÜ 👇
                input_config={
                    # Prompt içine {title} koyarsan ürün başlığını oraya yapıştırır
                    "prompt": "vector graphic design of the image, isolated on white background, clean lines, professional illustration style, flat colors, just design",
                    "resolution": "1 MP",
                    "aspect_ratio": "1:1",
                    "output_format": "png",
                    "output_quality": 80,
                    "safety_tolerance": 2
                }
            )
        )

        # ÖRNEK 2: Seedream (Daha basit model)
        # Not: 4.5 input olarak 'image_input' ister.
        active_models.append(
            ReplicateSimpleGenerator(
                model_endpoint="bytedance/seedream-4.5",
                model_name_tag="Seedream-4.5",
                input_is_list=True,
                image_input_key="image_input", 
                
                input_config={
                    "prompt": "vector graphic design of the image, isolated on white background, clean lines, professional illustration style, flat colors, just design",
                    "size": "2K",
                    "width": 2048,
                    "height": 2048,
                    "max_images": 1,
                    "aspect_ratio": "1:1",
                    "sequential_image_generation": "disabled"
                }
            )
        )
        # ==============================================================================

        # ÖRNEK 3: Nano Banana 
        # Not: Banana input olarak 'image_input' ister.
        active_models.append(
            ReplicateSimpleGenerator(
                model_endpoint="google/nano-banana",
                model_name_tag="Nano-Banana",
                input_is_list=True,
                image_input_key="image_input", 
                
                input_config={
                    "prompt": "vector graphic design of the image, isolated on white background, clean lines, professional illustration style, flat colors, just design",
                    "aspect_ratio": "1:1",
                    "output_format": "png"
                }
            )
        )
        # ==============================================================================


        # --- YARDIMCI FONKSİYON: Tek bir modelin çalıştırılma işi ---
        def run_single_model(model_instance, product_obj, crop_file_path):
            """Bu fonksiyon Thread içinde çalışacak"""
            try:
                model_instance.generate(product_obj, crop_file_path)
                return f"✅ {model_instance.model_name_tag} Tamamlandı."
            except Exception as e:
                return f"❌ {model_instance.model_name_tag} Hatası: {e}"


        # --- ANA DÖNGÜ ---
        self.stdout.write(f"🚀 {len(products)} ürün, {len(active_models)} model ile PARALEL işlenecek...")

        for p in products:
            self.stdout.write(f"\n📦 Ürün Hazırlanıyor: {p.title[:30]}... (ID: {p.id})")
            
            # 1. Kırpma (Bu işlem hala seri yapılmalı, çünkü referans resim olmadan modeller çalışamaz)
            crop_path = None
            if p.cropped_image and os.path.exists(p.cropped_image.path):
                crop_path = p.cropped_image.path
            else:
                crop_and_save_product_design(p.id)
                p.refresh_from_db() # Veritabanını tazele
                if p.cropped_image and os.path.exists(p.cropped_image.path):
                    crop_path = p.cropped_image.path

            # 2. PARALEL ÜRETİM BAŞLIYOR 🏁
            if crop_path:
                self.stdout.write(f"🔥 {len(active_models)} model AYNI ANDA tetikleniyor...")
                
                # ThreadPoolExecutor ile bir işçi havuzu oluşturuyoruz
                # max_workers=5 demek, aynı anda en fazla 5 model çalışsın demek.
                with ThreadPoolExecutor(max_workers=5) as executor:
                    
                    # Tüm modelleri göreve gönderiyoruz (Submit)
                    future_tasks = []
                    for model in active_models:
                        task = executor.submit(run_single_model, model, p, crop_path)
                        future_tasks.append(task)
                    
                    # Sonuçları bekliyoruz (Opsiyonel: İstersen beklemeyip geçebilirsin ama logları görmek için beklemek iyidir)
                    for future in as_completed(future_tasks):
                        result_msg = future.result()
                        print(f"   -> {result_msg}")
                        
            else:
                self.stdout.write("⚠️ Kırpma hatası, resim yok.")
                
            time.sleep(1) # Ürünler arası kısa bekleme
            
        self.stdout.write("\n✅ BÜTÜN İŞLEMLER TAMAMLANDI.")