import os
import replicate
import logging
import apps.ai.services.config
from apps.ai.services.config.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

class UniversalAIClient:
    """Tüm AI modellerine (Replicate, OpenAI) atılan istekleri yöneten tek merkez."""
    
    def __init__(self, api_key=None, platform="replicate"):
        self.api_key = api_key
        self.platform = platform
        
        if self.platform == "replicate" and self.api_key:
            
            os.environ["REPLICATE_API_TOKEN"] = self.api_key

    def run_detection(self, model_version, input_data):
        """Grounding DINO vb. detection modelleri için özel koşucu"""
        try:
            # Replicate API çağrısı
            output = replicate.run(model_version, input=input_data)
            return output
        except Exception as e:
            logger.error(f"AI Detection Hatası ({model_version}): {str(e)}")
            return None
            
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
                events = replicate.stream(config["endpoint"], input=payload)
                result = "".join([str(event) for event in events])
            else:
                result = replicate.run(config["endpoint"], input=payload)

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