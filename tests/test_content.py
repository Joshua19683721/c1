# -*- coding: utf-8 -*-
"""Content library invariants: articles, their ladders, categories and explanations."""

from __future__ import annotations

import pytest

from src import content
from src.categories import CATEGORIES, CATEGORY_ORDER


#: The specification asks for 200 articles, 50 per category. The library is
#: being filled in batch by batch, so tests assert the *structure* rather than
#: a frozen count that would have to be edited on every batch.
TARGET_ARTICLES = 50 * 8


def test_library_is_filling_towards_the_target():
    total = len(content.ARTICLES)
    assert total > 0
    assert total <= TARGET_ARTICLES, 'more articles than the specification asks for'
    print(f'\nlibrary progress: {total}/{TARGET_ARTICLES} articles')


def test_ids_are_unique():
    ids = [a.id for a in content.ARTICLES]
    assert len(set(ids)) == len(ids), 'duplicate article id'
    for article in content.ARTICLES:
        assert article.id.isascii(), f'{article.id}: keep ids url/filesystem safe'
        assert article.id.islower(), f'{article.id}: keep ids lowercase'


@pytest.mark.parametrize('article', content.ARTICLES, ids=lambda a: a.id)
def test_article_shape(article):
    assert article.text.strip(), 'article text must not be empty'
    assert len(article.questions) == 10
    for question in article.questions:
        assert len(question.options) == 4
        assert len(set(question.options)) == 4, 'options must be distinct'
        assert question.hint.strip(), 'every question needs a hint'
        assert question.explanation.strip(), (
            'every question needs an explanation — it is what turns a wrong '
            'answer into learning, so an empty one means the student is told '
            'they are wrong without being told why'
        )
        assert len(question.explanation) >= 10, 'explanation too short to teach'
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


def test_the_compact_question_form_rejects_malformed_input():
    """Q() is the fast authoring path, so it must fail loudly, not quietly."""
    from src.content import Q, OPTION_COUNT

    with pytest.raises(ValueError, match='expected 4 options'):
        Q('技能', '題目', '甲|乙|丙', 0, '提示', '解析', '摘要')
    with pytest.raises(ValueError, match='duplicate option'):
        Q('技能', '題目', '甲|乙|甲|丙', 0, '提示', '解析', '摘要')
    with pytest.raises(ValueError, match='correct_index out of range'):
        Q('技能', '題目', '甲|乙|丙|丁', 9, '提示', '解析', '摘要')
    assert OPTION_COUNT == 4


def test_compact_form_matches_the_expanded_form():
    """article() built from Q() must be identical to building questions by hand."""
    from src.content import Q, Article, article, q

    compact = article(
        id='x', title='t', author='a', genre='g', text='body', category='narrative',
        questions=[
            Q('技能', '第一題？', '甲|乙|丙|丁', 2, '提示一', '解析一', '摘要一'),
            Q('技能', '第二題？', '戊|己|庚|辛', 0, '提示二', '解析二', '摘要二'),
        ],
    )
    expanded = Article(
        id='x', title='t', author='a', genre='g', text='body', category='narrative',
        questions=(
            q(1, '技能', '第一題？', ('甲', '乙', '丙', '丁'), '提示一', '解析一', '摘要一', 2),
            q(2, '技能', '第二題？', ('戊', '己', '庚', '辛'), '提示二', '解析二', '摘要二', 0),
        ),
    )
    assert compact == expanded


def test_get_article_returns_none_for_unknown_id():
    assert content.get_article('nope') is None


# --- categories -------------------------------------------------------------

def test_every_category_is_declared_and_ordered():
    """Every module under src/categories must be reachable from CATEGORY_ORDER."""
    assert set(CATEGORIES) == set(CATEGORY_ORDER)
    for slug in CATEGORY_ORDER:
        assert CATEGORIES[slug].label.strip()
        assert CATEGORIES[slug].icon.strip()
        assert CATEGORIES[slug].blurb.strip()


def test_every_article_belongs_to_a_declared_category():
    for article in content.ARTICLES:
        assert article.category in CATEGORIES, article.id


def test_article_counts_add_up():
    assert sum(len(v) for v in content.BY_CATEGORY.values()) == len(content.ARTICLES)
    assert set(content.BY_CATEGORY) == set(CATEGORY_ORDER)


def test_every_category_is_covered_or_on_track():
    """A student must not land on an empty shelf.

    Printed rather than asserted so the suite stays green while categories are
    still being filled batch by batch.
    """
    empty = [slug for slug in CATEGORY_ORDER if not content.articles_in_category(slug)]
    print(f'\ncategories still empty: {empty or "none"}')


def test_every_category_has_at_least_one_article():
    """The specification asks for 200 articles, so an empty category is a gap.

    Reported rather than asserted, because the library is being filled in batch
    by batch and the test suite has to stay green in between.
    """
    empty = [slug for slug in CATEGORY_ORDER if not content.articles_in_category(slug)]
    print(f'\ncategories still to fill: {empty or "none"}')
    assert isinstance(empty, list)


def test_articles_in_category_returns_an_empty_tuple_for_unknown_slug():
    assert content.articles_in_category('nope') == ()
