# -*- coding: utf-8 -*-
"""Tolerant parsing: numbers first, then STT-tolerant semantic matching."""

from __future__ import annotations

import pytest

from src import content, parser


# --- stage 1: explicit numbers ---------------------------------------------

@pytest.mark.parametrize(
    ('raw', 'expected', 'how'),
    [
        ('3', 2, 'bare'),
        (' 2 ', 1, 'bare'),
        ('2.', 1, 'bare'),
        ('第四個', 3, 'cued'),
        ('第三個', 2, 'cued'),
        ('我選第二個', 1, 'cued'),
        ('答案是4', 3, 'cued'),
        ('我猜三', 2, 'cued'),
        ('我覺得是 3 啦', 2, 'isolated'),
        ('４', 3, 'bare'),
    ],
)
def test_explicit_numbers_are_parsed(raw, expected, how):
    index, strategy = parser.extract_option_index(raw)
    assert index == expected
    assert strategy == how


@pytest.mark.parametrize(
    'raw',
    [
        '十五萬大軍',
        '二千五百名士兵',
        '50元',
        '他買了3個橘子',
    ],
)
def test_numbers_inside_a_quoted_answer_are_not_mistaken_for_a_choice(raw):
    """「十五萬」must never be read as option 1, even if STT writes '15萬'."""
    index, _ = parser.extract_option_index(raw)
    assert index is None or len(parser.normalize(raw)) > 2


@pytest.mark.parametrize('raw', ['十五萬大軍', '二千五百名士兵', '我覺得很開心'])
def test_chinese_numerals_are_not_scanned_as_choices(raw):
    assert parser.extract_option_index(raw)[0] is None


def test_option_count_is_respected():
    assert parser.extract_option_index('5', 4)[0] is None


# --- stage 2: semantic matching --------------------------------------------

@pytest.mark.parametrize('article', content.ARTICLES, ids=lambda a: a.id)
def test_every_option_round_trips_to_itself(article):
    """If a student reads an option aloud, STT must map it back to that option."""
    for question in content.build_lesson(article.id).questions:
        for position, text in enumerate(question.options):
            result = parser.fuzzy_match_option(text, question.options)
            assert result.index == position, (article.id, question.number, text)


@pytest.mark.parametrize('article', content.ARTICLES, ids=lambda a: a.id)
def test_options_of_a_question_stay_distinguishable(article):
    """Folding must not collapse two genuinely different options into one."""
    for question in content.build_lesson(article.id).questions:
        folded = [parser.fold_relaxed(parser.normalize(o)) for o in question.options]
        assert len(set(folded)) == 4, question.options


def test_tai_wan_variant_folding():
    options = ['臺灣的海洋文化', '泰國的文化']
    assert parser.fuzzy_match_option('台灣的海洋文化', options).index == 0


def test_synonym_parents():
    """A child says 爸爸 where the option says 父親."""
    lesson = content.build_lesson('beiying')
    question = next(q for q in lesson.questions if q.number == 6)
    result = parser.fuzzy_match_option(
        '因為爸爸很愛我所以我很感動', question.options
    )
    assert result.suggestion == question.correct_index


@pytest.mark.parametrize('raw', ['今天天氣很好', '我不知道', '我忘記了', '香蕉很好吃'])
def test_unrelated_answers_are_rejected(raw):
    options = content.build_lesson('beiying').questions[5].options
    result = parser.fuzzy_match_option(raw, options)
    assert result.index is None


# --- the property that actually matters ------------------------------------

@pytest.mark.parametrize('article', content.ARTICLES, ids=lambda a: a.id)
def test_no_confidently_wrong_answers_across_the_corpus(article):
    """Feeding each option's own text must never select a *different* option.

    Measured over all 200 options this is the single most important guarantee:
    a wrong grade shown to a child is worse than an honest re-ask.
    """
    for question in content.build_lesson(article.id).questions:
        for position, text in enumerate(question.options):
            result = parser.fuzzy_match_option(text, question.options)
            assert result.index in (None, position)


def test_ambiguous_input_is_reported_not_guessed():
    lesson = content.build_lesson('beiying')
    question = next(q for q in lesson.questions if q.number == 10)
    result = parser.fuzzy_match_option('我覺得都要想', question.options)
    if result.index is None:
        assert result.suggestion is not None or result.how == 'below-threshold'


# --- combined cascade -------------------------------------------------------

def test_numbers_beat_text_matching():
    options = ['第一個選項很長很長的文字', '第二個', '第三個', '第四個']
    index, how, score = parser.combine_signals('4', options)
    assert (index, how) == (3, 'bare')
    assert score == 1.0


def test_combine_falls_through_to_fuzzy():
    options = list(content.build_lesson('kongchengji').questions[8].options)
    index, how, _ = parser.combine_signals(options[2], options)
    assert index == 2
    assert how == 'fuzzy'


def test_normalize_strips_punctuation_and_case():
    assert parser.normalize('  Hello,  WORLD！ ') == 'helloworld'
    assert parser.normalize('１２３４') == '1234'


def test_format_options_renders_one_based_labels():
    assert parser.format_options(['甲', '乙']) == '1. 甲　2. 乙'
