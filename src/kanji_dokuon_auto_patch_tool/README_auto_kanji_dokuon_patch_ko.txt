한자 → 한글 독음 자동 폰트 패치 도구
=====================================

이 버전은 readings_template.csv의 hangul 열을 수동으로 채우지 않아도 됩니다.
main.dol 내부에 있는 CP932 폰트 글자 순서표를 직접 찾아서,
각 한자 셀을 한국 한자음으로 자동 변환한 뒤 @Texture #423~#426에 다시 그려 넣습니다.

필요 패키지
-----------
    pip install pillow

가장 간단한 DOL 패치
-------------------
    python patch_kanji_dokuon_font_auto.py auto-patch-dol --dol main.dol --out patched_main.dol --font C:\Windows\Fonts\malgun.ttf

생성물:
    patched_main.dol                  패치된 DOL
    patched_main_auto_readings.csv    자동 생성된 한자/독음 목록
    patched_preview\patched_tex_*.png  미리보기 이미지

GameCube ISO에 바로 넣기
-----------------------
    python patch_kanji_dokuon_font_auto.py auto-patch-iso --iso original.iso --out patched.iso --font C:\Windows\Fonts\malgun.ttf

주의:
    이 명령은 GameCube ISO 직접 패치용입니다.
    Wii ISO는 파티션 암호화 때문에 wit/wwt로 추출/재빌드해야 합니다.

독음 CSV만 먼저 만들기
---------------------
    python patch_kanji_dokuon_font_auto.py auto-csv --dol main.dol --out auto_readings.csv

독음을 직접 고치고 싶을 때
-------------------------
1) auto-csv 또는 auto-patch-dol 실행 후 auto_readings.csv를 엽니다.
2) hangul 열에서 원하는 글자만 수정합니다.
3) 아래 명령으로 다시 패치합니다.

    python patch_kanji_dokuon_font_auto.py patch-dol --dol main.dol --csv auto_readings.csv --out patched_main.dol --font C:\Windows\Fonts\malgun.ttf

보정 독음표 사용
---------------
reading_overrides_sample.csv 같은 파일을 만들어 hanja,hangul 열로 보정할 수 있습니다.

    python patch_kanji_dokuon_font_auto.py auto-patch-dol --dol main.dol --out patched_main.dol --override-map reading_overrides_sample.csv --font C:\Windows\Fonts\malgun.ttf

예:
    hanja,hangul
    円,원
    楽,락
    力,력

내부 처리 방식
-------------
- DOL 내부 CP932 글자 순서표 앵커: 一右雨円王音下火花貝学気九休玉金
- 글자 순서표 크기: 2048바이트 = 1024글자
- 256글자씩 @Texture #423, #424, #425, #426에 대응
- #423, #424의 실제 이미지 밖 패딩 공백은 자동으로 제외
- 폰트 이미지는 기존 C4 4bpp 크기 그대로 픽셀만 교체하므로 main.dol 크기는 변하지 않습니다.
