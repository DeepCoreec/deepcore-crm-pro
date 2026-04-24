@echo off
echo ============================================
echo  DeepCore CRM Pro - Build Script
echo ============================================

pip install -r requirements.txt

pyinstaller --noconfirm --onedir --windowed ^
  --name "DeepCore CRM Pro" ^
  --add-data "theme.py;." ^
  --add-data "modules;modules" ^
  --hidden-import customtkinter ^
  --hidden-import reportlab ^
  --hidden-import openpyxl ^
  main.py

echo.
echo Build completado. Revisa la carpeta dist/
pause
