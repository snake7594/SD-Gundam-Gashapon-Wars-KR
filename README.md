# SD건담 가샤폰 워즈 한글 패치 (SD Gundam Gashapon Wars – Korean Translation)

닌텐도 게임큐브용 **「SD건담 가샤폰 워즈」**(일본판, 게임 ID: **GGPJB2**)의 한국어 번역 패치입니다.

> ⚠️ 이 저장소에는 게임 이미지(ISO)가 포함되어 있지 않습니다. 합법적으로 소유한 원본 ISO에 아래 패치를 적용해서 사용하세요.

## 적용 방법

1. **원본 ISO 준비** — 일본판 「SD Gundam Gashapon Wars」 (GGPJB2)
   - 원본 ISO CRC32: `D5F67251`
2. **패치 적용** — `SDGundamGashaponWars_KR_v1.0.xdelta`
   - Windows: [Delta Patcher](https://github.com/marco-calautti/DeltaPatcher/releases) 로 원본 ISO + 패치 선택 → Apply
   - 또는 커맨드라인: `xdelta3 -d -s "SD Gundam Gashapon Wars.iso" SDGundamGashaponWars_KR_v1.0.xdelta "SD Gundam Gashapon Wars (KR).iso"`
3. **결과 확인** — 패치 후 ISO CRC32: `03E67BAD`
4. Dolphin 등 게임큐브 에뮬레이터로 실행

## 번역 범위 (v1.0)

**한글화 완료**
- 📜 **스토리·튜토리얼 대사** 전량 (미션 시나리오, ~1,300줄)
- 🖥️ **시스템 UI** — 확인/저장/일시정지 대화상자, 메모리카드 메시지 등
- ⚔️ **전투 커맨드** — 맡긴다/끝장내라/돌격/가드 등
- 📂 **메뉴·도움말** — 버튼 안내, 모드 설명, 미션 제목
- 🗺️ **지형명** (평지·우주·대기권·콜로니 등)
- 🧑 **등장인물 이름** (아무로·샤아·마류·키라·신 등)

**미번역 (구조적 한계)**
- 🎨 큰 메뉴 로고(모드 선택·시나리오 게임 등)는 **이미지(텍스처)**라 별도 작업 필요
- 🤖 **유닛 이름**은 게임 내부 참조 키로 쓰여 부득이 일본어(가타카나) 유지
- 📖 유닛 도감 상세 설명·카드 상세 등 일부 텍스트

## 참고
- 폰트가 없는 한글은 게임 한자 글리프 셀을 재활용해 표시합니다. 이 때문에 아직 번역되지 않은 일부 한자 텍스트가 엉뚱한 글자로 보일 수 있습니다.
- 버그·오역 제보 환영합니다.

---
*비영리 팬 번역. 게임의 모든 권리는 원저작권자에게 있습니다.*
