# ------------------------------------------------------------------------------------
# 📊 scoring/__init__.py – Technical Scoring Package
#
# This package contains the new 0-8 technical scoring system for D.E.V.I
#
# ✅ score_technical_v1_8pt.py – Main scoring implementation
# ✅ Types and data contracts for scoring system
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

from .score_technical_v1_8pt import score_technical_v1_8pt, TechContext, TechScoreResult

__all__ = ['score_technical_v1_8pt', 'TechContext', 'TechScoreResult']
