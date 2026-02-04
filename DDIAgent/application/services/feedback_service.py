from dataclasses import dataclass
from typing import Optional, Dict, Any

from DDIAgent.infrastructure.database import Database
from DDIAgent.infrastructure.therapy_repository import TherapyRepository
from DDIAgent.application.runners.risk_assessment_runner import RiskAssessmentRunner


@dataclass
class FeedbackResult:
    status: str
    message: str
    therapy_id: int
    feedback_type: str
    threshold_before: Optional[float] = None
    threshold_after: Optional[float] = None
    threshold_change: Optional[float] = None
    therapy_snapshot: Optional[Dict[str, Any]] = None
    learning_applied: bool = False
    error: Optional[str] = None


class FeedbackService:
    """
    APPLICATION LAYER: Jedino mjesto gdje je dozvoljena learning/policy logika za feedback.
    Web sloj samo prosljeđuje podatke ovdje.
    """
    def __init__(self, db: Database, repo: TherapyRepository, runner: Optional[RiskAssessmentRunner] = None):
        self.db = db
        self.repo = repo
        self.runner = runner

    def submit_feedback(self, therapy_id: int, feedback_type: str, notes: str = "") -> FeedbackResult:
        feedback_type = (feedback_type or "").lower().strip()
        valid_types = {"confirmed", "false_alarm", "ignored"}
        if feedback_type not in valid_types:
            return FeedbackResult(
                status="error",
                message=f"feedback_type mora biti jedan od: {', '.join(sorted(valid_types))}",
                therapy_id=therapy_id,
                feedback_type=feedback_type,
                error="invalid_feedback_type"
            )

        # 1) PERSIST (repo) – update brojača i historije u DB
        ok = self.repo.update_feedback_counts(int(therapy_id), feedback_type, notes)
        if not ok:
            return FeedbackResult(
                status="error",
                message=f"Terapija {therapy_id} nije pronađena",
                therapy_id=therapy_id,
                feedback_type=feedback_type,
                error="therapy_not_found"
            )

        therapy = self.repo.find_by_id(int(therapy_id))
        if not therapy:
            return FeedbackResult(
                status="error",
                message=f"Terapija {therapy_id} nije pronađena nakon ažuriranja",
                therapy_id=therapy_id,
                feedback_type=feedback_type,
                error="therapy_reload_failed"
            )

        # 2) LEARNING (runner) 
        threshold_before = None
        threshold_after = None
        threshold_change = None
        learning_applied = False

        if self.runner and hasattr(self.runner, "learn_from_feedback"):
            threshold_before = getattr(self.runner, "adaptive_threshold", None)

            warning_severity = "MEDIUM"
            if getattr(therapy, "risk_history", None):
                latest = therapy.risk_history[-1]
                warning_severity = latest.get("risk_level", "MEDIUM")

          
            self.runner.learn_from_feedback(therapy, feedback_type, warning_severity)

            threshold_after = getattr(self.runner, "adaptive_threshold", None)
            if threshold_before is not None and threshold_after is not None:
                threshold_change = round(threshold_after - threshold_before, 2)

            learning_applied = True

       
        therapy_snapshot = {
            "id": therapy.id,
            "patient_id": therapy.patient_id,
            "confirmed_warnings": getattr(therapy, "confirmed_warnings_count", 0),
            "false_alarms": getattr(therapy, "false_alarms_count", 0),
            "ignored_warnings": getattr(therapy, "ignored_warnings_count", getattr(therapy, "ignored_warnings_count", 0)),
            "total_feedback": len(getattr(therapy, "feedback_history", []) or [])
        }

        return FeedbackResult(
            status="success",
            message="Feedback uspješno primljen! Agent će učiti iz vašeg odgovora.",
            therapy_id=therapy.id,
            feedback_type=feedback_type,
            threshold_before=threshold_before,
            threshold_after=threshold_after,
            threshold_change=threshold_change,
            therapy_snapshot=therapy_snapshot,
            learning_applied=learning_applied
        )
