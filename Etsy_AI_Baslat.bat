@echo off
TITLE Etsy AI Design Automator - Akilli Baslatici
COLOR 0B

echo ======================================================
echo    --- Etsy AI Design Automator Baslatiliyor ---
echo ======================================================

:: 1. Python Kontrolu
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python yuklu degil veya PATH'e eklenmemis!
    pause
    exit /b
)

:: 2. Sanal Ortam (venv) Kontrolu ve Olusturma
if not exist "venv" (
    echo [BILGI] Sanal ortam bulunamadi. Olusturuluyor...
    python -m venv venv
    echo [OK] Sanal ortam olusturuldu.
)

:: 3. Sanal Ortami Aktif Etme
call venv\Scripts\activate

:: 4. Kutuphaneleri Guncelleme
echo [1/4] Kutuphaneler kontrol ediliyor...
pip install -r requirements.txt --quiet

:: 5. Playwright Kurulumu
echo [2/4] Tarayici motoru kontrol ediliyor...
playwright install chromium

:: 6. Veritabani Gocleri (Migration)
echo [3/4] Veritabani yapisi guncelleniyor...
python manage.py makemigrations --noinput
python manage.py migrate --noinput

:: 7. Tarayiciyi Ac ve Sunucuyu Baslat
echo [4/4] Sistem hazir! Tarayici aciliyor...
start http://127.0.0.1:8000

echo ======================================================
echo    --- Sunucu aktif. Kapatmak icin pencereyi kapatin ---
echo ======================================================
python manage.py runserver
pause