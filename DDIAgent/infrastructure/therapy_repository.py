"""
INFRASTRUKTURA: Repository za Therapy entitete
"""
import sys
import os
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

# Dodaj root folder u Python path za absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.join(current_dir, '..', '..')
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    # Absolute import
    from DDIAgent.domain.entities import Therapy, Drug
    from DDIAgent.infrastructure.database import TherapyDB, Database
except ImportError:
    # Fallback za development
    from domain.entities import Therapy, Drug
    from .database import TherapyDB, Database

import json

class TherapyRepository:
    """Repository za upravljanje Therapy entitetima u bazi"""
    
    def __init__(self, database: Database):
        self.db = database
    
    def save(self, therapy: Therapy) -> Therapy:
        """Sačuvaj Therapy u bazu"""
        with self.db.get_session() as session:
            # Konvertuj domain entity u database model
            therapy_db = self._entity_to_db(therapy, session)
            session.add(therapy_db)
            session.commit()
            session.refresh(therapy_db)
            
            # Vrati entity sa ID-jem
            return self._db_to_entity(therapy_db)
    
    def find_by_id(self, therapy_id: int) -> Optional[Therapy]:
        """Pronađi Therapy po ID-u"""
        with self.db.get_session() as session:
            therapy_db = session.query(TherapyDB).filter_by(id=therapy_id).first()
            if therapy_db:
                return self._db_to_entity(therapy_db)
        return None
    
    def find_all_active(self) -> List[Therapy]:
        """Pronađi sve aktivne terapije"""
        with self.db.get_session() as session:
            therapies_db = session.query(TherapyDB).filter_by(status="ACTIVE").all()
            return [self._db_to_entity(t) for t in therapies_db]
    
    def find_all(self) -> List[Therapy]:
        """Pronađi sve terapije"""
        with self.db.get_session() as session:
            therapies_db = session.query(TherapyDB).all()
            return [self._db_to_entity(t) for t in therapies_db]
    
    def delete(self, therapy_id: int) -> bool:
        """Obriši terapiju"""
        with self.db.get_session() as session:
            therapy_db = session.query(TherapyDB).filter_by(id=therapy_id).first()
            if therapy_db:
                session.delete(therapy_db)
                session.commit()
                return True
        return False
    
    def _entity_to_db(self, therapy: Therapy, session: Session) -> TherapyDB:
     """Konvertuj domain entity u database model"""
    # Proveri da li već postoji u bazi
     if therapy.id:
        therapy_db = session.query(TherapyDB).filter_by(id=therapy.id).first()
        if not therapy_db:
            therapy_db = TherapyDB()
     else:
        therapy_db = TherapyDB()
    
    # Mapiraj polja
     therapy_db.patient_id = therapy.patient_id
     therapy_db.drugs = self._serialize_drugs(therapy.drugs)
     therapy_db.status = therapy.status
     therapy_db.risk_tolerance = therapy.risk_tolerance
     therapy_db.ignored_warnings_count = therapy.ignored_warnings_count
     therapy_db.previous_incidents = therapy.previous_incidents
     therapy_db.risk_history = therapy.risk_history
    
    # DODAJ OVO: sačuvaj feedback historiju
     therapy_db.feedback_history = getattr(therapy, 'feedback_history', [])
    
    # DODAJ OVO: sačuvaj confirmed i false alarm count
     therapy_db.confirmed_warnings_count = getattr(therapy, 'confirmed_warnings_count', 0)
     therapy_db.false_alarms_count = getattr(therapy, 'false_alarms_count', 0)
    
     return therapy_db
    
    def _db_to_entity(self, therapy_db: TherapyDB) -> Therapy:
        """Konvertuj database model u domain entity"""
        # Deserializuj lijekove
        drugs = self._deserialize_drugs(therapy_db.drugs) if therapy_db.drugs else []
        
        # Kreiraj domain entity
        therapy = Therapy(
            patient_id=therapy_db.patient_id,
            drugs=drugs,
            id=therapy_db.id,
            status=therapy_db.status,
            risk_tolerance=therapy_db.risk_tolerance,
            ignored_warnings_count=therapy_db.ignored_warnings_count,
            previous_incidents=therapy_db.previous_incidents,
            risk_history=therapy_db.risk_history if therapy_db.risk_history else [],
            feedback_history=therapy_db.feedback_history if therapy_db.feedback_history else [],
            confirmed_warnings_count=getattr(therapy_db, 'confirmed_warnings_count', 0),
            false_alarms_count=getattr(therapy_db, 'false_alarms_count', 0)
        )
        
        return therapy
    
    def _serialize_drugs(self, drugs: List[Drug]) -> List[dict]:
        """Serializuj listu Drug entiteta u JSON"""
        return [
            {
                'drug_id': drug.drug_id,
                'name': drug.name,
                'dosage': drug.dosage,
                'risk_profile': drug.risk_profile
            }
            for drug in drugs
        ]
    
    def refresh(self, therapy: Therapy) -> Therapy:
        """Eksplicitno osvježi terapiju iz baze"""
        if not therapy.id:
            return therapy
        
        with self.db.get_session() as session:
            # Eksplicitno expire i refresh
            therapy_db = session.query(TherapyDB).filter_by(id=therapy.id).first()
            if therapy_db:
                # Eksplicitno expire sve
                session.expire_all()
                # Refresh
                session.refresh(therapy_db)
                return self._db_to_entity(therapy_db)
        return therapy
    
    def _deserialize_drugs(self, drugs_data: List[dict]) -> List[Drug]:
        """Deserializuj JSON u listu Drug entiteta"""
        return [
            Drug(
                drug_id=drug_dict['drug_id'],
                name=drug_dict['name'],
                dosage=drug_dict.get('dosage'),
                risk_profile=drug_dict.get('risk_profile')
            )
            for drug_dict in drugs_data
        ]
    
    def add_feedback_to_therapy(self, therapy_id: int, feedback_data: dict) -> bool:
        """Dodaj feedback u historiju terapije"""
        with self.db.get_session() as session:
            therapy_db = session.query(TherapyDB).filter_by(id=therapy_id).first()
            if not therapy_db:
                return False
            
            # Inicijaliziraj feedback historiju ako ne postoji
            if therapy_db.feedback_history is None:
                therapy_db.feedback_history = []
            
            # Dodaj novi feedback
            therapy_db.feedback_history.append(feedback_data)
            
            # Ažuriraj brojila
            feedback_type = feedback_data.get('feedback_type')
            if feedback_type == 'confirmed':
                therapy_db.confirmed_warnings_count = getattr(therapy_db, 'confirmed_warnings_count', 0) + 1
            elif feedback_type == 'false_alarm':
                therapy_db.false_alarms_count = getattr(therapy_db, 'false_alarms_count', 0) + 1
            
            session.commit()
            return True
    
    def update_feedback_counts(self, therapy_id: int, feedback_type: str, notes: str = "") -> bool:
     """Ažuriraj feedback brojila i historiju za terapiju"""
     print(f"[REPOSITORY] update_feedback_counts called: therapy_id={therapy_id}, type={feedback_type}, notes={notes}")
    
     with self.db.get_session() as session:
        therapy_db = session.query(TherapyDB).filter_by(id=therapy_id).first()
        if not therapy_db:
            print(f"[REPOSITORY] Terapija {therapy_id} ne postoji!")
            return False
        
        print(f"[REPOSITORY] Pronađena terapija: ID={therapy_db.id}")
        
        # 1. Inicijaliziraj feedback historiju ako ne postoji
        if therapy_db.feedback_history is None:
            therapy_db.feedback_history = []
            print(f"[REPOSITORY] Inicijalizirana prazna feedback_history")
        
        # 2. Ako je feedback_history string (JSON), parsiraj ga
        if isinstance(therapy_db.feedback_history, str):
            print(f"[REPOSITORY] feedback_history je string")
            try:
                current_history = json.loads(therapy_db.feedback_history)
                if isinstance(current_history, list):
                    therapy_db.feedback_history = current_history
                    print(f"[REPOSITORY] Parsiran JSON u listu")
                else:
                    therapy_db.feedback_history = []
                    print(f"[REPOSITORY] Postavljen kao prazna lista (nije bio list)")
            except Exception as e:
                print(f"[REPOSITORY] Greška pri parsiranju JSON: {e}")
                therapy_db.feedback_history = []
        
        # 3. Dodaj novi feedback u historiju
        feedback_record = {
            'timestamp': datetime.now().isoformat(),
            'feedback_type': feedback_type,
            'notes': notes,
            'therapy_id': therapy_id
        }
        
        print(f"[REPOSITORY] Feedback record: {feedback_record}")
        print(f"[REPOSITORY] Pre dodavanja, dužina: {len(therapy_db.feedback_history)}")
        
        # OVO JE KLJUČNO: Dodaj u listu
        therapy_db.feedback_history.append(feedback_record)
        
        print(f"[REPOSITORY] Poslije dodavanja, dužina: {len(therapy_db.feedback_history)}")
        
        # 4. OBAVIJESTI SQLAlchemy da je lista promijenjena!
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(therapy_db, "feedback_history")
        print(f"[REPOSITORY] flag_modified pozvan za feedback_history")
        
        # 5. Ažuriraj odgovarajući brojač
        if feedback_type == 'confirmed':
            old_count = getattr(therapy_db, 'confirmed_warnings_count', 0)
            therapy_db.confirmed_warnings_count = old_count + 1
            print(f"[REPOSITORY] confirmed_warnings_count: {old_count} → {therapy_db.confirmed_warnings_count}")
        elif feedback_type == 'false_alarm':
            old_count = getattr(therapy_db, 'false_alarms_count', 0)
            therapy_db.false_alarms_count = old_count + 1
            print(f"[REPOSITORY] false_alarms_count: {old_count} → {therapy_db.false_alarms_count}")
        elif feedback_type == 'ignored':
            old_count = getattr(therapy_db, 'ignored_warnings_count', 0)
            therapy_db.ignored_warnings_count = old_count + 1
            print(f"[REPOSITORY] ignored_warnings_count: {old_count} → {therapy_db.ignored_warnings_count}")
        
        # 6. Sačuvaj promjene
        session.commit()
        print(f"[REPOSITORY] Commit uspješan!")
        
        # 7. Eksplicitno refresh da vidimo promjene
        session.refresh(therapy_db)
        print(f"[REPOSITORY] Refresh, nova dužina feedback_history: {len(therapy_db.feedback_history) if therapy_db.feedback_history else 0}")
        
        return True
    def get_therapy_with_raw_data(self, therapy_id: int) -> tuple[Optional[Therapy], dict]:
     """Vrati terapiju i raw database podatke"""
     with self.db.get_session() as session:
        therapy_db = session.query(TherapyDB).filter_by(id=therapy_id).first()
        if not therapy_db:
            return None, {}
        
        # Eksplicitno refresh iz baze
        session.refresh(therapy_db)
        
        # Uzmi raw podatke
        raw_data = {
            'confirmed_warnings_count': therapy_db.confirmed_warnings_count,
            'false_alarms_count': therapy_db.false_alarms_count,
            'ignored_warnings_count': therapy_db.ignored_warnings_count,
            'feedback_history_length': len(therapy_db.feedback_history) if therapy_db.feedback_history else 0,
            'updated_at': therapy_db.updated_at
        }
        
        return self._db_to_entity(therapy_db), raw_data


    def get_therapy_feedback_history(self, therapy_id: int) -> List[dict]:
        """Vrati feedback historiju za terapiju"""
        with self.db.get_session() as session:
            therapy_db = session.query(TherapyDB).filter_by(id=therapy_id).first()
            if therapy_db and therapy_db.feedback_history:
                return therapy_db.feedback_history
        return []