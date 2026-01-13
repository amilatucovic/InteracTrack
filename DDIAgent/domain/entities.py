"""
DOMAIN: Entiteti za DDI agenta
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from .enums import RiskLevel, ActionType, InteractionStatus

@dataclass
class Drug:
    """Lijek u terapiji"""
    drug_id: str
    name: str
    dosage: Optional[str] = None
    risk_profile: Optional[Dict[str, Any]] = None
    
    def __str__(self):
        return f"{self.name} ({self.drug_id})"

@dataclass
class DrugInteraction:
    """Interakcija između dva lijeka"""
    drug1_id: str
    drug2_id: str
    interaction_type: str
    risk_score: float
    risk_category: str
    
    def __str__(self):
        return f"{self.drug1_id}+{self.drug2_id}: {self.interaction_type} (score: {self.risk_score})"
    
    @property
    def is_critical(self) -> bool:
        return self.risk_score >= 4.5
    
    @property
    def is_high_risk(self) -> bool:
        return self.risk_score >= 3.0

@dataclass
class Therapy:
    """Trenutna terapija pacijenta"""
    # OBAVEZNI argumenti BEZ default vrijednosti (moraju biti prvi)
    patient_id: str
    drugs: List[Drug]
    
    # OPCIONALNI argumenti SA default vrijednostima
    id: Optional[int] = None
    status: str = "ACTIVE"  
    start_date: datetime = field(default_factory=datetime.now)
    risk_tolerance: float = 3.0
    ignored_warnings_count: int = 0
    previous_incidents: int = 0
    confirmed_warnings_count: int = 0
    false_alarms_count: int = 0
    risk_history: List[Dict[str, Any]] = field(default_factory=list)
    feedback_history: List[Dict] = field(default_factory=list)
    
    def add_drug(self, drug: Drug):
        """Dodaj lijek u terapiju"""
        self.drugs.append(drug)
    
    def remove_drug(self, drug_id: str):
        """Ukloni lijek iz terapije"""
        self.drugs = [d for d in self.drugs if d.drug_id != drug_id]
    
    def get_drug_ids(self) -> List[str]:
        """Vrati listu ID-jeva lijekova"""
        return [drug.drug_id for drug in self.drugs]
    
    @property
    def drug_count(self) -> int:
        return len(self.drugs)
    
    @property
    def has_multiple_drugs(self) -> bool:
        return len(self.drugs) >= 2
    

    @property
    def last_assessment_time(self) -> Optional[datetime]:
     """Vrati vrijeme posljednje procjene"""
     if not self.risk_history:
        return None
    
     try:
         latest = self.risk_history[-1]
         time_str = latest.get('assessment_time') or latest.get('timestamp')
         if time_str:
             if isinstance(time_str, str):
                return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
     except:
        pass
     return None

    @property
    def last_risk_level(self) -> Optional[RiskLevel]:
     """Vrati posljednji nivo rizika"""
     if not self.risk_history:
        return None
    
     try:
         latest = self.risk_history[-1]
         risk_str = latest.get('risk_level')
         if risk_str:
             return RiskLevel(risk_str)
     except:
         pass
     return None

@dataclass
class RiskAssessment:
    """Procjena rizika za terapiju"""
    # OBAVEZNI
    therapy: Therapy
    total_score: float
    risk_level: RiskLevel
    interactions_found: List[DrugInteraction]
    
    # OPCIONALNI
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertuj u dictionary za serijalizaciju"""
        return {
            'total_score': self.total_score,
            'risk_level': self.risk_level.value,
            'interaction_count': len(self.interactions_found),
            'timestamp': self.timestamp.isoformat(),
            'critical_count': len([i for i in self.interactions_found if i.is_critical]),
            'high_risk_count': len([i for i in self.interactions_found if i.is_high_risk]),
            'interactions': [
                {
                    'drug1_id': inter.drug1_id,
                    'drug2_id': inter.drug2_id,
                    'type': inter.interaction_type,
                    'score': inter.risk_score,
                    'category': inter.risk_category,
                    'is_critical': inter.is_critical
                }
                for inter in self.interactions_found[:10]  # Prvih 10
            ]
        }
    
    @property
    def has_critical_interactions(self) -> bool:
        return any(inter.is_critical for inter in self.interactions_found)
    
    @property
    def critical_count(self) -> int:
        """Broj kritičnih interakcija"""
        return len([i for i in self.interactions_found if i.is_critical])
    
    @property
    def high_risk_count(self) -> int:
        """Broj visoko rizičnih interakcija"""
        return len([i for i in self.interactions_found if i.is_high_risk])
    
    @property
    def interaction_count(self) -> int:
        """Ukupan broj interakcija"""
        return len(self.interactions_found)

@dataclass
class Warning:
    """Upozorenje generirano agentom"""
    # OBAVEZNI
    assessment: RiskAssessment
    action_type: ActionType
    message: str
    priority: str
    
    # OPCIONALNI
    id: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    status: str = "PENDING"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertuj u dictionary"""
        return {
            'id': self.id,
            'action_type': self.action_type.value,
            'message': self.message,
            'priority': self.priority,
            'suggestions': self.suggestions,
            'status': self.status,
            'assessment': self.assessment.to_dict(),
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class UserFeedback:
    """Feedback korisnika na upozorenje"""
    # OBAVEZNI
    warning_id: str
    action: str  # 'ACKNOWLEDGED', 'IGNORED', 'MODIFIED'
    
    # OPCIONALNI
    feedback_text: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_warning_acknowledged(cls, warning: Warning, feedback_text: str = ""):
        return cls(
            warning_id=warning.id,
            action="ACKNOWLEDGED",
            feedback_text=feedback_text
        )

@dataclass
class SystemSettings:
    """Podešavanja agenta"""
    # OBAVEZNI
    risk_thresholds: Dict[RiskLevel, float]
    
    # OPCIONALNI
    learning_enabled: bool = True
    review_threshold: float = 7.0
    last_training_date: Optional[datetime] = None
    
    def __post_init__(self):
        # Osiguraj da svi pragovi postoje
        for level in RiskLevel:
            if level not in self.risk_thresholds:
                self.risk_thresholds[level] = 0.0
    
    def get_threshold_for_level(self, level: RiskLevel) -> float:
        return self.risk_thresholds.get(level, 0.0)

@dataclass
class TherapyPercept:
    """Percept za agenta - ono što agent 'vidi' u SENSE fazi"""
    # OBAVEZNI
    therapy: Therapy
    
    requires_assessment: bool = True
    last_assessment_time: Optional[datetime] = None
    source: str = "THERAPY_QUEUE"
    
    @property
    def should_be_assessed(self) -> bool:
        """Da li terapija treba biti procijenjena?"""
        if not self.requires_assessment:
            return False
        
         # Ako je prošlo više od 1 sata od zadnje procjene
        if self.last_assessment_time:
            time_diff = datetime.now() - self.last_assessment_time
            return time_diff.total_seconds() > 3600  # 1 sat
        
        return True