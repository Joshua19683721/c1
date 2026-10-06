# -*- coding: utf-8 -*-
"""繁體中文保證 — Simplified to Traditional Chinese, Taiwan conventions.

The audience is Taiwanese 國小六年級 students, so every Chinese string that
reaches a screen has to be Traditional. Authored content is written that way,
but an LLM reply is not under our control: a model asked in Chinese will
happily answer 「軟體」 or 「網路資訊」. This module is the single gate that
catches that.

Conversion uses OpenCC's s2twp profile, which maps Simplified to Traditional
*and* swaps mainland vocabulary for Taiwan usage:

    軟體   → 軟體        網路資訊 → 網路資訊        點選 → 點選

s2tw alone would leave 「軟體」「網絡」, which are correct characters but wrong
for a Taiwanese classroom.
"""

from __future__ import annotations

__all__ = [
    'to_traditional',
    'backend',
    'is_already_traditional',
    'REQUIRED_PACKAGE',
    'SIMPLIFIED_ONLY',
    'simplified_characters',
]

REQUIRED_PACKAGE = 'opencc-python-reimplemented'

#: Characters that exist only in Simplified Chinese. Deliberately narrow: 台/臺,
#: 里/裡 and 只/隻 are Taiwan usage variants, so an OpenCC round-trip would
#: report false positives on perfectly good Traditional text. This list is the
#: cheap, exact check used for authored articles.
SIMPLIFIED_ONLY = (
    '们个静现学书说语读写给应该认识这么为吗体对错进过还没点热爱双边万与专东丝严丧'
    '狮猫猪鸡鸭鹅马鸟鱼龙龟蚁蚂铁银铅纸笔图馆记声听观见觉变让谁请谢讲词语'
    '门问间关开无长为车动务员园围场处复备够头妇妈宝实将层岁师帮广当录忆忧怀态总'
    '恶戏战户报担数旧时显术机条极树样检欢气汉汤沟泪济湾满灯灵烦烧'
    '赏虫写览团圆坚奖怜恳撑摇摊'
    '兴乐习义乡亲众优会传伤价仅从仓仪产亚'
)


def simplified_characters(text: str) -> list[str]:
    """The Simplified characters present in *text*, in reading order."""
    seen: list[str] = []
    for char in text:
        if char in SIMPLIFIED_ONLY and char not in seen:
            seen.append(char)
    return seen

_CONVERTER = None
_BACKEND = 'unavailable'


def _load():
    global _CONVERTER, _BACKEND
    if _CONVERTER is not None:
        return _CONVERTER
    try:
        from opencc import OpenCC

        _CONVERTER = (OpenCC('s2t'), OpenCC('s2twp'))
        _BACKEND = 'opencc-s2t+s2twp'
    except Exception:  # noqa: BLE001 - any import/config failure degrades
        _CONVERTER = False
        _BACKEND = 'builtin-fallback-table'
    return _CONVERTER


def _fallback(text: str) -> str:
    """Convert with the built-in character table (no OpenCC needed).

    The dependency is optional so a missing install cannot take the classroom
    app down, but returning the model's Simplified reply untouched is worse
    than a partial conversion: the student sees Simplified on screen. This
    table covers the single-character differences only; OpenCC stays primary.
    """
    if not text:
        return text
    from .zh_fallback import FALLBACK_MAP

    return ''.join(FALLBACK_MAP.get(char, char) for char in text)


def to_traditional(text: str) -> str:
    """Return *text* in Traditional Chinese (Taiwan conventions).

    Never raises. OpenCC is used when it is installed; otherwise the built-in
    fallback table converts the characters it knows, so Simplified model output
    does not reach the screen unconverted either way. backend() reports which
    of the two ran.
    """
    if not text:
        return text
    converter = _load()
    if converter is False:
        return _fallback(text)
    s2t, s2twp = converter
    try:
        first_pass = s2t.convert(text)
        # Two passes on purpose. The Taiwan phrase table rewrites correct
        # Traditional text too — 說明 becomes 說明瞭 — so running it
        # unconditionally would mangle text the model already got right.
        # It only runs when the character pass actually changed something,
        # i.e. when the model really did write Simplified.
        if first_pass == text:
            return text
        return s2twp.convert(first_pass)
    except Exception:  # noqa: BLE001 - conversion must never break a reply
        return _fallback(text)


def backend() -> str:
    """Which converter is in use: opencc-s2t+s2twp, or unavailable."""
    _load()
    return _BACKEND


def is_already_traditional(text: str) -> bool:
    """True when conversion would be a no-op, i.e. the text has no Simplified.

    Used by the test suite to prove the authored corpus and the UI chrome are
    already Traditional, rather than merely being fixed up on the way out.
    """
    return to_traditional(text) == text
