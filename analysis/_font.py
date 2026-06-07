import matplotlib
import matplotlib.font_manager as fm

_CJK_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
]

def setup():
    for path in _CJK_CANDIDATES:
        try:
            fm.fontManager.addfont(path)
        except Exception:
            pass
    matplotlib.rcParams["font.family"] = [
        "Noto Sans CJK SC", "Noto Sans CJK JP",
        "PingFang SC", "Arial Unicode MS", "sans-serif"
    ]
    matplotlib.rcParams["axes.unicode_minus"] = False
