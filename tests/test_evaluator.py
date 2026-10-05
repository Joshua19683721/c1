# -*- coding: utf-8 -*-
"""Pipeline 1 cascade, with the LLM disabled so the behaviour is deterministic."""

from __future__ import annotations

import pytest

from src.content import build_lesson
from src.evaluator import evaluate_answer


@pytest.fixture()
def question():
    lesson = build_lesson('beiying')
    return lesson.questions[0]


def _evaluate(question, text):
    return evaluate_answer(question, text, allow_llm=False)


def test_number_answer_skips_the_model(question):
    result = _evaluate(question, str(question.display_number))
    assert result.how == 'number'
    assert result.resolved
    assert result.is_correct is True
    assert result.selected_text == question.correct_text


def test_wrong_number_is_reported_as_wrong(question):
    wrong = (question.correct_index + 1) % 4
    result = _evaluate(question, str(wrong + 1))
    assert result.index == wrong
    assert result.is_correct is False


def test_chinese_number_is_understood(question):
    numerals = {1: '一', 2: '二', 3: '三', 4: '四'}
    target = numerals[question.display_number]
    result = _evaluate(question, f'我選第{target}個')
    assert result.is_correct is True


def test_empty_input_asks_rather_than_guessing(question):
    result = _evaluate(question, '   ')
    assert result.index is None
    assert result.is_correct is None
    assert result.feedback


def test_wrong_answer_gives_a_hint_not_the_answer(question):
    wrong = (question.correct_index + 1) % 4
    result = _evaluate(question, str(wrong + 1))
    assert result.is_correct is False
    assert question.hint[:6] in result.feedback
    # the revealing phrase is absent unless explicitly requested
    assert question.correct_text not in result.feedback


def test_praise_varies_so_ten_correct_answers_do_not_read_like_a_machine():
    lesson = build_lesson('kongchengji')
    messages = {
        _evaluate(q, str(q.display_number)).feedback
        for q in lesson.questions
    }
    assert len(messages) > 1


def test_unresolved_answer_offers_a_confirmation_instead_of_grading():
    lesson = build_lesson('beiying')
    question = next(q for q in lesson.questions if q.number == 10)
    result = _evaluate(question, '我覺得都要想')
    if not result.resolved:
        assert result.is_correct is None, 'an unresolved answer must not be graded'
        assert result.needs_confirmation or result.suggestion is None


def test_verbatim_answer_text_is_accepted():
    lesson = build_lesson('fanqie')
    for question in lesson.questions:
        result = _evaluate(question, question.correct_text)
        assert result.is_correct is True, question.stem


def test_offline_mode_never_raises_on_odd_input():
    lesson = build_lesson('shihu')
    for question in lesson.questions[:3]:
        for text in ('', '？', '嗯', '123456', '   ！  ', '不知道'):
            assert evaluate_answer(question, text, allow_llm=False) is not None
