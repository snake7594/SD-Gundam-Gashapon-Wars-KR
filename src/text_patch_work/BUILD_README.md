# SD건담 가샤폰 워즈 (GGPJB2) — 대사 한글 패치 파이프라인

게임 내 스토리/튜토리얼 **대사(SPB)** 를 한국어로 번역·주입한 파이프라인.
결과물: `../SD Gundam Gashapon Wars (KR text).iso` (원본과 크기 동일, 제자리 패치).

## 포맷 (리버스엔지니어링)
- 대사 저장소: `files/Spb/**/*.SPB` (204개). 매직 `SPAR`.
  - 헤더(LE): +0x00 "SPAR", +0x04 ver=4, +0x08 파일크기, +0x0C 엔트리수, +0x10~ 선형 명령 스트림.
  - 텍스트 명령: `04 00`(opcode) + `len u16 LE`(널 종료 포함) + Shift-JIS 본문 + `00`.
  - **절대 오프셋/점프 테이블 없음** → 동일 크기 제자리 치환이면 100% 안전.
- 제어토큰: `@cN`(색), `@bN`(버튼), `@iN`; 줄바꿈 `\n`/`\\n`; 후리가나 루비 `|漢字(かな)`.

## 폰트 (캐리어-한자 방식, 코드 수정 없음)
- main.dol 한자 순서표(0x2DF02C, 1024자) → 표시 셀 956개.
- 그 중 **진짜 한자 셀**만 캐리어로 사용(기호 ν Ⅱ α ζ ㍉ 는 원형 보존).
- 뒤쪽 668셀 = 대사 한글 음절(글리프 새로 그림), 앞쪽 283셀 = 한자 독음(미번역 메뉴 가독성).
- 인코딩: 한글 음절 → 그 셀 원본 한자의 SJIS 코드. 그 외 문자 → 자기 cp932 바이트.
  - 게임이 그 SJIS를 보면 해당 셀(한글 글리프)을 그림 → 한글 표시.

## 실행 순서
```
python 01_extract.py          # SPB -> dialogue_all.json / unique_jp.json
python 03_make_batches.py     # 고유 1101개 -> 20 배치
(20 translate agents)         # batches/ -> translated/
python 04_merge_validate.py   # 병합/검증/줄바꿈정규화/음절집계 -> ko_final.json, syllables.json
(overflow: 08 -> 3 agents -> 09)   # 예산 초과 88개 압축 재번역
python 06_build_font.py       # 캐리어 폰트 -> patched_main.dol, carrier_map.json
python 07_encode_inject.py --apply   # 동일크기 주입 -> patched_files/
python 11_verify_all.py       # 라운드트립 1313/1313
python 12_build_iso.py --apply  # FST 오프셋 제자리 패치 -> KR text ISO
python 13_verify_iso.py       # ISO에서 직접 읽어 최종 검증
```

## 검증 결과
- 번역: 고유 1101개 전량, 토큰/후리가나 문제 0.
- 음절: 668종 (956셀에 여유).
- 주입: 1313개 대사, 오버플로 0, 전 파일 크기 동일.
- 라운드트립: 1313/1313 일치. ISO 최종 검증 통과.

## 범위/한계
- **번역 대상 = SPB 대사만.** 메뉴/도움말(.vsc, 바이트역순+XOR0xFF), 유닛명 등은 미번역.
- 미번역 화면에서 '희귀 한자'가 캐리어와 겹치면 엉뚱한 한글로 보일 수 있음(흔한 한자는 독음 표시).
- 확장 시: 같은 캐리어 방식으로 .vsc/유닛명도 번역 가능.
