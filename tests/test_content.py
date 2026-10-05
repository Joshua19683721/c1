# -*- coding: utf-8 -*-
"""Content library invariants: the 5 articles and their 10-step ladders."""

from __future__ import annotations

import pytest

from src import content


def test_spec_article_count():
    assert len(content.ARTICLES) == 5


def test_ids_are_unique():
    ids = [a.id for a in content.ARTICLES]
    assert len(set(ids)) == 5


@pytest.mark.parametrize('article', content.ARTICLES, ids=lambda a: a.id)
def test_article_shape(article):
    assert article.text.strip(), 'article text must not be empty'
    assert len(article.questions) == 10
    for question in article.questions:
        assert len(question.options) == 4
        assert len(set(question.options)) == 4, 'options must be distinct'
        assert question.hint.strip(), 'every question needs a hint'
        assert 0 <= question.correct_index < 4


@pytest.mark.parametrize('article', content.ARTICLES, ids=lambda a: a.id)
def test_question_numbers_are_one_to_ten(article):
    assert [q.number for q in article.questions] == list(range(1, 11))


@pytest.mark.parametrize('article', content.ARTICLES, ids=lambda a: a.id)
def test_shuffle_is_deterministic(article):
    first = content.build_lesson(article.id)
    second = content.build_lesson(article.id)
    for a, b in zip(first.questions, second.questions):
        assert a.options == b.options
        assert a.correct_index == b.correct_index


@pytest.mark.parametrize('article', content.ARTICLES, ids=lambda a: a.id)
def test_shuffle_preserves_the_correct_answer(article):
    plain = content.build_lesson(article.id, shuffle=False)
    shuffled = content.build_lesson(article.id, shuffle=True)
    for before, after in zip(plain.questions, shuffled.questions):
        assert before.correct_text == after.correct_text
        assert after.options[after.correct_index] == before.correct_text


@pytest.mark.parametrize('article', content.ARTICLES, ids=lambda a: a.id)
def test_shuffle_does_not_leave_the_answer_always_first(article):
    positions = [q.display_number for q in content.build_lesson(article.id).questions]
    assert len(set(positions)) >= 3, f'option order still predictable: {positions}'


def test_shuffle_false_reproduces_specification_layout():
    lesson = content.build_lesson('beiying', shuffle=False)
    assert all(q.correct_index == 0 for q in lesson.questions)


def test_unknown_article_raises():
    with pytest.raises(KeyError):
        content.build_lesson('does-not-exist')


def test_get_article_returns_none_for_unknown_id():
    assert content.get_article('nope') is None
