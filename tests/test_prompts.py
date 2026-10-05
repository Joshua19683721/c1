# -*- coding: utf-8 -*-
"""The YAML pipeline contract: templates load, placeholders fill, nothing goes blank."""

from __future__ import annotations

import pytest

from src import content
from src.prompts import (
    MISSING,
    get_pipeline,
    load_pipelines,
    placeholders_in,
    render_prompt,
)


def test_both_pipelines_are_defined():
    names = {p.name for p in load_pipelines()}
    assert 'option_evaluator' in names
    assert 'cot_reflection_generator' in names


def test_every_pipeline_has_a_step_with_content():
    for pipeline in load_pipelines():
        assert pipeline.steps, pipeline.name
        assert pipeline.first.prompt_template.strip()
        assert pipeline.description.strip()


def test_option_evaluator_expects_the_documented_variables():
    template = get_pipeline('option_evaluator').first.prompt_template
    expected = {
        'current_question', 'opt1', 'opt2', 'opt3', 'opt4',
        'correct_index', 'student_input',
    }
    assert set(placeholders_in(template)) == expected


def test_cot_pipeline_lists_the_ten_answers_separately():
    """The specification writes {{ answer_1 }}…{{ answer_10 }}, not a joined list.

    Kept verbatim on purpose: enumerating them one per line maps more reliably
    to the model's per-question reasoning than a single numbered blob.
    """
    template = get_pipeline('cot_reflection_generator').first.prompt_template
    expected = {'article_title', 'article_text'} | {
        f'answer_{i}' for i in range(1, 11)
    }
    assert set(placeholders_in(template)) == expected
    for i in range(1, 11):
        assert f'{{{{ answer_{i} }}}}' in template


def test_cot_pipeline_uses_the_specified_headings():
    template = get_pipeline('cot_reflection_generator').first.prompt_template
    assert '第一部分：你的閱讀思考拼圖' in template
    assert '第二部分：AI 老師的 CoT 思維鏈解析' in template
    for stage in ('尋找線索', '串聯情意', '大腦昇華'):
        assert stage in template


def test_render_replaces_every_placeholder():
    template = get_pipeline('option_evaluator').first.prompt_template
    rendered = render_prompt(
        template,
        current_question='題目？',
        opt1='甲', opt2='乙', opt3='丙', opt4='丁',
        correct_index=3,
        student_input='乙',
    )
    assert MISSING not in rendered
    assert '乙' in rendered
    assert '{{' not in rendered


def test_missing_values_are_visible_not_blank():
    """A silently empty slot weakens a prompt; a marker is easy to spot."""
    rendered = render_prompt('學生說：{{ student_input }}', other='x')
    assert MISSING in rendered


def test_templates_speak_to_a_sixth_grader():
    for pipeline in load_pipelines():
        text = pipeline.first.prompt_template
        assert '六年級' in text
        assert '你是一位' in text


def test_missing_pipeline_raises_with_a_useful_message():
    with pytest.raises(KeyError) as excinfo:
        get_pipeline('not_a_pipeline')
    assert 'option_evaluator' in str(excinfo.value)


def test_real_question_renders_without_blank_slots():
    lesson = content.build_lesson('shihu')
    question = lesson.questions[0]
    rendered = render_prompt(
        get_pipeline('option_evaluator').first.prompt_template,
        current_question=question.stem,
        opt1=question.options[0], opt2=question.options[1],
        opt3=question.options[2], opt4=question.options[3],
        correct_index=question.display_number,
        student_input='1',
    )
    assert MISSING not in rendered
