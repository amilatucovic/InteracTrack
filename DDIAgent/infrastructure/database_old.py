"""
INFRASTRUKTURA: Database setup za DDI agenta
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
import os
from datetime import datetime

Base = declarative_base()

class TherapyDB(Base):
    __tablename__ = 'therapies'
    
    # PRIMARY KEY i OBAVEZNI podaci
    id = Column(Integer, primary_key=True)
    patient_id = Column(String(100), nullable=False)
    
    # JSON podaci sa default vrijednostima
    drugs = Column(JSON, nullable=False, default=lambda: [])
    risk_history = Column(JSON, nullable=False, default=lambda: [])
    feedback_history = Column(JSON, nullable=False, default=lambda: [])
    
    # STATUS i PODEŠAVANJA
    status = Column(String(50), nullable=False, default="ACTIVE")
    risk_tolerance = Column(Float, nullable=False, default=3.0)
    
    # BROJAČI
    ignored_warnings_count = Column(Integer, nullable=False, default=0)
    previous_incidents = Column(Integer, nullable=False, default=0)
    confirmed_warnings_count = Column(Integer, nullable=False, default=0)
    false_alarms_count = Column(Integer, nullable=False, default=0)
    
    # TIMESTAMPS
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # METODE
    def __repr__(self):
        return f"<TherapyDB(id={self.id}, patient='{self.patient_id}', status='{self.status}')>"
    
    def to_dict(self):
        """Konvertuj u dictionary"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'drugs': self.drugs,
            'status': self.status,
            'risk_tolerance': self.risk_tolerance,
            'ignored_warnings_count': self.ignored_warnings_count,
            'previous_incidents': self.previous_incidents,
            'confirmed_warnings_count': self.confirmed_warnings_count,
            'false_alarms_count': self.false_alarms_count,
            'risk_history': self.risk_history,
            'feedback_history': self.feedback_history,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class WarningDB(Base):
    __tablename__ = 'warnings'
    
    # PRIMARY KEY i OBAVEZNI podaci
    id = Column(Integer, primary_key=True)
    therapy_id = Column(Integer, nullable=False, index=True)  # INDEX za brže pretraživanje
    patient_id = Column(String(100), nullable=False, index=True)
    
    # UP OZORENJE PODACI
    action_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String(50), nullable=False, default="MEDIUM")
    status = Column(String(50), nullable=False, default="PENDING")
    
    # JSON PODACI
    assessment_data = Column(JSON, nullable=True)  # Može biti NULL
    suggestions = Column(JSON, nullable=False, default=lambda: [])
    details = Column(JSON, nullable=False, default=lambda: {})  # Dodatni detalji
    
    # FEEDBACK
    feedback_type = Column(String(50), nullable=True)  # 'confirmed', 'false_alarm', 'ignored'
    feedback_notes = Column(Text, nullable=True)
    feedback_at = Column(DateTime, nullable=True)
    
    # TIMESTAMPS
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    acknowledged_at = Column(DateTime, nullable=True)
    
    # METODE
    def __repr__(self):
        return f"<WarningDB(id={self.id}, therapy_id={self.therapy_id}, action='{self.action_type}')>"
    
    def to_dict(self):
        """Konvertuj u dictionary"""
        return {
            'id': self.id,
            'therapy_id': self.therapy_id,
            'patient_id': self.patient_id,
            'action_type': self.action_type,
            'message': self.message,
            'priority': self.priority,
            'status': self.status,
            'assessment_data': self.assessment_data,
            'suggestions': self.suggestions,
            'details': self.details,
            'feedback_type': self.feedback_type,
            'feedback_notes': self.feedback_notes,
            'feedback_at': self.feedback_at.isoformat() if self.feedback_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }

class FeedbackDB(Base):
    __tablename__ = 'feedbacks'
    
    # PRIMARY KEY
    id = Column(Integer, primary_key=True)
    
    # REFERENCE
    warning_id = Column(Integer, nullable=False, index=True)
    therapy_id = Column(Integer, nullable=False, index=True)
    patient_id = Column(String(100), nullable=False, index=True)
    
    # FEEDBACK PODACI
    feedback_type = Column(String(50), nullable=False)  # 'confirmed', 'false_alarm', 'ignored'
    notes = Column(Text, nullable=True)
    
    # AGENT LEARNING METRIKE
    threshold_before = Column(Float, nullable=False)
    threshold_after = Column(Float, nullable=False)
    warning_severity = Column(String(50), nullable=True)
    
    # JSON za dodatne podatke
    metadata = Column(JSON, nullable=False, default=lambda: {})
    
    # TIMESTAMPS
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    
    # METODE
    def __repr__(self):
        return f"<FeedbackDB(id={self.id}, warning={self.warning_id}, type='{self.feedback_type}')>"
    
    def to_dict(self):
        """Konvertuj u dictionary"""
        return {
            'id': self.id,
            'warning_id': self.warning_id,
            'therapy_id': self.therapy_id,
            'patient_id': self.patient_id,
            'feedback_type': self.feedback_type,
            'notes': self.notes,
            'threshold_before': self.threshold_before,
            'threshold_after': self.threshold_after,
            'warning_severity': self.warning_severity,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class AgentLearningDB(Base):
    __tablename__ = 'agent_learning'
    
    # PRIMARY KEY
    id = Column(Integer, primary_key=True)
    
    # AGENT METRIKE
    adaptive_threshold = Column(Float, nullable=False, default=3.0)
    total_feedbacks = Column(Integer, nullable=False, default=0)
    confirmed_count = Column(Integer, nullable=False, default=0)
    ignored_count = Column(Integer, nullable=False, default=0)
    false_alarm_count = Column(Integer, nullable=False, default=0)
    
    # TAČNOST
    current_accuracy = Column(Float, nullable=False, default=0.0)
    accuracy_history = Column(JSON, nullable=False, default=lambda: [])
    
    # JSON za dodatne metrike
    learning_metrics = Column(JSON, nullable=False, default=lambda: {})
    
    # TIMESTAMP
    recorded_at = Column(DateTime, nullable=False, default=datetime.now)
    
    # METODE
    def __repr__(self):
        return f"<AgentLearningDB(id={self.id}, threshold={self.adaptive_threshold}, accuracy={self.current_accuracy:.1f}%)>"
    
    def to_dict(self):
        """Konvertuj u dictionary"""
        return {
            'id': self.id,
            'adaptive_threshold': self.adaptive_threshold,
            'total_feedbacks': self.total_feedbacks,
            'confirmed_count': self.confirmed_count,
            'ignored_count': self.ignored_count,
            'false_alarm_count': self.false_alarm_count,
            'current_accuracy': self.current_accuracy,
            'accuracy_history': self.accuracy_history,
            'learning_metrics': self.learning_metrics,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }

class Database:
    def __init__(self, db_path: str = "data/ddi_agent.db"):
        """Inicijalizuj SQLite bazu sa poboljšanim podešavanjima"""
        try:
            # Kreiraj folder ako ne postoji
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # Kreiraj engine sa boljim podešavanjima
            self.engine = create_engine(
                f"sqlite:///{db_path}",
                echo=False,  # Ne prikazuj SQL u konzoli osim za debugging
                connect_args={"check_same_thread": False},  # Važno za threading
                pool_pre_ping=True  # Provjeri konekciju prije korištenja
            )
            
            # Kreiraj tabele
            Base.metadata.create_all(self.engine, checkfirst=True)
            
            # Kreiraj session factory
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False  # Bolje za caching
            )
            
            # Kreiraj inicijalni agent learning record
            self._initialize_agent_learning()
            
            print(f"✅ Database inicijaliziran: {db_path}")
            self._print_database_stats()
            
        except Exception as e:
            print(f"❌ Greška pri inicijalizaciji baze: {e}")
            raise
    
    def _initialize_agent_learning(self):
        """Kreiraj početni agent learning record ako ne postoji"""
        with self.get_session() as session:
            existing = session.query(AgentLearningDB).first()
            if not existing:
                agent_record = AgentLearningDB(
                    adaptive_threshold=3.0,
                    total_feedbacks=0,
                    confirmed_count=0,
                    ignored_count=0,
                    false_alarm_count=0,
                    current_accuracy=0.0,
                    accuracy_history=[],
                    learning_metrics={
                        'learning_rate': 0.1,
                        'confirmed_adjustment': -0.2,
                        'ignored_adjustment': 0.3,
                        'false_alarm_penalty': 0.5
                    }
                )
                session.add(agent_record)
                session.commit()
                print("📊 Kreiran početni agent learning record")
    
    def _print_database_stats(self):
        """Prikaži statistike baze"""
        try:
            with self.get_session() as session:
                # Broj terapija
                therapy_count = session.query(TherapyDB).count()
                
                # Broj upozorenja
                warning_count = session.query(WarningDB).count()
                
                # Broj feedback-a
                feedback_count = session.query(FeedbackDB).count()
                
                # Agent learning
                agent_stats = session.query(AgentLearningDB).first()
                
                print(f"📊 Database statistike:")
                print(f"   • Terapije: {therapy_count}")
                print(f"   • Upozorenja: {warning_count}")
                print(f"   • Feedback-ovi: {feedback_count}")
                if agent_stats:
                    print(f"   • Agent prag: {agent_stats.adaptive_threshold:.2f}")
                    print(f"   • Agent tačnost: {agent_stats.current_accuracy:.1f}%")
                
        except Exception as e:
            print(f"⚠️  Nije moguće prikazati statistike: {e}")
    
    def get_session(self) -> Session:
        """Vrati novu database session"""
        return self.SessionLocal()
    
    def execute(self, sql: str, params: tuple = None):
        """Izvrši raw SQL komandu"""
        with self.get_session() as session:
            if params:
                session.execute(sql, params)
            else:
                session.execute(sql)
            session.commit()
    
    def fetch_all(self, sql: str, params: tuple = None):
        """Izvrši raw SQL query i vrati sve rezultate"""
        with self.get_session() as session:
            if params:
                result = session.execute(sql, params)
            else:
                result = session.execute(sql)
            
            # Konvertuj u listu dict-ova
            rows = []
            for row in result:
                rows.append(dict(row._mapping))
            return rows
    
    def fetch_one(self, sql: str, params: tuple = None):
        """Izvrši raw SQL query i vrati prvi rezultat"""
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None
    
    def test_connection(self):
        """Testiraj database konekciju"""
        try:
            with self.get_session() as session:
                # Proveri da li možemo dobiti session
                session.execute("SELECT 1")
                
                # Proveri tabele
                table_names = self.engine.table_names()
                required_tables = ['therapies', 'warnings', 'feedbacks', 'agent_learning']
                
                missing_tables = [t for t in required_tables if t not in table_names]
                
                if missing_tables:
                    print(f"⚠️  Nedostaju tabele: {missing_tables}")
                    return False
                
                print("✅ Database konekcija uspješna, sve tabele postoje")
                return True
                
        except Exception as e:
            print(f"❌ Database konekcija neuspješna: {e}")
            return False
    
    def backup_database(self, backup_path: str = None):
        """Napravi backup baze"""
        import shutil
        import time
        
        if backup_path is None:
            backup_dir = "backups"
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = f"{backup_dir}/ddi_agent_backup_{timestamp}.db"
        
        try:
            # Zatvori sve konekcije
            self.engine.dispose()
            
            # Kopiraj fajl
            original_path = self.engine.url.database
            shutil.copy2(original_path, backup_path)
            
            print(f"✅ Backup kreiran: {backup_path}")
            return backup_path
            
        except Exception as e:
            print(f"❌ Greška pri backup-u: {e}")
            return None