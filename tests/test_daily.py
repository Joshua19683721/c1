# -*- coding: utf-8 -*-
"""每天一篇：分類的年度排程，以及「今日課程」的挑選規則。"""

from __future__ import annotations

from datetime import date

import pytest

from src import content
from src.categories import CATEGORY_ORDER
from tools.export_site_data import build_payload


def test_every_article_has_a_slot_inside_the_year():
    for article in content.ARTICLES:
        assert 1 <= article.day <= content.DAYS_IN_YEAR, article.id


def test_slots_are_unique_within_a_category():
    for slug in CATEGORY_ORDER:
        days = [a.day for a in content.BY_CATEGORY[slug]]
        assert len(set(days)) == len(days), f'{slug}: duplicate day'


@pytest.mark.parametrize('slug', CATEGORY_ORDER)
def test_every_category_answers_every_day_of_the_year(slug):
    for day in range(1, content.DAYS_IN_YEAR + 1):
        article = content.article_for_day(slug, day)
        assert article is not None, f'{slug} day {day}'
        assert article.category == slug


def test_a_filled_category_serves_its_own_slot():
    for slug in CATEGORY_ORDER:
        for article in content.BY_CATEGORY[slug]:
            assert content.article_for_day(slug, article.day) is article


def test_a_short_category_cycles_instead_of_going_blank():
    slug = 'expository'
    group = content.BY_CATEGORY[slug]
    assert len(group) < content.DAYS_IN_YEAR, 'pick a category that is not full yet'
    assert content.article_for_day(slug, 300) is group[(300 - 1) % len(group)]


def test_the_leap_day_reuses_the_last_slot():
    assert content.daily_article('narrative', date(2024, 12, 31)) is (
        content.article_for_day('narrative', content.DAYS_IN_YEAR)
    )


def test_today_lessons_covers_every_category():
    lessons = content.today_lessons(date(2024, 3, 5))
    assert [slug for slug, _ in lessons] == list(CATEGORY_ORDER)
    for slug, article in lessons:
        assert article is not None and article.category == slug


def test_the_same_date_always_picks_the_same_article():
    first = content.daily_article('narrative', date(2025, 6, 1))
    second = content.daily_article('narrative', date(2025, 6, 1))
    assert first is second


def test_the_exported_calendar_matches_the_library():
    payload = build_payload()
    assert payload['daysInYear'] == content.DAYS_IN_YEAR
    by_id = {a.id: a for a in content.ARTICLES}
    assert set(payload['daily']) == set(CATEGORY_ORDER)
    for slug, ids in payload['daily'].items():
        assert len(ids) == content.DAYS_IN_YEAR, slug
        for day, article_id in enumerate(ids, start=1):
            assert by_id[article_id].category == slug, (slug, day)
            assert article_id == content.article_for_day(slug, day).id, (slug, day)


def test_exported_articles_carry_their_day():
    payload = build_payload()
    for article in payload['articles']:
        assert 1 <= article['day'] <= content.DAYS_IN_YEAR, article['id']
