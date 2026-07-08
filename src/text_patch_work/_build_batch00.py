# -*- coding: utf-8 -*-
import json, re, sys

SRC = 'batches/batch_00.json'
OUT = 'translated/batch_00.json'
BR = '\\n'          # 2-char line-break token (backslash + n) -> JSON "\\n"
MARK = '§'     # placeholder for line breaks in templates

# ko templates; MARK (§) = one line break. @tokens inline verbatim.
T = {
 0:  "@c7처음 하는 캡슐 편집이니까§조금만 설명할게요.",
 20: "@c7또 「되돌리기」를 선택하면 편집 화면에§들어왔을 때 상태로 @c6「박스」@c7를 되돌릴 수 있어요.",
 40: "@c7【아무로】「온다ー！」",
 80: "@c7【키라】「키라 야마토, 프리덤, 갑니다！」",
 100:"@c7【아무로】「하나！」",
 120:"@c7【슬레거】「슬레거, 나간다！」",
 140:"@c7【진】「조금만 핸디캡 좀 받을까‥‥받아라！」",
 160:"@c7지온의 영광！ 나의 자존심！§그렇게 놓아둘 순 없다, 놓아둘 순 없어！",
 180:"@c7흥, 싸움은 비정한 법이지.",
 200:"@c7카미유 비단, Z건담,§출격합니다！",
 220:"@c7주위의 빨간 라인 밖으로는§나갈 수 없어요.",
 240:"@c5「격투」@c7 공격은 가까운 거리에서 쓰는§공격이에요.§@c7적에게 다가가서 @b8을 눌러 보세요.",
 260:"@c7그럼 전투를 재개합니다.",
 280:"@c7명중당하면 @b1 버튼을 연타해서§서둘러 벗어나세요.",
 300:"@c7일정 시간마다 여러 효과를 지닌§아이템이 랜덤으로 떨어져요.§@c5「파란 아이템」@c7은 @c6「유닛」@c7이 강해지는§등 플러스 효과가 있어요.",
 320:"@c7이 미션부터 일부 필드에서는§배틀 중에 미사일이 날아와요.",
 340:"@c7이번엔 Y버튼으로 격투 공격을 시도해 봅니다.§가까이 다가가서 Y버튼을 눌러 주세요.",
 380:"@c7시뮬레이션도 없이 다짜고짜 실전이냐….",
 400:"@c7마젤라 어택 부대를 격파하라",
 420:"@c7바쿠와는 다르다……대장기인가！？",
 440:"@c7무우 라 플라가,§에일 스트라이크, 출격한다！",
 460:"@c7좋아？…라기엔 너무 많아요！§그렇죠？ 세이라 씨.",
 480:"@c7마드록을 쓰러뜨려라",
 500:"@c7단판 승부입니다！",
 520:"@c7찾았다……건담！",
 560:"@c7싱글（튜토리얼）시작",
 580:"@c0각 진영이§@c6「유닛」@c0을 가지고,",
 600:"@c7그 자리가 아니라 화살표 위치로 이동§시키는 거예요.",
 620:"@c7적군은 @c6이지스 건담@c7을 중심으로 진을 거느리§고 있습니다.§이들을 모두 쓰러뜨리는 것이 이번 목표입니다.",
 640:"@c7（임시 텍스트와 처리）§실제로는 자신이 선택할 유닛을 고르고,§스타트 버튼으로 시작합니다.§튜토리얼용 전투를 시작합니다.",
 680:"@c7튜토리얼용 전투를 시작합니다.",
 700:"@cb레드 사이드@c7는 오른쪽에 표시돼요.§HP는 여기서 확인할 수 있어요.",
 720:"@c6「포격 유닛」@c7에 커서를 맞추고§@b4를 누르면 메뉴가 나와요.§@c6「포격」@c7을 골라서 적을 @c6「포격」§@c7해 보세요.",
 740:"@c7이 @c6「유닛」@c7을,",
 760:"@b5@c7을 누른 뒤 @b7을 누르§면 COM으로 설정§할 수 있어요.",
 780:"@c7위",
 800:"@c7먼저 @c4「거점」@c7을 @c6「점령」@c7해 보세요.",
 820:"@c0그런 걸 믿을 수 있겠나,§나와 승부해라！",
 840:"@c6「밀어내기」@c7로 @c4「거§점」@c7을 @c6「점령」@c7할 수 있어요.§행동이 끝난 @c6「유닛」§@c7도 밀어낼 수 있어요.",
 860:"@c7그럼 자유롭게 움직여서 적을 쓰러뜨려 보세요.",
 880:"@c7그럼 시험 삼아 @c6「진지」@c7를 늘려 볼게요.",
 900:"@c7이 @c4「거점」@c7에 놓아 볼게요.",
 920:"@c7항상 @c6「유닛」@c7을 배치해서§@c6「점령」@c7당하지 않도록 조심하세요.",
 940:"@c6「카드」@c7에 따라 여러 효과가§발생하지만, 좋은 효과만 있는 건 아니라서§방심하면 안 돼요.",
 960:"@c0하지만, 분하지 않아…§어째서지?!",
 980:"@c0수고했어요.§이제 당신은 어엿한§플레이어네요.",
 1000:"@c7적 소대장「타우로는 전위, 켄은 백업!」",
 1020:"@c7【마류】「‥‥지금은 적의 공격 때문에 못 쓰게 됐으니까,§남은 기체로 어떻게든 하는 수밖에 없겠네.」",
 1040:"@c7【키라】「알겠습니다！」",
 1060:"@c7【마류】「상성은 호각이네. 조심해！」",
 1080:"@c7【마류】「비행 타입 기체는 지형의 영향을 받지 않아.§단기로 나아가는 건 위험하지만, 기동력을 살려서§여러 아군과 연계하면 잘 쓸 수 있을지도？」",
 1100:"@c7【마류】「전함에는 특별한 능력이 있어.§수송 능력과 회복 능력이야.§수송 능력은 커맨드의 「탑재」로§기체를 탑재하고, 「발진」으로 탑재한 기체를§사출해.§회복 능력은 전함 주위의 아군기를§회복시키는 능력이야.§전함 주위에 배치해 두면§다음 차례에 회복돼.」",
}

BINARY_IDS = {60, 360, 540, 660}

def tokens(s):
    return re.findall(r'@[A-Za-z][0-9A-Za-z]', s)

def count_br(jp):
    tmp = jp.replace('\\\\n', '\x01')  # 3-char (\\n) -> marker
    n = tmp.count('\x01')
    n += tmp.count('\\n')              # remaining 2-char (\n)
    return n

def main():
    data = json.load(open(SRC, encoding='utf-8'))
    out = []
    errs = []
    for it in data:
        i = it['id']; jp = it['jp']
        if i in BINARY_IDS:
            out.append({'id': i, 'ko': jp})
            continue
        if i not in T:
            errs.append('MISSING TEMPLATE %s' % i); continue
        tpl = T[i]
        ko = tpl.replace(MARK, BR)
        # validate @token sequence
        jt, kt = tokens(jp), tokens(ko)
        if jt != kt:
            errs.append('TOKEN MISMATCH id=%s jp=%s ko=%s' % (i, jt, kt))
        # validate br count
        jbr = count_br(jp); kbr = tpl.count(MARK)
        if jbr != kbr:
            errs.append('BR MISMATCH id=%s jp=%d ko=%d' % (i, jbr, kbr))
        if MARK in ko:
            errs.append('LEFTOVER MARK id=%s' % i)
        out.append({'id': i, 'ko': ko})
    # ensure every id present
    ids_in = [it['id'] for it in data]
    ids_out = [o['id'] for o in out]
    if ids_in != ids_out:
        errs.append('ID SET/ORDER MISMATCH')
    if errs:
        print('VALIDATION ERRORS:')
        for e in errs: print(' -', e)
        sys.exit(1)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('OK wrote %d items to %s' % (len(out), OUT))

main()
