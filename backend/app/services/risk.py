"""Turn an uncalibrated score into a review decision and a display band.

Low is exactly not flagged, and Medium and High are exactly flagged. The high boundary only moves
the line between Medium and High, so changing it can never change who gets flagged.
"""

from dataclasses import dataclass

from app.models.enums import PredictionDecision, RiskLevel

RISK_SCORE_SCALE = 100.0


@dataclass(frozen=True)
class RiskAssessment:
    """The result of applying the thresholds to one score."""

    decision: PredictionDecision
    risk_level: RiskLevel
    risk_score: float


def assess_score(score: float, threshold: float, high_boundary: float) -> RiskAssessment:
    """Apply the frozen threshold and the high boundary to one score."""
    if high_boundary <= threshold:
        raise ValueError("The high risk boundary must be above the frozen threshold")
    if score < threshold:
        decision, level = PredictionDecision.NOT_FLAGGED, RiskLevel.LOW
    elif score < high_boundary:
        decision, level = PredictionDecision.FLAG_FOR_REVIEW, RiskLevel.MEDIUM
    else:
        decision, level = PredictionDecision.FLAG_FOR_REVIEW, RiskLevel.HIGH
    return RiskAssessment(decision, level, score * RISK_SCORE_SCALE)
