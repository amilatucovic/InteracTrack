"""
ML: Scoring model za DDI interakcije
"""
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
import sys
import os

# Dodaj DDIAgent folder u Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
ddi_agent_dir = os.path.join(current_dir, '..')
if ddi_agent_dir not in sys.path:
    sys.path.append(ddi_agent_dir)

try:
    from domain.entities import DrugInteraction
    print("✅ Uspješno importiran DrugInteraction iz domain.entities")
except ImportError as e:
    print(f"⚠️ Greška pri importu: {e}")
    # Fallback
    class DrugInteraction:
        def __init__(self, drug1_id, drug2_id, interaction_type, risk_score, risk_category):
            self.drug1_id = drug1_id
            self.drug2_id = drug2_id
            self.interaction_type = interaction_type
            self.risk_score = risk_score
            self.risk_category = risk_category


class ScoringModel:
    """Model za procjenu rizika interakcija"""
    
    def __init__(self, data_path: str = "data/DDI_with_scores.csv"):
        """Inicijalizuj model sa putanjom do podataka"""
        try:
            self.df = pd.read_csv(data_path)
            self._build_lookup()
            print(f"✅ Scoring model učitano {len(self.df)} interakcija")
        except Exception as e:
            print(f"❌ Greška pri učitavanju scoring modela: {e}")
            self.df = pd.DataFrame()
            self.interaction_lookup = {}
    
    def _build_lookup(self):
        """Kreira lookup tabelu za brzo pronalaženje"""
        self.interaction_lookup = {}
        
        for _, row in self.df.iterrows():
            key = self._create_key(row['drug1_id'], row['drug2_id'])
            if key not in self.interaction_lookup:
                self.interaction_lookup[key] = []
            
            self.interaction_lookup[key].append({
                'type': row['interaction_type'],
                'score': row['risk_score'],
                'category': row['risk_category']
            })
    
    def _create_key(self, drug1_id: str, drug2_id: str) -> str:
        """Kreira normalizovani ključ za par lijekova"""
        sorted_ids = sorted([drug1_id, drug2_id])
        return f"{sorted_ids[0]}|{sorted_ids[1]}"
    
    def find_interactions(self, drug1_id: str, drug2_id: str) -> List[DrugInteraction]:
        """Pronađi interakcije između dva lijeka"""
        key = self._create_key(drug1_id, drug2_id)
        
        if key not in self.interaction_lookup:
            return []
        
        interactions = []
        for inter_data in self.interaction_lookup[key]:
            interactions.append(DrugInteraction(
                drug1_id=drug1_id,
                drug2_id=drug2_id,
                interaction_type=inter_data['type'],
                risk_score=inter_data['score'],
                risk_category=inter_data['category']
            ))
        
        return interactions
    
    def calculate_therapy_risk(self, drug_ids: List[str]) -> Dict[str, Any]:
        """Izračunaj ukupni rizik terapije sa više lijekova"""
        all_interactions = []
        total_risk_score = 0
        
        # Pronađi sve interakcije između svih parova lijekova
        for i in range(len(drug_ids)):
            for j in range(i + 1, len(drug_ids)):
                interactions = self.find_interactions(drug_ids[i], drug_ids[j])
                all_interactions.extend(interactions)
                total_risk_score += sum(inter.risk_score for inter in interactions)
        
        # Izračunaj maksimalni i prosječni rizik
        max_risk = max((inter.risk_score for inter in all_interactions), default=0)
        avg_risk = total_risk_score / len(all_interactions) if all_interactions else 0
        
        # Grupiši interakcije po kategorijama
        categories = {}
        for inter in all_interactions:
            if inter.risk_category not in categories:
                categories[inter.risk_category] = []
            categories[inter.risk_category].append(inter)
        
        return {
            'drug_count': len(drug_ids),
            'interaction_count': len(all_interactions),
            'total_risk_score': total_risk_score,
            'average_risk': avg_risk,
            'max_risk': max_risk,
            'critical_interactions': [inter for inter in all_interactions if inter.risk_score >= 4],
            'high_risk_interactions': [inter for inter in all_interactions if inter.risk_score >= 3],
            'categories': categories,
            'all_interactions': all_interactions
        }