# -*- coding: utf-8 -*-
"""ReadExpress-CoT (國小六年級版) — package root.

Layering, outermost first:

    app.py               Streamlit UI, session state, navigation
    src.cot              Pipeline 2 — reflection + 3-step CoT
    src.evaluator        Pipeline 1 — answer resolution + feedback
    src.llm              OpenAI-compatible backend (optional)
    src.prompts          YAML pipeline loading and rendering
    src.speech           TTS reader + local Whisper STT
    src.parser           tolerant number parsing + fuzzy matching
    src.content          the 5 articles and their 10-step ladders
"""

from __future__ import annotations

__version__ = '1.0.0'
__all__ = ['__version__', 'zh']
