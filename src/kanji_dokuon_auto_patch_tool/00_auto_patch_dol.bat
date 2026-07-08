@echo off
chcp 65001 >nul
REM main.dol과 이 bat 파일을 같은 폴더에 두고 실행하세요.
REM Pillow가 없으면 먼저: pip install pillow

set DOL=main.dol
set OUT=patched_main.dol
set FONT=C:\Windows\Fonts\malgun.ttf

python patch_kanji_dokuon_font_auto.py auto-patch-dol ^
  --dol "%DOL%" ^
  --out "%OUT%" ^
  --csv-out "auto_readings.csv" ^
  --font "%FONT%" ^
  --preview-dir "patched_preview"

pause
