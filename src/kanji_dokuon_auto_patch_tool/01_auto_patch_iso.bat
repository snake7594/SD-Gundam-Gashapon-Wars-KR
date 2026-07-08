@echo off
chcp 65001 >nul
REM GameCube ISO 직접 패치용입니다. Wii ISO는 wit/wwt로 추출/재빌드해야 합니다.
REM original.iso와 이 bat 파일을 같은 폴더에 두고 실행하세요.
REM Pillow가 없으면 먼저: pip install pillow

set ISO=original.iso
set OUT=patched.iso
set FONT=C:\Windows\Fonts\malgun.ttf

python patch_kanji_dokuon_font_auto.py auto-patch-iso ^
  --iso "%ISO%" ^
  --out "%OUT%" ^
  --work-dir "auto_patch_work" ^
  --csv-out "auto_readings.csv" ^
  --font "%FONT%" ^
  --preview-dir "patched_preview"

pause
