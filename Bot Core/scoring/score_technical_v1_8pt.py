# ------------------------------------------------------------------------------------
# 📊 score_technical_v1_8pt.py – 0-8 Technical Scoring System
#
# This module implements the new 0-8 technical scoring system for D.E.V.I
# Replaces the legacy weighted scoring with a clean, deterministic approach.
#
# ✅ TechContext – Input data contract for scoring
# ✅ TechScoreResult – Output data contract for scoring results
# ✅ score_technical_v1_8pt() – Main scoring function
# ✅ Component scoring functions (BOS, FVG, OB, etc.)
# ✅ EMA alignment validation
#
# Scoring Rules:
# - BOS: 2.0 points (confirmed + direction match)
# - FVG: 2.0 points (valid + not filled + direction match)
# - OB Tap: 1.5 points (tap + direction match)
# - Rejection: 1.0 points (at key level + confirmed + direction match)
# - Sweep: 1.0 points (recent + reversal confirmed + direction match)
# - Engulfing: 0.5 points (present + direction match)
# - Total capped at 8.0
#
# Author: Terrence Ndifor (Terry)
# Project: Smart Multi-Timeframe Trading Bot
# ------------------------------------------------------------------------------------

from typing import Literal, Dict, Tuple
from dataclasses import dataclass
import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'Data Files'))
from config import CONFIG


@dataclass
class TechContext:
    """Input data contract for technical scoring"""
    dir: Literal["BUY", "SELL"]         # proposed technical direction
    session: Literal["asia", "london", "newyork", "post_session", "pm"]
    symbol: str
    
    # Structure signals
    bos_confirmed: bool
    bos_direction: Literal["BUY", "SELL", "NEUTRAL"]
    fvg_valid: bool
    fvg_filled: bool
    fvg_direction: Literal["BUY", "SELL", "NEUTRAL"]
    ob_tap: bool
    ob_direction: Literal["BUY", "SELL", "NEUTRAL"]
    rejection_at_key_level: bool
    rejection_confirmed_next: bool
    rejection_direction: Literal["BUY", "SELL", "NEUTRAL"]
    sweep_recent: bool
    sweep_reversal_confirmed: bool
    sweep_direction: Literal["BUY", "SELL", "NEUTRAL"]
    engulfing_present: bool
    engulfing_direction: Literal["BUY", "SELL", "NEUTRAL"]
    
    # Trend context
    ema21: float
    ema50: float
    ema200: float
    price: float
    
    # HTF confirms
    ema_aligned_m15: bool
    ema_aligned_h1: bool


@dataclass
class TechScoreResult:
    """Output data contract for technical scoring results"""
    score_8pt: float               # 0.0..8.0
    technical_direction: Literal["BUY", "SELL", "HOLD"]
    ema_alignment_ok: bool         # M15 and H1 alignment both true
    components: Dict[str, float]   # Component breakdown


def score_bos(ctx: TechContext) -> float:
    """Score Break of Structure - 0.0 or 2.0 points"""
    if ctx.bos_confirmed and ctx.bos_direction == ctx.dir:
        return 2.0
    return 0.0


def score_fvg(ctx: TechContext) -> float:
    """Score Fair Value Gap - 0.0 or 2.0 points (requires valid and not filled)"""
    if ctx.fvg_valid and not ctx.fvg_filled and ctx.fvg_direction == ctx.dir:
        return 2.0
    return 0.0


def score_ob_tap(ctx: TechContext) -> float:
    """Score Order Block Tap - 0.0 or 1.5 points"""
    if ctx.ob_tap and ctx.ob_direction == ctx.dir:
        return 1.5
    return 0.0


def score_rejection(ctx: TechContext) -> float:
    """Score Rejection - 0.0 or 1.0 points (requires at key level and confirmed next)"""
    if (ctx.rejection_at_key_level and 
        ctx.rejection_confirmed_next and 
        ctx.rejection_direction == ctx.dir):
        return 1.0
    return 0.0


def score_sweep(ctx: TechContext) -> float:
    """Score Liquidity Sweep - 0.0 or 1.0 points (requires recent and reversal confirmed)"""
    if (ctx.sweep_recent and 
        ctx.sweep_reversal_confirmed and 
        ctx.sweep_direction == ctx.dir):
        return 1.0
    return 0.0


def score_engulfing(ctx: TechContext) -> float:
    """Score Engulfing Pattern - 0.0 or 0.5 points"""
    if ctx.engulfing_present and ctx.engulfing_direction == ctx.dir:
        return 0.5
    return 0.0


def ema_alignment_ok(ctx: TechContext) -> bool:
    """Check if M15 EMA alignment is true (H1 is optional for better trade opportunities)"""
    # For now, only require M15 alignment to allow more trade opportunities
    # H1 alignment is preferred but not mandatory
    return ctx.ema_aligned_m15


def score_technical_v1_8pt(ctx: TechContext) -> TechScoreResult:
    """
    Returns the 0-8 score and component breakdown.
    
    Rules:
      - Add points only when the signal direction matches ctx.dir
      - Cap total at 8.0
      - EMA alignment OK only if both M15 and H1 aligned with ctx.dir
    """
    
    # Score each component
    bos_score = score_bos(ctx)
    fvg_score = score_fvg(ctx)
    ob_score = score_ob_tap(ctx)
    rejection_score = score_rejection(ctx)
    sweep_score = score_sweep(ctx)
    engulfing_score = score_engulfing(ctx)
    
    # Calculate total score (capped at 8.0)
    total_score = min(
        bos_score + fvg_score + ob_score + rejection_score + sweep_score + engulfing_score,
        8.0
    )
    
    # Check EMA alignment
    ema_aligned = ema_alignment_ok(ctx)
    
    # Determine technical direction
    if total_score > 0 and ema_aligned:
        technical_direction = ctx.dir
    else:
        technical_direction = "HOLD"
    
    # Build component breakdown
    components = {
        "bos": bos_score,
        "fvg": fvg_score,
        "ob_tap": ob_score,
        "rejection": rejection_score,
        "sweep": sweep_score,
        "engulfing": engulfing_score
    }
    
    return TechScoreResult(
        score_8pt=total_score,
        technical_direction=technical_direction,
        ema_alignment_ok=ema_aligned,
        components=components
    )


# Export the main function and types
__all__ = [
    'score_technical_v1_8pt',
    'TechContext', 
    'TechScoreResult',
    'score_bos',
    'score_fvg', 
    'score_ob_tap',
    'score_rejection',
    'score_sweep',
    'score_engulfing',
    'ema_alignment_ok'
]
