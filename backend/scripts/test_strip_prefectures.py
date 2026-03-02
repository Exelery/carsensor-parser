#!/usr/bin/env python3
"""Проверка _strip_prefectures: список текстов на входе, печать до/после."""
import re
import sys


def _strip_prefectures(s: str) -> str:
    if not s or not s.strip():
        return s
    s = s.strip()
    parts = s.split()
    suffix_re = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\u3000-\u303fー・]{2,6}[都道府県]$")
    cleaned = []
    for i, p in enumerate(parts):
        if (p.endswith(")") or p.endswith("）")) and len(p) >= 2 and p[-2] in "都道府県":
            p = p[:-1].rstrip()
        if len(p) < 2 or p[-1] not in "都道府県":
            cleaned.append(p)
            continue
        suffix = suffix_re.search(p)
        if suffix:
            rest = p[: suffix.start()].rstrip()
            if rest:
                cleaned.append(rest)
        elif len(p) > 6:
            cleaned.append(p)
    while cleaned and len(cleaned[-1]) >= 2 and cleaned[-1][-1] in "都道府県":
        cleaned.pop()
    return " ".join(cleaned).strip()


SAMPLES = [
    "スズキ ハスラー 660 ハイブリッド G 岡山県",
    "ダイハツ ムーヴ 660 L 大阪府",
    "スズキ ハスラー 660 ハイブリッド G 滋賀県",
    "ダイハツ ムーヴキャンバス 660 セオリー X 愛知県",
    "フィアット パンダ イージー 北海道",
    "ルノー トゥインゴ EDC 東京都",
    "シトロエン C3 インスパイア―ド バイ ジャパン コレクション 千葉県",
    "ＢＭＷ 5シリーズ M550i xドライブ 4WD 東京都",
    "フィアット 500(チンクエチェント) ツインエア ラウンジ 東京都",
    "ミニ ミニ クーパーD 5ドア DCT 愛知県",
    "フィアット 500(チンクエチェント) 1.2 ポップ 東京都",
    "フィアット 500(チンクエチェント) ツインエア カルト 京都府",
    "ＢＭＷ 3シリーズ 320d xドライブ ディーゼルターボ 4WD 神奈川県",
    "フィアット パンダ イージー 福岡県",
    "スバル フォレスター 1.8 スポーツ 4WD 埼玉県",
    "トヨタ カローラツーリング 1.8 ハイブリッド WxB E-Four 4WD 山形県",
    "スバル レヴォーグ 1.8 GT EX 4WD 北海道",
    "(日産 NV200バネットバン 1.6 DX 岐阜県)",
]


def main():
    if len(sys.argv) > 1:
        lines = [line.strip() for line in sys.argv[1:] if line.strip()]
    else:
        lines = SAMPLES
    for raw in lines:
        out = _strip_prefectures(raw)
        ok = "✓" if out != raw and (not out or not any(c in out for c in "都道府県")) else " "
        print(f"{ok} IN:  {raw}")
        print(f"   OUT: {out}")
        print()


if __name__ == "__main__":
    main()
