# -*- coding: utf-8 -*-
"""Drive the real Streamlit app headlessly via AppTest.

This is the only test that exercises app.py end to end — session state,
button wiring, the reflection section and the reset flow. Everything else
tests the modules underneath.
"""

from __future__ import annotations

import pytest

from streamlit.testing.v1 import AppTest

from src.content import build_lesson

APP_FILE = 'app.py'


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


def test_sidebar_offers_every_article(app):
    """AppTest exposes the formatted labels, which is what a teacher actually reads."""
    labels = list(app.selectbox[0].options)
    assert labels == [
        '《背影》朱自清・抒情記敘',
        '《吃冰的滋味》古蒙仁・記敘散文',
        '《空城計》羅貫中・古典白話',
        '《臺灣的海洋文化與石滬》・在地文化',
        '《番茄紅了，醫生的臉就綠了》・科普閱讀',
    ]


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
    markdown = '\n'.join(m.value for m in app.markdown)
    assert 'rx-reading' in markdown
    assert '最不能忘記的是他的背影' in markdown


@pytest.mark.parametrize('article_id', ['beiying', 'kongchengji'])
def test_answering_every_option_button_finishes_the_lesson(app, article_id):
    app.selectbox[0].select(article_id).run()
    lesson = build_lesson(article_id)

    for question in lesson.questions:
        assert not app.exception, app.exception
        key = f'rx_opt_{question.number}_{question.correct_index}'
        assert key in {b.key for b in app.button}, f'missing option button {key}'
        app.button(key=key).click().run()

    state = app.session_state
    assert state['rx_q'] == 10
    assert len(state['rx_answers']) == 10
    assert all(state['rx_correct'])
    assert not app.exception


def test_completion_shows_the_puzzle_and_the_three_cot_steps(app):
    markdown = '\n'.join(m.value for m in app.markdown)
    assert '你的閱讀思考拼圖' in markdown
    assert 'CoT 思維鏈解析' in markdown
    for number in (1, 2, 3):
        assert f'第 {number} 步' in markdown

    reflection = app.session_state['rx_reflection']
    assert len(reflection.steps) == 3
    assert reflection.puzzle.strip()


def test_restarting_clears_the_lesson(app):
    assert app.session_state['rx_q'] == 10
    app.button(key='rx_again').click().run()
    assert app.session_state['rx_q'] == 0
    assert app.session_state['rx_answers'] == []
    assert app.session_state['rx_reflection'] is None
