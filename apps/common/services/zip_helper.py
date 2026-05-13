import io
import zipfile
import os
from django.http import HttpResponse
from datetime import datetime

class ZipExportService:
    """
    Bellek (RAM) üzerinde güvenli ZIP dosyaları oluşturur ve 
    kullanıcıya indirebileceği bir HttpResponse döndürür.
    """
    def __init__(self, filename_prefix="Etsy_Export"):
        self.buffer = io.BytesIO()
        self.zip_file = zipfile.ZipFile(self.buffer, 'w', zipfile.ZIP_DEFLATED)
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        self.filename = f"{filename_prefix}_{date_str}.zip"

    def add_text_file(self, file_path_in_zip, text_content):
        """ZIP içerisine uçtan uca bir text (txt) dosyası oluşturur."""
        self.zip_file.writestr(file_path_in_zip, text_content)

    def add_file_from_disk(self, file_path_in_zip, physical_file_path):
        """Diskteki fiziksel bir dosyayı okuyup ZIP'e ekler (I/O Korumalı)."""
        try:
            if os.path.exists(physical_file_path):
                with open(physical_file_path, 'rb') as f:
                    self.zip_file.writestr(file_path_in_zip, f.read())
        except Exception as e:
            print(f"ZIP'e dosya ekleme hatası ({physical_file_path}): {e}")

    def add_directory_contents(self, dir_path_in_zip, physical_dir_path):
        """Bir klasörün içindeki tüm dosyaları ZIP'te belirtilen klasörün içine koyar."""
        if os.path.exists(physical_dir_path):
            for file_name in os.listdir(physical_dir_path):
                file_path = os.path.join(physical_dir_path, file_name)
                if os.path.isfile(file_path):
                    self.add_file_from_disk(f"{dir_path_in_zip}/{file_name}", file_path)

    def get_http_response(self):
        """ZIP'i kapatır ve kullanıcıya indirtmek üzere Django HttpResponse döner."""
        self.zip_file.close()
        self.buffer.seek(0)
        
        response = HttpResponse(self.buffer, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{self.filename}"'
        return response