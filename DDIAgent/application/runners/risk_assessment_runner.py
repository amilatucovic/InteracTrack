"""
RUNNER: Risk Assessment Agent (Sense→Think→Act→Learn)
Prema uputama: mora biti jasno razdvojeno Sense→Think→Act→Learn
"""
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from DDIAgent.domain.entities import Therapy, TherapyPercept, RiskAssessment, Warning, Drug
from DDIAgent.domain.enums import ActionType, RiskLevel
from DDIAgent.application.services.scoring_service import ScoringService
from DDIAgent.infrastructure.database import Database
from DDIAgent.infrastructure.therapy_repository import TherapyRepository
from DDIAgent.ml.scoring_model import ScoringModel
from DDIAgent.application.services.scoring_service import ScoringService

@dataclass
class TickResult:
    """Rezultat jednog tick-a agenta (prema Pravilu #6)"""
    has_work: bool
    therapy_id: Optional[int] = None
    patient_id: Optional[str] = None
    drug_count: Optional[int] = None
    assessment: Optional[RiskAssessment] = None
    warning: Optional[Warning] = None
    action_taken: Optional[ActionType] = None
    timestamp: datetime = datetime.now()
    
    def to_dict(self):
        """Konvertuj u dictionary za Web layer (prema uputama)"""
        if not self.has_work:
            return {"has_work": False, "timestamp": self.timestamp.isoformat()}
        
        result = {
            "has_work": True,
            "therapy_id": self.therapy_id,
            "patient_id": self.patient_id,
            "drug_count": self.drug_count,
            "action_taken": self.action_taken.value if self.action_taken else None,
            "timestamp": self.timestamp.isoformat()
        }
        
        if self.assessment:
            result["assessment"] = self.assessment.to_dict()
        
        if self.warning:
            result["warning"] = self.warning.to_dict()
        
        return result

class RiskAssessmentRunner:
    """
    Runner za procjenu rizika terapije.
    IMPLEMENTIRA: Sense→Think→Act→Learn ciklus (prema uputama)
    """
    
    def __init__(self, 
             database: Database, 
             scoring_service: ScoringService,
             therapy_repository: TherapyRepository):
    
     self.db = database
     self.scoring_service = scoring_service
     self.therapy_repository = therapy_repository
    
     # Učitaj prag iz baze
     self.adaptive_threshold = self._load_threshold_from_db()
    
    # ADAPTIVNI PRAVILNIK (deo politike ponašanja)
     self.learning_rate = 0.1
     self.user_feedback_history = []
    
    # POBOLJŠANO UČENJE:
     self.feedback_learning_rate = 0.15
     self.confirmed_threshold_adjustment = -0.2
     self.ignored_threshold_adjustment = 0.3
     self.false_alarm_penalty = 0.5
    
     # UČITAJ STATISTIKE IZ BAZE ← OVO JE NOVO!
     self._load_learning_stats_from_db()
    
     print(f"[RUNNER_INIT] Inicijaliziran sa pragom: {self.adaptive_threshold}")
     print(f"[RUNNER_INIT] Statistike: {self.learning_stats}")
    
    def _load_threshold_from_db(self):
      """Učitaj prag iz agent_learning tabele"""
      try:
        with self.db.get_session() as session:
            from DDIAgent.infrastructure.database import AgentLearningDB
            record = session.query(AgentLearningDB).first()
            if record:
                return record.adaptive_threshold
      except:
        pass
      return 3.0  # Default

    def _save_threshold_to_db(self):
     """Sačuvaj prag u agent_learning tabelu"""
     try:
        with self.db.get_session() as session:
            from DDIAgent.infrastructure.database import AgentLearningDB
            record = session.query(AgentLearningDB).first()
            if not record:
                record = AgentLearningDB(adaptive_threshold=self.adaptive_threshold)
                session.add(record)
            else:
                record.adaptive_threshold = self.adaptive_threshold
            session.commit()
     except Exception as e:
        print(f"⚠️  Greška pri čuvanju praga u bazu: {e}")

    def learn_from_feedback(self, therapy: Therapy, feedback_type: str, warning_severity: str = "MEDIUM"):
        """Uči iz korisničkog feedback-a - KOMPLETNA IMPLEMENTACIJA"""
        print(f"[LEARN_FROM_FEEDBACK] Primljen feedback '{feedback_type}' za terapiju {therapy.id}")
        
        self._adjust_threshold_from_feedback(feedback_type, warning_severity)
        
        self._update_learning_stats(feedback_type)
        
        self._save_threshold_to_db()
        
        print(f"[LEARN_FROM_FEEDBACK] Novi prag: {self.adaptive_threshold:.2f}")
        return therapy
    
    def _update_therapy_with_feedback(self, therapy: Therapy, feedback_type: str, warning_severity: str):
     """Ažuriraj terapiju sa novim feedback-om"""
    # Inicijaliziraj feedback historiju ako ne postoji
     if not hasattr(therapy, 'feedback_history'):
        therapy.feedback_history = []
    
    # Dodaj novi feedback record
     feedback_record = {
        'timestamp': datetime.now().isoformat(),
        'feedback_type': feedback_type,
        'warning_severity': warning_severity,
        'adaptive_threshold_before': self.adaptive_threshold,
        'therapy_id': therapy.id,
        'patient_id': therapy.patient_id
     }
    
     therapy.feedback_history.append(feedback_record)
    
    # Ažuriraj brojila za terapiju
     if feedback_type == 'confirmed':
        therapy.confirmed_warnings_count = getattr(therapy, 'confirmed_warnings_count', 0) + 1
        print(f"[LEARN] Potvrđeno upozorenje za terapiju {therapy.id}")
        
     elif feedback_type == 'ignored':
        therapy.ignored_warnings_count += 1
        print(f"[LEARN] Ignorisano upozorenje za terapiju {therapy.id} (ukupno: {therapy.ignored_warnings_count})")
        
     elif feedback_type == 'false_alarm':
        therapy.false_alarms_count = getattr(therapy, 'false_alarms_count', 0) + 1
        print(f"[LEARN] Lažna uzbuna za terapiju {therapy.id}")
    
    
    def _adjust_threshold_from_feedback(self, feedback_type: str, warning_severity: str):
        """Prilagodi prag na osnovu feedbacka"""
        old_threshold = self.adaptive_threshold
        
        if feedback_type == 'confirmed':
            # Postani osjetljiviji kada korisnik potvrdi upozorenje
            severity_multiplier = 2.0 if warning_severity == 'CRITICAL' else 1.5 if warning_severity == 'HIGH' else 1.0
            adjustment = self.confirmed_threshold_adjustment * severity_multiplier
            self.adaptive_threshold = max(1.0, self.adaptive_threshold + adjustment)
            
        elif feedback_type == 'ignored':
            # Postani manje osjetljiv kada korisnik ignorira
            adjustment = self.ignored_threshold_adjustment
            self.adaptive_threshold = min(5.0, self.adaptive_threshold + adjustment)
            
        elif feedback_type == 'false_alarm':
            # Kazni se za lažne uzbune (postani manje osjetljiv)
            self.adaptive_threshold += self.false_alarm_penalty
            print(f"[LEARN] Kazna za lažnu uzbunu!")
        
        # Zaokruži na 2 decimale
        self.adaptive_threshold = round(self.adaptive_threshold, 2)
        
        if old_threshold != self.adaptive_threshold:
            print(f"[LEARN] Prag promjenjen: {old_threshold:.2f} → {self.adaptive_threshold:.2f}")
    
    def _update_learning_stats(self, feedback_type: str):
     """Ažuriraj statistike učenja i spremi u bazu"""
     # Ažuriraj lokalne statistike
     self.learning_stats['total_feedbacks'] += 1
    
     if feedback_type == 'confirmed':
        self.learning_stats['confirmed_count'] += 1
     elif feedback_type == 'ignored':
        self.learning_stats['ignored_count'] += 1
     elif feedback_type == 'false_alarm':
        self.learning_stats['false_alarm_count'] += 1
    
    # Izračunaj tačnost
     if self.learning_stats['total_feedbacks'] > 0:
        accuracy = (self.learning_stats['confirmed_count'] / self.learning_stats['total_feedbacks']) * 100
        self.learning_stats['accuracy_history'].append(accuracy)
        
        # Zadrži samo posljednjih 100 tačnosti
        if len(self.learning_stats['accuracy_history']) > 100:
            self.learning_stats['accuracy_history'].pop(0)
    
     
     self._save_learning_stats_to_db()
    
     print(f"[LEARN_STATS] Ažurirane statistike: {self.learning_stats}")
    
    def _save_learning_stats_to_db(self):
     """Spremi statistike učenja u bazu"""
     try:
        with self.db.get_session() as session:
            from DDIAgent.infrastructure.database import AgentLearningDB
            
            record = session.query(AgentLearningDB).first()
            if not record:
                record = AgentLearningDB()
                session.add(record)
            
            # Ažuriraj record
            record.total_feedbacks = self.learning_stats['total_feedbacks']
            record.confirmed_count = self.learning_stats['confirmed_count']
            record.ignored_count = self.learning_stats['ignored_count']
            record.false_alarm_count = self.learning_stats['false_alarm_count']
            record.current_accuracy = self.learning_stats['accuracy_history'][-1] if self.learning_stats['accuracy_history'] else 0.0
            record.accuracy_history = self.learning_stats['accuracy_history']
            
            session.commit()
            print(f"[LEARN_STATS] Statistike spremljene u bazu")
            
     except Exception as e:
        print(f"[LEARN_STATS] Greška pri spremanju statistika: {e}")

    def _load_learning_stats_from_db(self):
     """Učitaj statistike učenja iz baze"""
     try:
        with self.db.get_session() as session:
            from DDIAgent.infrastructure.database import AgentLearningDB
            
            record = session.query(AgentLearningDB).first()
            if record:
                # Učitaj iz baze
                self.learning_stats = {
                    'total_feedbacks': record.total_feedbacks,
                    'confirmed_count': record.confirmed_count,
                    'ignored_count': record.ignored_count,
                    'false_alarm_count': record.false_alarm_count,
                    'accuracy_history': record.accuracy_history or []
                }
                print(f"[RUNNER] Učitane statistike iz baze: {self.learning_stats}")
            else:
                # Kreiraj default
                self.learning_stats = {
                    'total_feedbacks': 0,
                    'confirmed_count': 0,
                    'ignored_count': 0,
                    'false_alarm_count': 0,
                    'accuracy_history': []
                }
                print(f"[RUNNER] Kreirane default statistike")
                
     except Exception as e:
        print(f"[RUNNER] Greška pri učitavanju statistika: {e}")
        self.learning_stats = {
            'total_feedbacks': 0,
            'confirmed_count': 0,
            'ignored_count': 0,
            'false_alarm_count': 0,
            'accuracy_history': []
        }

    def calculate_trust_factor(self, therapy: Therapy) -> float:
        """Izračunaj koliko agent vjeruje svojim procjenama za ovu terapiju"""
        if not hasattr(therapy, 'feedback_history') or not therapy.feedback_history:
            return 0.5  # Neutralno - nema historije
        
        feedbacks = therapy.feedback_history
        if len(feedbacks) < 2:
            return 0.5  # Nema dovoljno podataka
        
        # Izračunaj tačnost za ovu terapiju
        confirmed = sum(1 for f in feedbacks if f.get('feedback_type') == 'confirmed')
        false_alarms = sum(1 for f in feedbacks if f.get('feedback_type') == 'false_alarm')
        total = len(feedbacks)
        
        if total == 0:
            return 0.5
        
        accuracy = confirmed / total
        false_rate = false_alarms / total
        
        # Trust faktor (0.0 = nema povjerenja, 1.0 = puno povjerenja)
        # Više težine damo tačnosti nego false alarm rate
        trust = (accuracy * 0.7) + ((1 - false_rate) * 0.3)
        
        return max(0.1, min(0.9, trust))
    
    def get_learning_stats(self):
        """Vrati statistike učenja"""
        stats = self.learning_stats.copy()
        
        # Dodaj trenutni prag
        stats['adaptive_threshold'] = self.adaptive_threshold
        
        # Izračunaj prosječnu tačnost
        if stats['accuracy_history']:
            stats['average_accuracy'] = sum(stats['accuracy_history']) / len(stats['accuracy_history'])
        else:
            stats['average_accuracy'] = 0
        
        # Izračunaj trend tačnosti (poboljšanje/pogoršanje)
        if len(stats['accuracy_history']) >= 10:
            recent = stats['accuracy_history'][-10:]
            older = stats['accuracy_history'][-20:-10] if len(stats['accuracy_history']) >= 20 else stats['accuracy_history'][:10]
            
            if older and recent:
                recent_avg = sum(recent) / len(recent)
                older_avg = sum(older) / len(older)
                stats['accuracy_trend'] = recent_avg - older_avg
            else:
                stats['accuracy_trend'] = 0
        else:
            stats['accuracy_trend'] = 0
        
        return stats
    

    def _apply_policy_with_feedback(self, assessment: RiskAssessment, therapy: Therapy) -> ActionType:
        """Primijeni politiku koja uči iz historije feedbacka"""
        # Izračunaj faktor pouzdanosti na osnovu historije feedbacka
        trust_factor = self.calculate_trust_factor(therapy)
        
        # Bazni prag
        base_threshold = self.adaptive_threshold
        
        # Prilagodi prag na osnovu historije feedbacka za ovu terapiju
        if hasattr(therapy, 'confirmed_warnings_count') and therapy.confirmed_warnings_count > 0:
            # Ako smo ranije imali tačne upozorenja, postani osjetljiviji
            confirmed_factor = therapy.confirmed_warnings_count * 0.1
            base_threshold = max(1.0, base_threshold - confirmed_factor)
        
        if therapy.ignored_warnings_count > 0:
            # Ako su upozorenja često ignorisana, postani manje osjetljiv
            ignored_factor = therapy.ignored_warnings_count * 0.15
            base_threshold = min(5.0, base_threshold + ignored_factor)
        
        # Koristi trust faktor za prilagodbu pragova
        # Više povjerenje = stroži pragovi (manje tolerancije)
        trust_adjustment = (1 - trust_factor) * 0.5  # 0 do 0.5
        
        print(f"[POLICY_WITH_FEEDBACK] Trust faktor: {trust_factor:.2f}, Base threshold: {base_threshold:.2f}")
        
        # ODLUČIVANJE SA FEEDBACK FAKTORIMA:
        if assessment.has_critical_interactions:
            return ActionType.ESCALATE
        
        elif assessment.total_score >= base_threshold * (2.0 - trust_adjustment):
            return ActionType.WARN
        
        elif assessment.total_score >= base_threshold * (1.5 - trust_adjustment * 0.5):
            return ActionType.REQUEST_INFO
        
        else:
            return ActionType.INFORM
    
    def tick(self) -> TickResult:
        """
        Izvrši jedan ciklus agenta (Pravilo #1: Step/Tick = jedna iteracija)
        Pravilo #2: Tick radi "malo", ne "sve" - obrađuje jednu terapiju
        Pravilo #3: Mora imati "no-work" izlaz bez štete
        """
        # === SENSE === (Percepcija)
        percept = self._sense()
        if not percept:
            return TickResult(has_work=False)  # Pravilo #3: No-work izlaz
        
        # === THINK === (Odluka)
        assessment, action = self._think(percept)
        
        # === ACT === (Akcija)
        warning = self._act(percept, assessment, action)
        
        # === LEARN === (Učenje)
        self._learn(percept, assessment, warning)
        
        return TickResult(
            has_work=True,
            therapy_id=percept.therapy.id,
            patient_id=percept.therapy.patient_id,
            drug_count=percept.therapy.drug_count,
            assessment=assessment,
            warning=warning,
            action_taken=action
        )
    
    def _sense(self) -> Optional[TherapyPercept]:
     """SENSE: Pronađi terapiju za procjenu"""
     active_therapies = self.therapy_repository.find_all_active()
    
     print(f"[SENSE] Pronađeno {len(active_therapies)} aktivnih terapija")
    
     for i, therapy in enumerate(active_therapies):
        print(f"[SENSE] {i+1}. ID:{therapy.id} Pacijent:{therapy.patient_id} Lijekovi:{therapy.drug_count}")
        
        last_time = self._get_last_assessment_time(therapy.id)
        last_str = last_time.strftime("%H:%M:%S") if last_time else "NIKAD"
        
        percept = TherapyPercept(
            therapy=therapy,
            requires_assessment=True,
            last_assessment_time=last_time,
            source="SCHEDULED_CHECK"
        )
        
        print(f"[SENSE]   Zadnja procjena: {last_str}, Treba procjenu: {percept.should_be_assessed}")
        
        if percept.should_be_assessed:
            print(f"[SENSE]   ✓ ODABRANA: {therapy.patient_id}")
            return percept
    
     print("[SENSE]   ✗ NEMA terapija za procjenu")
     return None
    
    def _think(self, percept: TherapyPercept) -> tuple[RiskAssessment, ActionType]:
        """
        THINK: Procjeni rizik i donesi odluku
        - Koristi scoring service za procjenu
        - Primjenjuje politiku odlučivanja (adaptivni pragovi)
        """
        # 1. Procjeni rizik (koristi scoring servis)
        assessment = self.scoring_service.assess_therapy_risk(percept.therapy)
        
        # 2. Primijeni politiku odlučivanja
        action = self._apply_policy(assessment, percept.therapy)
        
        return assessment, action
    
    def _act(self, percept: TherapyPercept, assessment: RiskAssessment, 
             action: ActionType) -> Optional[Warning]:
        """
        ACT: Izvrši odlučenu akciju
        Generiše poruke/warning-e
        """
        # Pravilo #5: Tick mora biti idempotentan koliko god može
        # (implementirano kroz transakcije u repository)
        
        if action == ActionType.INFORM:
            print(f"[ACT:INFORM] Terapija {percept.therapy.id}: {assessment.interaction_count} interakcija")
            return None
        
        warning = Warning(
            assessment=assessment,
            action_type=action,
            message=self._generate_warning_message(assessment, action),
            priority=self._determine_priority(assessment),
            suggestions=self._generate_suggestions(assessment),
            status="PENDING"  # Čeka feedback korisnika
        )
        
        print(f"[ACT:{action.value}] {warning.message}")
        return warning
    
    def _learn(self, percept: TherapyPercept, assessment: RiskAssessment, 
           warning: Optional[Warning]):
     """LEARN: Ažuriraj znanje na osnovu iskustva"""
     if assessment.risk_level == RiskLevel.CRITICAL:
        # Smanji prag za kritične slučajeve (postani osjetljiviji)
        self.adaptive_threshold = max(2.0, self.adaptive_threshold - self.learning_rate)
        print(f"[LEARN] Smanjen prag na {self.adaptive_threshold:.2f} zbog kritičnog rizika")
    
     if percept.therapy.risk_history is None:
        percept.therapy.risk_history = []
    
     current_time = datetime.now()
     percept.therapy.risk_history.append({
        'timestamp': current_time.isoformat(),
        'total_score': assessment.total_score,
        'risk_level': assessment.risk_level.value,
        'action_taken': warning.action_type.value if warning else "INFORM",
        'interaction_count': assessment.interaction_count,
        'critical_count': assessment.critical_count,
        'high_risk_count': assessment.high_risk_count,
        'assessment_time': current_time.isoformat()  
    })
    
    # Sačuvaj ažuriranu terapiju
     self.therapy_repository.save(percept.therapy)
     print(f"[LEARN] Terapija {percept.therapy.id} označena kao obrađena u {current_time.strftime('%H:%M:%S')}")
    
    def _apply_policy(self, assessment: RiskAssessment, therapy: Therapy) -> ActionType:
        """
        Primijeni politiku odlučivanja sa adaptivnim pragovima
        KOJA SADA UČI IZ FEEDBACKA
        """
        # DEBUG
        print(f"\n[POLICY] Početni prag: {self.adaptive_threshold}")
        print(f"[POLICY] Assessment total_score: {assessment.total_score}")
        print(f"[POLICY] Critical count: {assessment.critical_count}")
        
        # PRVO: Provjeri kritične interakcije - OVO SE NE MIJENJA
        if assessment.has_critical_interactions:
            print(f"[POLICY] KRITIČNE interakcije detektovane → ESCALATE")
            return ActionType.ESCALATE
        
        # DRUGO: Prilagodi prag na osnovu historije feedbacka
        effective_threshold = self.adaptive_threshold
        
        # FAKTOR 1: Historija ignorisanja upozorenja
        if therapy.ignored_warnings_count > 0:
            adjustment = therapy.ignored_warnings_count * 0.15
            effective_threshold += adjustment
            print(f"[POLICY] Povećan prag na {effective_threshold:.2f} zbog {therapy.ignored_warnings_count} ignorisanih upozorenja")
        
        # FAKTOR 2: Prethodni incidenti
        if therapy.previous_incidents > 0:
            adjustment = therapy.previous_incidents * 0.2
            effective_threshold = max(1.0, effective_threshold - adjustment)
            print(f"[POLICY] Smanjen prag na {effective_threshold:.2f} zbog {therapy.previous_incidents} prethodnih incidenata")
        
        # FAKTOR 3: Feedback historija
        trust_factor = self.calculate_trust_factor(therapy)
        feedback_adjustment = (1 - trust_factor) * 0.3  # Manje povjerenje = veći prag
        effective_threshold += feedback_adjustment
        
        # FAKTOR 4: Broj lijekova
        drug_factor = therapy.drug_count / 5.0
        effective_threshold -= drug_factor * 0.5
        
        # Zaokruži
        effective_threshold = round(effective_threshold, 2)
        
        print(f"[POLICY] Konačan prag: {effective_threshold:.2f} (Trust faktor: {trust_factor:.2f})")
        
        # ODLUČIVANJE:
        # Ako imamo feedback historiju, koristimo poboljšanu politiku
        if hasattr(therapy, 'feedback_history') and therapy.feedback_history:
            return self._apply_policy_with_feedback(assessment, therapy)
        else:
            # Stara logika za terapije bez feedback historije
            if assessment.total_score >= effective_threshold + 2.0:
                return ActionType.WARN
            elif assessment.total_score >= effective_threshold:
                return ActionType.REQUEST_INFO
            else:
                return ActionType.INFORM
    
    def _generate_warning_message(self, assessment: RiskAssessment, action: ActionType) -> str:
        """Generiše poruku na osnovu akcije i procjene"""
        templates = {
            ActionType.ESCALATE: 
                "🚨 KRITIČAN RIZIK! Pronađeno {critical} kritičnih interakcija. "
                "HITNO KONSULTUJTE LJEKARA!",
            
            ActionType.WARN: 
                "⚠️ VISOK RIZIK! Ukupno {total} interakcija sa score-om {score:.1f}. "
                "Preporučuje se modifikacija terapije.",
            
            ActionType.REQUEST_INFO: 
                "❓ UMJEREN RIZIK. {count} interakcija pronađeno. "
                "Molimo potvrdite da li je terapija ispravna.",
            
            ActionType.INFORM: 
                "ℹ️ {count} interakcija pronađeno. Preporučuje se redovno praćenje."
        }
        
        template = templates.get(action, templates[ActionType.INFORM])
        
        return template.format(
            critical=assessment.critical_count,
            total=assessment.interaction_count,
            score=assessment.total_score,
            count=assessment.interaction_count
        )
    
    def _determine_priority(self, assessment: RiskAssessment) -> str:
        """Određuje prioritet na osnovu procjene rizika"""
        if assessment.risk_level == RiskLevel.CRITICAL:
            return "HIGHEST"
        elif assessment.risk_level == RiskLevel.HIGH:
            return "HIGH"
        elif assessment.risk_level == RiskLevel.MODERATE:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_suggestions(self, assessment: RiskAssessment) -> list:
        """Generiše sugestije na osnovu procjene"""
        suggestions = []
        
        if assessment.critical_count > 0:
            suggestions.append("Hitno konsultujte ljekara!")
            suggestions.append("Razmotrite zamjenu kritičnih lijekova")
        
        if assessment.high_risk_count > 0:
            suggestions.append("Povećajte monitoring vitalnih znakova")
            suggestions.append("Razmotrite alternativne lijekove sa nižim rizikom")
        
        if assessment.interaction_count > 5:
            suggestions.append("Simplifikujte terapiju ako je moguće")
            suggestions.append("Razmotrite konsolidaciju lijekova")
        
        if assessment.total_score > 10:
            suggestions.append("Razmotrite hospitalizaciju za monitoring")
        
        return suggestions
    
    def _get_last_assessment_time(self, therapy_id: int) -> Optional[datetime]:
     """Pronađi vrijeme posljednje procjene"""
     therapy = self.therapy_repository.find_by_id(therapy_id)
    
     if not therapy or not therapy.risk_history:
        return None
    
     try:
        # Pretpostavimo da je risk_history list dict-ova sa 'timestamp' i 'assessment_time'
        latest_record = therapy.risk_history[-1]
        
        # Pokušaj prvo sa 'assessment_time', pa sa 'timestamp'
        time_str = latest_record.get('assessment_time') or latest_record.get('timestamp')
        
        if time_str:
            if isinstance(time_str, str):
                return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            elif isinstance(time_str, datetime):
                return time_str
     except (KeyError, ValueError, TypeError) as e:
        print(f"[SENSE] Greška pri čitanju vremena: {e}")
    
     return None

# Factory funkcija za kreiranje runnera
def create_risk_assessment_runner(data_path: str = "data/DDI_with_scores.csv"):
    """Kreira runner sa svim zavisnostima (Dependency Injection)"""
    # Inicijalizuj sve komponente
    database = Database("data/ddi_agent.db")
    
    scoring_model = ScoringModel(data_path)
    scoring_service = ScoringService(scoring_model)
    
    therapy_repository = TherapyRepository(database)
    
    # Kreiraj runner
    runner = RiskAssessmentRunner(
        database=database,
        scoring_service=scoring_service,
        therapy_repository=therapy_repository
    )
    
    return runner