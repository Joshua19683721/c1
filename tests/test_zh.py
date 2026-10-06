# -*- coding: utf-8 -*-
"""Tests for the Traditional Chinese gate (src/zh.py).

The gate must:
- Convert Simplified to Traditional Chinese with Taiwan vocabulary (s2twp)
- Still convert when OpenCC is missing, via the built-in fallback table
- Only run the Taiwan phrase pass when the character pass actually changed something
- Never raise, even on conversion errors

Background: the reflection the student reads last (閱讀思考拼圖 and the CoT steps)
is written by the model, so it is the most likely place for Simplified text to
appear. Returning the model's reply untouched when OpenCC was missing is exactly
how Simplified reached the screen, which is what the fallback closes.
"""

from __future__ import annotations

import pytest

import src.zh as zh
from src.zh_fallback import FALLBACK_MAP


@pytest.fixture
def without_opencc():
    """Force the no-OpenCC path, then restore the real backend."""
    saved = (zh._CONVERTER, zh._BACKEND)
    zh._CONVERTER = False
    zh._BACKEND = 'builtin-fallback-table'
    try:
        yield
    finally:
        zh._CONVERTER, zh._BACKEND = saved
        zh._load()


def test_backend_reports_valid_value():
    assert isinstance(zh.backend(), str)
    assert zh.backend() in ('opencc-s2t+s2twp', 'builtin-fallback-table')


def test_empty_string_returns_empty():
    assert zh.to_traditional('') == ''


def test_none_returns_none():
    assert zh.to_traditional(None) is None


def test_already_traditional_is_noop():
    traditional_text = '這是一段繁體中文測試。'
    assert zh.is_already_traditional(traditional_text)
    assert zh.to_traditional(traditional_text) == traditional_text


@pytest.mark.parametrize('simplified,expected_traditional', [
    ('软件', '軟體'),       # mainland term -> Taiwan term
    ('网络信息', '網路資訊'),  # mainland term -> Taiwan term
    ('点击', '點選'),       # mainland term -> Taiwan term
    ('数据', '資料'),       # character conversion
])
def test_simplified_to_traditional_taiwan(simplified, expected_traditional):
    result = zh.to_traditional(simplified)
    if zh.backend() == 'opencc-s2t+s2twp':
        assert result == expected_traditional
    else:
        # The fallback table only knows characters, so Taiwan vocabulary is not
        # applied — but no Simplified character may survive.
        assert not zh.simplified_characters(result), result


def test_two_pass_guard_prevents_mangling():
    """Taiwan phrase pass should only run when character pass changed something."""
    traditional_that_changes = '說明'
    result = zh.to_traditional(traditional_that_changes)
    assert result == traditional_that_changes


def test_conversion_error_does_not_raise():
    original = '測試文字'
    saved = zh._CONVERTER
    try:
        zh._CONVERTER = False
        assert zh.to_traditional(original) == original
    finally:
        zh._CONVERTER = saved
        zh._load()


def test_mixed_simplified_traditional():
    mixed = '這是軟體測試'
    result = zh.to_traditional(mixed)
    if zh.backend() == 'opencc-s2t+s2twp':
        assert result == '這是軟體測試'
    else:
        assert not zh.simplified_characters(result)


# --- the fallback table -----------------------------------------------------

def test_fallback_converts_when_opencc_is_missing(without_opencc):
    """A missing OpenCC must not hand Simplified text to the screen."""
    assert zh.backend() == 'builtin-fallback-table'
    converted = zh.to_traditional('这个学生读得很好，老师很高兴。')
    assert converted == '這個學生讀得很好，老師很高興。'
    assert not zh.simplified_characters(converted)


def test_fallback_leaves_traditional_text_alone(without_opencc):
    text = '閱讀理解練習，學生回答問題。'
    assert zh.to_traditional(text) == text


def test_fallback_table_covers_every_gated_character():
    missing = [ch for ch in zh.SIMPLIFIED_ONLY if ch not in FALLBACK_MAP]
    assert not missing, f'no fallback for: {"".join(missing)}'


def test_fallback_targets_are_never_simplified():
    for simplified, traditional in FALLBACK_MAP.items():
        assert simplified != traditional
        assert traditional not in zh.SIMPLIFIED_ONLY


def test_fallback_table_agrees_with_opencc():
    """Every pair must be what OpenCC itself would produce."""
    try:
        from opencc import OpenCC
    except ImportError:  # pragma: no cover - OpenCC is a declared dependency
        pytest.skip('OpenCC is not installed')
    convert = OpenCC('s2t').convert
    wrong = [
        (s, t, convert(s)) for s, t in FALLBACK_MAP.items() if convert(s) != t
    ]
    assert not wrong, wrong[:5]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
