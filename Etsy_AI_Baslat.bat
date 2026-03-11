@echo off
title Etsy AI Design Automation - Baslatici
color 0A

echo ===================================================
echo     Etsy AI Design Automation'a Hos Geldiniz!
echo ===================================================
echo.

:: Python yüklü mü kontrol et
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [HATA] Python bilgisayarinizda yuklu degil! 
    echo Lutfen python.org adresinden Python'i indirin ve kurarken "Add to PATH" secenegini isaretleyin.
    pause
    exit
)

:: Sanal ortam (venv) var mı kontrol et, yoksa İLK KURULUMU yap
IF NOT EXIST "venv\Scripts\activate.bat" (
    echo [SISTEM] Ilk kurulum yapiliyor. Bu islem internet hizina bagli olarak birkac dakika surebilir...
    echo [1/4] Sanal ortam olusturuluyor...
    python -m venv venv
    
    echo [2/4] Kutuphaneler indiriliyor...
    call venv\Scripts\activate
    pip install -r requirements.txt
    
    echo [3/4] Playwright tarayici motoru kuruluyor...
    playwright install chromium
    
    echo [4/4] Veritabani hazirlaniyor...
    python manage.py migrate
    
    echo [SISTEM] Kurulum basariyla tamamlandi!
) ELSE (
    echo [SISTEM] Sistem hazir, sanal ortam aktif ediliyor...
    call venv\Scripts\activate
)

echo.
echo [BASARILI] Sunucu baslatiliyor... Lutfen bu siyah pencereyi KAPATMAYIN!
echo Uygulama tarayicinizda otomatik olarak acilacaktir...
echo.

:: Tarayıcıyı 2 saniye gecikmeyle otomatik aç (Sunucunun ayaklanmasını beklemek için)
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8000/login/

:: Django sunucusunu ayağa kaldır
python manage.py runserver

pause