# -*- coding: utf-8 -*-
"""Drive the real Streamlit app headlessly via AppTest.

This is the only test that exercises app.py end to end — session state,
button wiring, the explanation card, the retry flow and the category picker.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from streamlit.testing.v1 import AppTest

from src.categories import CATEGORIES
from src.content import articles_in_category, build_lesson, get_article

# Absolute, because Streamlit changed how AppTest resolves relative paths:
# older versions resolved against the current working directory, newer ones
# resolve against the *calling file*, which turns 'app.py' into tests/app.py.
# Caught by CI on streamlit 1.65; an absolute path works on both.
APP_FILE = str(Path(__file__).resolve().parent.parent / 'app.py')


@pytest.fixture(scope='module')
def app():
    instance = AppTest.from_file(APP_FILE, default_timeout=60)
    instance.run()
    assert not instance.exception, instance.exception
    return instance


def test_app_starts_cleanly(app):
    markdown = '\n'.join(m.value for m in app.markdown)
    assert 'ReadExpress-CoT 閱讀快線' in markdown
    assert '國小素養版' in markdown
    assert not app.exception


def test_progress_reports_the_current_rung_in_the_specified_format(app):
    """The specification asks for [第 N 題 / 共 10 題]."""
    progress = app.get('progress')
    assert progress, 'no progress indicator rendered'
    assert progress[0].text == '第 1 題 / 共 10 題'
    assert progress[0].value == 0


def test_four_big_option_buttons_are_rendered(app):
    keys = {b.key for b in app.button if b.key and b.key.startswith('rx_opt_1_')}
    assert keys == {'rx_opt_1_0', 'rx_opt_1_1', 'rx_opt_1_2', 'rx_opt_1_3'}


def test_reading_pane_shows_the_article(app):
    _select_category(app, 'narrative')
    _select_article(app, 'beiying')
    markdown = '\n'.join(m.value for m in app.markdown)
    assert 'rx-reading' in markdown
    assert '最不能忘記的是他的背影' in markdown


def test_sidebar_groups_articles_by_category(app):
    """First selectbox is the category, second is the article within it."""
    categories = list(app.selectbox[0].options)
    assert categories, 'no categories offered'
    for slug in CATEGORIES:
        if articles_in_category(slug):
            label = (
                f"{CATEGORIES[slug].icon} {CATEGORIES[slug].label}"
                f"（{len(articles_in_category(slug))} 篇）"
            )
            assert label in categories

    assert list(app.selectbox[1].options), 'no articles in the first category'


def _select_category(app, slug):
    # set_value takes the option *value* (the slug), not its position — passing
    # an index stores the int as the widget value and format_func blows up.
    app.selectbox[0].set_value(slug)
    app.run()
    assert not app.exception, app.exception


def _select_article(app, article_id):
    app.selectbox[1].set_value(article_id)
    app.run()
    assert not app.exception, app.exception


def _play_correct(app, article_id):
    """Answer every question correctly, clicking 下一題 between them."""
    _select_category(app, get_article(article_id).category)
    _select_article(app, article_id)

    lesson = build_lesson(article_id)
    for question in lesson.questions:
        assert not app.exception, app.exception
        key = f'rx_opt_{question.number}_{question.correct_index}'
        assert key in {b.key for b in app.button}, f'missing option button {key}'
        app.button(key=key).click().run()
        assert not app.exception, app.exception
        assert 'rx_next' in {b.key for b in app.button}, 'no 下一題 after an answer'
        app.button(key='rx_next').click().run()

    state = app.session_state
    assert state['rx_q'] == 10
    assert len(state['rx_answers']) == 10
    assert all(state['rx_correct'])
    assert not app.exception


@pytest.mark.parametrize('article_id', ['beiying', 'kongchengji'])
def test_answering_every_option_button_finishes_the_lesson(app, article_id):
    _play_correct(app, article_id)


def test_completion_shows_the_puzzle_and_the_three_cot_steps(app):
    markdown = '\n'.join(m.value for m in app.markdown)
    assert '你的閱讀思考拼圖' in markdown
    assert 'CoT 思維鏈解析' in markdown
    for number in (1, 2, 3):
        assert f'第 {number} 步' in markdown

    reflection = app.session_state['rx_reflection']
    assert len(reflection.steps) == 3
    assert reflection.puzzle.strip()


def test_a_wrong_answer_shows_the_explanation_and_allows_a_retry(app):
    _select_category(app, 'narrative')
    _select_article(app, 'beiying')

    question = build_lesson(app.session_state['rx_article_id']).questions[0]
    wrong = (question.correct_index + 1) % 4

    app.button(key=f'rx_opt_{question.number}_{wrong}').click().run()
    assert not app.exception, app.exception

    markdown = '\n'.join(m.value for m in app.markdown)
    assert '正確答案與解析' in markdown
    assert question.explanation in markdown
    labels = [b.label for b in app.button]
    assert '🔄 再試一次' in labels
    assert '➡️ 懂了，看下一題' in labels
    assert app.session_state['rx_q'] == 0, 'a wrong answer advanced the lesson'

    app.button(key='rx_retry').click().run()
    markdown = '\n'.join(m.value for m in app.markdown)
    assert '正確答案與解析' not in markdown
    assert app.session_state['rx_q'] == 0

    app.button(key=f'rx_opt_{question.number}_{question.correct_index}').click().run()
    markdown = '\n'.join(m.value for m in app.markdown)
    assert '為什麼是這個答案？' in markdown
    assert app.session_state['rx_q'] == 0, 'a correct answer advanced on its own'
    labels = [b.label for b in app.button]
    assert '➡️ 下一題' in labels
    assert '🔄 再試一次' not in labels, 'a correct answer should not offer a retry'

    app.button(key='rx_next').click().run()
    assert app.session_state['rx_q'] == 1


def test_restarting_clears_the_lesson(app):
    # Self-contained: this fixture is module-scoped, so the test must not rely
    # on where the previous one happened to stop.
    _select_category(app, 'narrative')
    _select_article(app, 'beiying')
    app.button(key='rx_restart').click().run()

    assert app.session_state['rx_q'] == 0
    assert not any(app.session_state['rx_answers'])
    assert app.session_state['rx_reflection'] is None
    assert app.session_state['rx_last'] is None
