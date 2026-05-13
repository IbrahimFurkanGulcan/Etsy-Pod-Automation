import base64
from cryptography.fernet import Fernet
from django.conf import settings

def get_fernet():
    # Django'nun SECRET_KEY'inden 32 bytelık bir anahtar üretiyoruz
    key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode('utf-8')[:32].ljust(32, b'0'))
    return Fernet(key)

def encrypt_text(text):
    """Metni şifreler"""
    if not text:
        return text
    return get_fernet().encrypt(text.encode('utf-8')).decode('utf-8')

def decrypt_text(text):
    """Şifreli metni çözer"""
    if not text:
        return text
    try:
        return get_fernet().decrypt(text.encode('utf-8')).decode('utf-8')
    except:
        # Eğer veri daha önceden düz metin olarak kaydedildiyse patlamaması için kendini döndürür
        return text