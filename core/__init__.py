"""
Cradilot Core Package
确定性评分与测算引擎的统一出口。
"""

from .dms_engine import calculate_dms
from .ars_engine import calculate_ars
from .roi_engine import calculate_roi, resolve_assumptions, assumptions_from_inputs
from .recommendation import (
    generate_pain_points,
    generate_action_roadmap,
    apply_loss_model,
    refresh_roi_milestones,
)

__all__ = [
    "calculate_dms",
    "calculate_ars",
    "calculate_roi",
    "resolve_assumptions",
    "assumptions_from_inputs",
    "generate_pain_points",
    "generate_action_roadmap",
    "apply_loss_model",
    "refresh_roi_milestones",
]
