"""
DOMAIN: Enum-i za DDI agenta
"""
from enum import Enum

class RiskLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    
    @classmethod
    def from_score(cls, score: float) -> 'RiskLevel':
        """Odredi nivo rizika na osnovu score-a"""
        if score >= 4.5:
            return cls.CRITICAL
        elif score >= 3.5:
            return cls.HIGH
        elif score >= 2.5:
            return cls.MODERATE
        elif score >= 1.0:
            return cls.LOW
        else:
            return cls.NONE

class ActionType(str, Enum):
    """Akcije koje agent može preduzeti (prema uputama)"""
    INFORM = "INFORM"           # Samo informativna poruka
    WARN = "WARN"               # Upozori korisnika
    REQUEST_INFO = "REQUEST_INFO" # Zatraži dodatne informacije
    ESCALATE = "ESCALATE"       # Preporuči konsultaciju s ljekarom
    
    @classmethod
    def from_risk_level(cls, risk_level: RiskLevel, has_critical: bool = False) -> 'ActionType':
        """Odredi akciju na osnovu nivoa rizika"""
        if has_critical or risk_level == RiskLevel.CRITICAL:
            return cls.ESCALATE
        elif risk_level == RiskLevel.HIGH:
            return cls.WARN
        elif risk_level == RiskLevel.MODERATE:
            return cls.REQUEST_INFO
        else:
            return cls.INFORM

class InteractionStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    ASSESSED = "ASSESSED"
    REVIEW_NEEDED = "REVIEW_NEEDED"

class WarningStatus(str, Enum):
    """Status upozorenja"""
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IGNORED = "IGNORED"
    ESCALATED = "ESCALATED"

class TherapyStatus(str, Enum):
    """Status terapije"""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    SUSPENDED = "SUSPENDED"
    MODIFIED = "MODIFIED"