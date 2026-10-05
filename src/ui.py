# -*- coding: utf-8 -*-
"""Visual system for ReadExpress-CoT.

A small Morandi-blue / warm-sand palette tuned for a primary-school reading
room: large type, generous line height, high-contrast ink, and option buttons
big enough for a child to hit reliably.

Streamlit's own theming covers backgrounds; these styles target the elements
that matter pedagogically — the reading pane and the four option cards.
"""

from __future__ import annotations

__all__ = ['COLORS', 'inject_css', 'option_label']

COLORS = {
    'ink': '#2F3B4C',
    'muted': '#6B7A90',
    'morandi': '#7D94AD',
    'morandi_dark': '#5E7288',
    'morandi_soft': '#E4EAF1',
    'sand': '#D8A26A',
    'sand_soft': '#FBF0E1',
    'paper': '#FAF8F5',
    'success': '#6E9E7A',
    'success_soft': '#E6F0E7',
    'warn': '#C98A5B',
    'warn_soft': '#FBEEE2',
}

_CSS = """
<style>
  .rx-title {
    font-size: 2.05rem; font-weight: 800; letter-spacing: .5px;
    color: %(ink)s; margin: 0;
  }
  .rx-subtitle { color: %(muted)s; font-size: 1rem; margin-top: 2px; }

  .rx-card {
    background: %(paper)s;
    border: 1px solid #E4DED4;
    border-radius: 18px;
    padding: 20px 22px;
    box-shadow: 0 2px 10px rgba(47, 59, 76, .05);
  }

  /* 閱讀區：18px 以上、寬鬆行距，長時間閱讀不累 */
  .rx-reading {
    font-size: 18.5px;
    line-height: 2.05;
    color: %(ink)s;
    letter-spacing: .4px;
  }
  .rx-reading-title {
    font-size: 1.28rem; font-weight: 700; color: %(morandi_dark)s;
    margin: 0 0 4px 0;
  }
  .rx-reading-meta { font-size: .85rem; color: %(muted)s; margin-bottom: 12px; }

  .rx-question {
    font-size: 1.32rem; font-weight: 700; line-height: 1.85;
    color: %(ink)s; margin-bottom: 6px;
  }
  .rx-skill {
    display: inline-block; font-size: .78rem; font-weight: 700;
    color: %(morandi_dark)s; background: %(morandi_soft)s;
    border-radius: 999px; padding: 3px 12px; margin-bottom: 10px;
  }

  /* 大顆、易按的選項卡片 */
  div.stButton > button {
    width: 100%%; text-align: left; white-space: normal;
    font-size: 1.02rem; line-height: 1.75; padding: 14px 16px;
    border-radius: 14px; border: 2px solid #DCE3EB;
    background: #FFFFFF; color: %(ink)s; font-weight: 500;
    transition: transform .12s ease, box-shadow .12s ease, border-color .12s ease;
  }
  div.stButton > button:hover {
    border-color: %(morandi)s; color: %(morandi_dark)s;
    box-shadow: 0 4px 14px rgba(125, 148, 173, .22); transform: translateY(-1px);
  }
  div.stButton > button:focus { border-color: %(morandi_dark)s; }

  .rx-correct {
    background: %(success_soft)s; border: 2px solid %(success)s !important;
    color: #2F5B39 !important; font-weight: 700 !important;
  }
  .rx-wrong {
    background: %(warn_soft)s; border: 2px solid %(warn)s !important;
    color: #8A4E20 !important; font-weight: 700 !important;
  }

  .rx-feedback {
    border-radius: 14px; padding: 14px 18px; font-size: 1.05rem;
    line-height: 1.8; font-weight: 600;
  }
  .rx-feedback-ok { background: %(success_soft)s; color: #2F5B39; }
  .rx-feedback-no { background: %(warn_soft)s; color: #8A4E20; }
  .rx-feedback-hint {
    display: block; margin-top: 8px; font-size: .95rem;
    font-weight: 400; color: #6B5637;
  }

  .rx-puzzle {
    background: %(sand_soft)s; border: 1px solid #EBD9BE;
    border-radius: 16px; padding: 20px 22px;
    font-size: 1.08rem; line-height: 2.0; color: %(ink)s;
  }
  .rx-step {
    background: %(morandi_soft)s; border-left: 5px solid %(morandi)s;
    border-radius: 0 14px 14px 0; padding: 14px 18px; margin-bottom: 12px;
  }
  .rx-step-title { font-weight: 800; color: %(morandi_dark)s; font-size: 1.05rem; }
  .rx-step-body { color: %(ink)s; line-height: 1.95; font-size: 1.0rem; }

  .rx-meta { font-size: .8rem; color: %(muted)s; }
  .rx-footer { color: %(muted)s; font-size: .85rem; text-align: center; padding: 18px 0 6px; }
</style>
""" % COLORS


def inject_css() -> None:
    """Apply the ReadExpress-CoT visual system to the current Streamlit page."""
    import streamlit as st

    st.markdown(_CSS, unsafe_allow_html=True)


def option_label(number: int, text: str) -> str:
    """Label shown on an option button."""
    return f'{number}. {text}'
