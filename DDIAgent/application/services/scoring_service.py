"""
APPLICATION: Scoring service za procjenu rizika terapija
"""
from typing import List, Dict, Any
from DDIAgent.domain.entities import Therapy, RiskAssessment, DrugInteraction
from DDIAgent.domain.enums import RiskLevel
from DDIAgent.ml.scoring_model import ScoringModel

class ScoringService:
    """Servis za procjenu rizika terapija koristeći scoring model"""
    
    def __init__(self, scoring_model: ScoringModel):
        self.scoring_model = scoring_model
    
    def assess_therapy_risk(self, therapy: Therapy) -> RiskAssessment:
        """Procjeni rizik terapije"""
        drug_ids = therapy.get_drug_ids()
        
        # Ako ima manje od 2 lijeka, nema interakcija
        if len(drug_ids) < 2:
            return RiskAssessment(
                therapy=therapy,
                total_score=0.0,
                risk_level=RiskLevel.NONE,
                interactions_found=[]
            )
        
        # Izračunaj rizik koristeći scoring model
        risk_report = self.scoring_model.calculate_therapy_risk(drug_ids)
        
        # Odredi nivo rizika na osnovu maksimalnog score-a
        risk_level = RiskLevel.from_score(risk_report['max_risk'])
        
        # Kreiraj RiskAssessment
        assessment = RiskAssessment(
            therapy=therapy,
            total_score=risk_report['total_risk_score'],
            risk_level=risk_level,
            interactions_found=risk_report['all_interactions']
        )
        
        return assessment
    
    def get_detailed_interaction_report(self, therapy: Therapy) -> Dict[str, Any]:
        """Vrati detaljan izvještaj o interakcijama"""
        drug_ids = therapy.get_drug_ids()
        
        if len(drug_ids) < 2:
            return {
                'has_interactions': False,
                'message': 'Terapija ima manje od 2 lijeka'
            }
        
        risk_report = self.scoring_model.calculate_therapy_risk(drug_ids)
        
        return {
            'has_interactions': len(risk_report['all_interactions']) > 0,
            'drug_count': len(drug_ids),
            'interaction_count': risk_report['interaction_count'],
            'total_risk_score': risk_report['total_risk_score'],
            'average_risk': risk_report['average_risk'],
            'max_risk': risk_report['max_risk'],
            'critical_interactions': len(risk_report['critical_interactions']),
            'high_risk_interactions': len(risk_report['high_risk_interactions']),
            'categories': {
                category: len(interactions)
                for category, interactions in risk_report['categories'].items()
            },
            'interactions': [
                {
                    'drug1': inter.drug1_id,
                    'drug2': inter.drug2_id,
                    'type': inter.interaction_type,
                    'score': inter.risk_score,
                    'category': inter.risk_category,
                    'is_critical': inter.is_critical,
                    'is_high_risk': inter.is_high_risk
                }
                for inter in risk_report['all_interactions'][:10]  # Prvih 10
            ]
        }