"""
INFRASTRUKTURA: Čitanje podataka iz fajlova
"""
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any
import os

class FileDataLoader:
    """Učitava podatke iz CSV i JSON fajlova"""
    
    def __init__(self, data_dir: str = None):
        # Ako nije specificirano, koristi default relativnu putanju
        if data_dir is None:
            # Uzmi base dir projekta
            base_dir = Path(__file__).parent.parent.parent
            self.data_dir = base_dir / "data"
        else:
            self.data_dir = Path(data_dir)
        
    def load_interactions(self) -> pd.DataFrame:
        """Učitaj interakcije sa score-ovima"""
        file_path = self.data_dir / "DDI_with_scores.csv"
        if not file_path.exists():
            raise FileNotFoundError(f"Interactions file not found: {file_path}")
        
        df = pd.read_csv(file_path)
        print(f"✅ Učitano {len(df)} interakcija")
        return df
    
    def load_drug_lookup(self) -> Dict[str, str]:
        """Učitaj lookup tabelu lijekova"""
        file_path = self.data_dir / "drug_lookup.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Drug lookup file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ Učitano {len(data)} lijekova")
        return data
    
    def load_scoring_config(self) -> Dict[str, Any]:
        """Učitaj scoring konfiguraciju"""
        file_path = self.data_dir / "scoring_config.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Scoring config not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data