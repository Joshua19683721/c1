# -*- coding: utf-8 -*-
"""ReadExpress-CoT 閱讀快線（國小素養版）— Streamlit entry point.

    streamlit run app.py

Layout follows the specification blueprint:
    header      title, article picker, [第 N 題 / 共 10 題] progress
    left        文章閱讀框（18px+, 寬鬆行距）＋朗讀按鈕
    right       題目卡片、4 個大顆選項按鈕、語音/打字雙輸入、即時回饋
    bottom      完成 10 題後展開：閱讀思考拼圖 ＋ 3 步驟 CoT 解析
"""

from __future__ import annotations

import streamlit as st

from src import ui
from src.content import ARTICLES, TOTAL_QUESTIONS, build_lesson
from src.cot import generate_reflection
from src.evaluator import EvaluationResult, evaluate_answer
from src.llm import default_client
from src.speech import (
    record_audio,
    render_tts,
    stt_status,
    synthesize_mp3,
    transcribe_array,
)

st.set_page_config(
    page_title='ReadExpress-CoT 閱讀快線（國小素養版）',
    page_icon='📚',
    layout='wide',
    initial_sidebar_state='expanded',
)

ui.inject_css()

ARTICLE_LABELS = {
    'beiying': '《背影》朱自清・抒情記敘',
    'chibing': '《吃冰的滋味》古蒙仁・記敘散文',
    'kongchengji': '《空城計》羅貫中・古典白話',
    'shihu': '《臺灣的海洋文化與石滬》・在地文化',
    'fanqie': '《番茄紅了，醫生的臉就綠了》・科普閱讀',
}


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def reset_lesson(article_id: str) -> None:
    st.session_state.rx_article_id = article_id
    st.session_state.rx_q = 0
    st.session_state.rx_answers = []
    st.session_state.rx_correct = []
    st.session_state.rx_last = None
    st.session_state.rx_suggestion = None
    st.session_state.rx_reflection = None
    st.session_state.rx_input = ''
    st.session_state.rx_wrong_attempts = 0


def current_lesson():
    return build_lesson(
        st.session_state.rx_article_id,
        shuffle=st.session_state.get('rx_shuffle', True),
    )


def submit_answer(raw_input: str) -> None:
    """Resolve an answer, record it, and advance when we are sure."""
    lesson = current_lesson()
    index = st.session_state.rx_q
    if index >= len(lesson.questions):
        return

    question = lesson.questions[index]
    result = evaluate_answer(
        question,
        raw_input,
        allow_llm=st.session_state.get('rx_use_llm', True),
    )
    st.session_state.rx_last = result

    if result.index is None:
        # Not confident: stay put, offer the runner-up for confirmation.
        st.session_state.rx_suggestion = result.suggestion
        return

    st.session_state.rx_answers.append(question.options[result.index])
    st.session_state.rx_correct.append(bool(result.is_correct))
    st.session_state.rx_suggestion = None
    st.session_state.rx_input = ''
    st.session_state.rx_q = index + 1

    if st.session_state.rx_q >= len(lesson.questions):
        st.session_state.rx_reflection = generate_reflection(
            lesson,
            st.session_state.rx_answers,
            allow_llm=st.session_state.get('rx_use_llm', True),
        )


defaults = {
    'rx_article_id': ARTICLES[0].id,
    'rx_q': 0,
    'rx_answers': [],
    'rx_correct': [],
    'rx_last': None,
    'rx_suggestion': None,
    'rx_reflection': None,
    'rx_input': '',
    'rx_wrong_attempts': 0,
    'rx_use_llm': True,
    'rx_shuffle': True,
    'rx_audio_seconds': 6.0,
    'rx_last_typed': '',
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown('#### ⚙️ 課堂設定')

    ids = [a.id for a in ARTICLES]
    picked = st.selectbox(
        '選擇文章',
        options=ids,
        format_func=lambda aid: ARTICLE_LABELS[aid],
        index=ids.index(st.session_state.rx_article_id),
        key='rx_article_picker',
    )
    if picked != st.session_state.rx_article_id:
        reset_lesson(picked)

    st.session_state.rx_use_llm = st.toggle(
        '啟用 AI 判讀（需要 API 金鑰）',
        value=bool(st.session_state.rx_use_llm),
        help='關閉後完全離線：數字與選項比對在本機完成，速度最快。',
    )
    st.session_state.rx_shuffle = st.toggle(
        '洗牌選項順序',
        value=bool(st.session_state.rx_shuffle),
        help='原始規格裡 50 題的答案全部都是選項 1。開啟洗牌後，'
             '正確答案會平均落在不同位置，避免學生只記「答案永遠是 A」。',
    )

    st.divider()
    status = default_client().status()
    if status['available'] and st.session_state.rx_use_llm:
        st.success(f'AI 已連線，模型：{status["model"]}')
    elif status['available']:
        st.info('AI 已連線，目前設為離線模式。')
    else:
        st.warning(
            '未設定 API 金鑰，系統使用離線模式。'
            '數字解析與選項比對照常運作；'
            '若想讓 AI 用更自然的語氣回饋，請設定環境變數 DEEPSEEK_API_KEY。'
        )

    st.divider()
    if st.button('🔄 重新開始這篇文章', use_container_width=True):
        reset_lesson(st.session_state.rx_article_id)
        st.rerun()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

lesson = current_lesson()
questions = lesson.questions
position = st.session_state.rx_q
finished = position >= len(questions)

st.markdown(
    '<div class="rx-title">📚 ReadExpress-CoT 閱讀快線'
    '<span style="font-size:1.1rem;color:#6B7A90;font-weight:600;">'
    '（國小素養版）</span></div>'
    f'<div class="rx-subtitle">'
    f'{lesson.display_title}　{lesson.author}　｜　{lesson.genre}</div>',
    unsafe_allow_html=True,
)

progress = position / len(questions)
st.progress(
    min(progress, 1.0),
    text=(
        f'第 {min(position + 1, TOTAL_QUESTIONS)} 題 / 共 {TOTAL_QUESTIONS} 題'
        if not finished
        else f'已完成 {TOTAL_QUESTIONS} 題 🎉'
    ),
)

st.divider()

reading_col, quiz_col = st.columns([5, 6], gap='large')


# ---------------------------------------------------------------------------
# Left — 閱讀與聆聽區
# ---------------------------------------------------------------------------

with reading_col:
    st.markdown('<div class="rx-card">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="rx-reading-title">{lesson.display_title}</div>'
        f'<div class="rx-reading-meta">{lesson.author}　·　{lesson.genre}</div>'
        f'<div class="rx-reading">{lesson.text}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('#### 🔊 朗讀')
    render_tts(lesson.text)

    if st.button('⬇️ 下載文章音檔（需要網路）', key='rx_tts_dl'):
        try:
            st.audio(synthesize_mp3(lesson.text), format='audio/mp3')
        except Exception as exc:  # noqa: BLE001
            st.caption(f'音檔產生失敗：{exc}')


# ---------------------------------------------------------------------------
# Right — 互動學習區
# ---------------------------------------------------------------------------

with quiz_col:
    last: EvaluationResult | None = st.session_state.rx_last

    if finished:
        correct = sum(1 for flag in st.session_state.rx_correct if flag)
        st.markdown('<div class="rx-card">', unsafe_allow_html=True)
        st.markdown(f'## 🎉 完成啦！答對 {correct} / {TOTAL_QUESTIONS} 題')
        st.markdown(
            '你的十個答案已經組裝成一段完整的閱讀理解，'
            '往下看 AI 老師怎麼一步步帶你讀這篇文章。'
        )
        st.markdown('</div>', unsafe_allow_html=True)

        wrong_rows = [
            (i + 1, st.session_state.rx_answers[i])
            for i, ok in enumerate(st.session_state.rx_correct)
            if not ok
        ]
        if wrong_rows:
            with st.expander(f'看看答錯的 {len(wrong_rows)} 題'):
                for number, chosen in wrong_rows:
                    st.markdown(f'- **第 {number} 題** 你選：{chosen}')

        st.markdown('#### 你的 10 個答案')
        st.markdown(
            '\n'.join(
                f'{i + 1}. {text}'
                for i, text in enumerate(st.session_state.rx_answers)
            )
        )
        if st.button('🔄 再讀一次這篇文章', key='rx_again'):
            reset_lesson(st.session_state.rx_article_id)
            st.rerun()

    else:
        question = questions[position]

        st.markdown('<div class="rx-card">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="rx-skill">{question.skill}</div>'
            f'<div class="rx-question">'
            f'<strong>{question.number}.</strong> {question.stem}</div>',
            unsafe_allow_html=True,
        )

        for i, text in enumerate(question.options):
            if st.button(
                ui.option_label(i + 1, text),
                key=f'rx_opt_{question.number}_{i}',
                use_container_width=True,
            ):
                submit_answer(str(i + 1))
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # --- 即時回饋 -----------------------------------------------------
        if last is not None:
            if last.resolved:
                ok = bool(last.is_correct)
                verdict = '✅ 太棒了！答對了' if ok else '💡 再試試看喔！'
                tone = 'ok' if ok else 'no'
                st.markdown(
                    f'<div class="rx-feedback rx-feedback-{tone}">{verdict}'
                    f'<span class="rx-feedback-hint">{last.feedback}</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="rx-feedback rx-feedback-no">🤔 {last.feedback}'
                    f'<span class="rx-feedback-hint">'
                    f'（系統判斷方式：{last.note}）</span></div>',
                    unsafe_allow_html=True,
                )

                suggestion = st.session_state.rx_suggestion
                if suggestion is not None:
                    st.markdown('##### 你是不是想選這個？')
                    if st.button(
                        ui.option_label(suggestion + 1, question.options[suggestion]),
                        key='rx_confirm_suggestion',
                        use_container_width=True,
                    ):
                        submit_answer(str(suggestion + 1))
                        st.rerun()
                    st.caption('不對的話，請再說一次，或直接按上面的選項。')

        # --- 雙輸入控制列 --------------------------------------------------
        st.markdown('###### ⌨️ 打字輸入　/　🎤 語音輸入')

        st.text_input(
            '可以打選項數字（1～4），也可以把答案的內容打出來',
            key='rx_input',
            placeholder='例如：2　或　第三個　或　父親很愛我',
            label_visibility='collapsed',
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                '📤 送出答案', use_container_width=True, type='primary'
            ):
                submit_answer(st.session_state.rx_input)
                st.rerun()
        with c2:
            stt = stt_status()
            if stt.available:
                st.caption(f'🎤 可用　錄音長度：{st.session_state.rx_audio_seconds:.0f} 秒')
            else:
                st.caption(f'🎤 不可用：{stt.reason}')

        with st.expander('🎤 說話選項（在本機辨識，不會上傳）'):
            st.session_state.rx_audio_seconds = st.slider(
                '錄音長度（秒）',
                min_value=3.0,
                max_value=15.0,
                value=float(st.session_state.rx_audio_seconds),
                step=1.0,
                key='rx_audio_len',
            )
            if st.button('● 開始錄音並辨識', use_container_width=True):
                message = ''
                with st.spinner('正在聽你說話…'):
                    try:
                        audio = record_audio(float(st.session_state.rx_audio_seconds))
                        message = transcribe_array(audio)
                    except Exception as exc:  # noqa: BLE001
                        message = ''
                        st.error(f'語音辨識失敗：{exc}')
                if message:
                    st.session_state.rx_input = message
                    st.success(f'我聽到的是：「{message}」，確認後按「送出答案」。')
                    st.rerun()
                else:
                    st.warning('沒有聽清楚，再試一次看看？')


# ---------------------------------------------------------------------------
# Bottom — 思考鏈拼圖區
# ---------------------------------------------------------------------------

reflection = st.session_state.rx_reflection

if finished and reflection is not None:
    st.divider()
    st.markdown('## 🧩 你的閱讀思考拼圖')
    st.markdown(
        f'<div class="rx-puzzle">{reflection.puzzle}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('## 🧠 AI 老師的 CoT 思維鏈解析')
    for step in reflection.steps:
        st.markdown(
            f'<div class="rx-step">'
            f'<div class="rx-step-title">第 {step.number} 步　{step.title}</div>'
            f'<div class="rx-step-body">{step.body}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    badge = 'AI 老師生成' if reflection.is_llm else '離線版生成'
    st.markdown(
        f'<div class="rx-meta">反思來源：{badge}　·　{reflection.note}</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="rx-footer">'
    'ReadExpress-CoT 國小素養版　·　'
    '文章與題目取自 ReadExpress-CoT-Elementary.md 規格檔　·　'
    '提示詞定義於 dsh_config/read_express_cot_pipelines_elem.yaml'
    '</div>',
    unsafe_allow_html=True,
)
