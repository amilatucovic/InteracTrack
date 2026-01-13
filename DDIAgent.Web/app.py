"""
WEB LAYER: Flask API za DDI Agent
TANKI transport sloj - samo poziva runner i vraća rezultate
"""
from flask import Flask, jsonify, redirect, request, render_template
from flask_cors import CORS
import threading
import time
import sys
import os
from datetime import datetime  
from jinja2 import Environment


# ============================================
# KONFIGURACIJA - FIXIRANE PUTANJE
# ============================================
# DIJAGNOSTIKA
print("="*60)
print("🔍 DIJAGNOSTIKA PUTANJA")
print("="*60)
print(f"__file__: {__file__}")
print(f"Trenutna datoteka: {os.path.abspath(__file__)}")
print(f"Direktorij datoteke: {os.path.dirname(os.path.abspath(__file__))}")
print("="*60)

# OVO JE KLJUČNO: Koristi Parent 1 umjesto Parent 2
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Parent 1 = InteracTrack
CENTRAL_DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Apsolutne putanje
DB_PATH = os.path.join(CENTRAL_DATA_DIR, "ddi_agent.db")
CSV_PATH = os.path.join(CENTRAL_DATA_DIR, "DDI_with_scores.csv")

print("="*60)
print("📁 KONFIGURACIJA PUTANJA")
print("="*60)
print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"DATA_DIR: {CENTRAL_DATA_DIR}")
print(f"DB_PATH: {DB_PATH}")
print(f"CSV_PATH: {CSV_PATH}")
print(f"DB postoji: {'✅' if os.path.exists(DB_PATH) else '❌'} ({os.path.getsize(DB_PATH)/1024:.1f} KB)" if os.path.exists(DB_PATH) else '❌ Ne postoji')
print(f"CSV postoji: {'✅' if os.path.exists(CSV_PATH) else '❌'} ({os.path.getsize(CSV_PATH)/1024/1024:.2f} MB)" if os.path.exists(CSV_PATH) else '❌ Ne postoji')
print("="*60)

# Dodaj DDIAgent u path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from DDIAgent.application.runners.risk_assessment_runner import create_risk_assessment_runner

# ============================================
# FLASK APLIKACIJA
# ============================================
app = Flask(__name__)
CORS(app)

# Dodajte ovo ispod create_app() ili u postojeći kod

def format_datetime(value, format='%d.%m.%Y %H:%M'):
    """Formatira datetime za template"""
    if not value:
        return ""
    try:
        if isinstance(value, str):
            # Pokušaj parsirati ISO format
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        else:
            dt = value
        return dt.strftime(format)
    except:
        return str(value)

# Dodajte filter u Jinja2 environment
app.jinja_env.filters['format_datetime'] = format_datetime


@app.template_filter('reverse')
def reverse_filter(seq):
    """Filter za reverse liste u template-u"""
    try:
        return list(reversed(seq))
    except:
        return seq

# ============================================
# GLOBALNO STANJE
# ============================================
runner = None
agent_thread = None
stop_agent = False
tick_history = []

# ============================================
# INICIJALIZACIJA AGENTA
# ============================================
def initialize_agent():
    """Inicijalizuj DDI agenta"""
    global runner
    
    if runner is None:
        try:
            print("="*60)
            print("🤖 INICIJALIZACIJA DDI AGENT-A")
            print("="*60)
            
            # Provjeri CSV PRIJE nego što pokušaš kreirati runner
            if not os.path.exists(CSV_PATH):
                print(f"❌ GREŠKA: CSV fajl ne postoji!")
                print(f"   Lokacija: {CSV_PATH}")
                print(f"\n🛠️  RJEŠENJE:")
                print(f"   1. Provjeri da li DDI_with_scores.csv postoji u {CENTRAL_DATA_DIR}")
                print(f"   2. Ako ne postoji, kopiraj ga:")
                print(f"      copy '{PROJECT_ROOT}\\DDI_with_scores.csv' '{CENTRAL_DATA_DIR}\\'")
                raise FileNotFoundError(f"CSV fajl nije pronađen: {CSV_PATH}")
            
            # CSV postoji, pokušaj kreirati runner
            print(f"📁 Učitavam CSV: {CSV_PATH}")
            runner = create_risk_assessment_runner(CSV_PATH)
            
            print("✅ DDI Agent uspješno inicijaliziran!")
            print(f"📊 Agent koristi bazu: {DB_PATH}")
            
        except FileNotFoundError as e:
            print(f"❌ KRITIČNA GREŠKA: {e}")
            print("   CSV fajl je neophodan za rad agenta!")
            raise
        except Exception as e:
            print(f"❌ Greška pri inicijalizaciji agenta: {e}")
            raise
    
    return runner

# ============================================
# AGENT BACKGROUND WORKER
# ============================================
def agent_background_worker():
    """Pokreće agent tick-ove u pozadini"""
    global runner, stop_agent, tick_history
    
    if runner is None:
        print("❌ Runner nije inicijaliziran, zaustavljam agenta")
        return
    
    print("🔄 DDI Agent pokrenut u pozadini")
    tick_counter = 0
    
    while not stop_agent:
        try:
            tick_counter += 1
            
            # Izvrši JEDAN agent tick
            result = runner.tick()
            
            if result and result.has_work:
                # Sačuvaj u historiju
                result_dict = result.to_dict()
                tick_history.append(result_dict)
                
                # Limitiraj historiju
                if len(tick_history) > 50:
                    tick_history.pop(0)
                
                print(f"[Tick #{tick_counter}] {result.patient_id} → {result.action_taken.value}")
                
                # Detaljniji ispis za WARN/ESCALATE
                if result.action_taken in ["WARN", "ESCALATE"]:
                    if hasattr(result, 'assessment') and result.assessment:
                        assessment = result.assessment
                        if isinstance(assessment, dict):
                            print(f"   ⚠️  Rizik: {assessment.get('risk_level', 'N/A')}, "
                                  f"Score: {assessment.get('total_score', 0):.1f}, "
                                  f"Interakcije: {assessment.get('interaction_count', 0)}")
            
            # Pauza između tick-ova
            time.sleep(5)
            
        except Exception as e:
            print(f"❌ Greška u agent tick-u: {e}")
            time.sleep(10)

# ============================================
# API KONTROLERI (ISTO KAO PRIJE)
# ============================================
@app.route('/')
def index():
    """Glavna web stranica"""
    # Podaci za template
    context = {
        "application": "InteracTrack DDI Agent",
        "description": "Inteligentni agent za procjenu rizika interakcija lijekova",
        "architecture": "Sense → Think → Act → Learn"
    }
    return render_template('index.html', **context)
@app.route('/api/debug/paths', methods=['GET'])
def debug_paths():
    """Debug informacije o putanjama"""
    return jsonify({
        "project_root": PROJECT_ROOT,
        "central_data_dir": CENTRAL_DATA_DIR,
        "db_path": DB_PATH,
        "csv_path": CSV_PATH,
        "db_exists": os.path.exists(DB_PATH),
        "csv_exists": os.path.exists(CSV_PATH),
        "db_size_kb": round(os.path.getsize(DB_PATH) / 1024, 1) if os.path.exists(DB_PATH) else 0,
        "csv_size_mb": round(os.path.getsize(CSV_PATH) / 1024 / 1024, 2) if os.path.exists(CSV_PATH) else 0
    })

@app.route('/api/agent/status', methods=['GET'])
def agent_status():
    """Status DDI Agent-a"""
    global runner
    
    is_running = agent_thread is not None and agent_thread.is_alive()
    runner_type = type(runner).__name__ if runner else None
    
    # Pokušaj dobiti adaptive threshold ako postoji
    adaptive_threshold = None
    if runner and hasattr(runner, 'adaptive_threshold'):
        adaptive_threshold = runner.adaptive_threshold
    
    return jsonify({
        "agent": {
            "initialized": runner is not None,
            "type": runner_type,
            "running_in_background": is_running,
            "adaptive_threshold": adaptive_threshold,
            "database": DB_PATH if os.path.exists(DB_PATH) else "N/A",
            "csv_available": os.path.exists(CSV_PATH)
        },
        "history": {
            "total_ticks": len(tick_history),
            "recent_ticks": len(tick_history[-10:]),
            "last_actions": [
                {
                    "patient_id": h.get("patient_id"),
                    "action": h.get("action_taken"),
                    "timestamp": h.get("timestamp")
                }
                for h in tick_history[-5:]
            ] if tick_history else []
        }
    })

@app.route('/api/agent/tick', methods=['POST'])
def execute_tick():
    """Izvrši JEDAN agent tick (Sense→Think→Act→Learn)"""
    global runner
    
    try:
        runner = initialize_agent()
        
        # Agent izvršava JEDAN ciklus
        result = runner.tick()
        
        if result and result.has_work:
            # Snimi u historiju
            tick_history.append(result.to_dict())
            if len(tick_history) > 50:
                tick_history.pop(0)
            
            return jsonify({
                "tick_executed": True,
                "agent_cycle": "Sense → Think → Act → Learn",
                "result": result.to_dict(),
                "message": f"Agent je obradio terapiju za pacijenta {result.patient_id}"
            })
        else:
            return jsonify({
                "tick_executed": True,
                "agent_cycle": "Sense (no work)",
                "result": None,
                "message": "Nema terapija za obradu u ovom tick-u"
            })
            
    except Exception as e:
        return jsonify({
            "tick_executed": False,
            "error": str(e),
            "message": "Greška pri izvršavanju agent tick-a"
        }), 500

@app.route('/api/agent/start', methods=['POST'])
def start_background_agent():
    """Pokreni agenta u pozadini"""
    global agent_thread, stop_agent
    
    try:
        initialize_agent()
        
        if agent_thread and agent_thread.is_alive():
            return jsonify({
                "status": "already_running", 
                "message": "Agent je već pokrenut"
            })
        
        stop_agent = False
        agent_thread = threading.Thread(target=agent_background_worker, daemon=True)
        agent_thread.start()
        
        return jsonify({
            "status": "started",
            "message": "DDI Agent pokrenut u pozadini",
            "tick_interval_seconds": 5,
            "thread_id": agent_thread.ident,
            "database": DB_PATH
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Greška pri pokretanju agenta: {e}"
        }), 500

@app.route('/api/agent/stop', methods=['POST'])
def stop_background_agent():
    """Zaustavi pozadinskog agenta"""
    global stop_agent
    
    stop_agent = True
    thread_was_running = agent_thread and agent_thread.is_alive()
    
    return jsonify({
        "status": "stopping",
        "message": "DDI Agent se zaustavlja...",
        "was_running": thread_was_running
    })

@app.route('/api/agent/history', methods=['GET'])
def get_tick_history():
    """Vrati historiju agent tick-ova"""
    recent_history = tick_history[-20:] if len(tick_history) > 20 else tick_history
    
    # Pojednostavi historiju za prikaz
    simplified_history = []
    for item in recent_history:
        simplified = {
            "patient_id": item.get("patient_id", "N/A"),
            "therapy_id": item.get("therapy_id"),
            "action_taken": item.get("action_taken"),
            "timestamp": item.get("timestamp"),
            "risk_level": item.get("assessment", {}).get("risk_level") if item.get("assessment") else None,
            "interaction_count": item.get("assessment", {}).get("interaction_count") if item.get("assessment") else 0
        }
        simplified_history.append(simplified)
    
    return jsonify({
        "total_count": len(tick_history),
        "recent_count": len(recent_history),
        "history": simplified_history
    })

@app.route('/api/therapies', methods=['GET'])
def get_therapies():
    """Lista terapija iz baze"""
    try:
        from DDIAgent.infrastructure.database import Database
        from DDIAgent.infrastructure.therapy_repository import TherapyRepository
        
        print(f"📁 Učitavam terapije iz: {DB_PATH}")
        db = Database(DB_PATH)
        repo = TherapyRepository(db)
        therapies = repo.find_all()
        
        return jsonify({
            "status": "success",
            "database": DB_PATH,
            "database_size_kb": round(os.path.getsize(DB_PATH) / 1024, 1) if os.path.exists(DB_PATH) else 0,
            "count": len(therapies),
            "therapies": [
                {
                    "id": t.id,
                    "patient_id": t.patient_id,
                    "drug_count": t.drug_count,
                    "status": t.status,
                    "risk_tolerance": t.risk_tolerance,
                    "last_assessment": t.last_assessment.isoformat() if hasattr(t, 'last_assessment') and t.last_assessment else None
                }
                for t in therapies
            ]
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "database": DB_PATH,
            "database_exists": os.path.exists(DB_PATH)
        }), 500

@app.route('/api/therapies/add', methods=['POST'])
def add_therapy():
    """Dodaj novu terapiju"""
    try:
        from DDIAgent.infrastructure.database import Database
        from DDIAgent.infrastructure.therapy_repository import TherapyRepository
        from DDIAgent.domain.entities import Therapy, Drug
        
        data = request.json
        
        if not data or 'patient_id' not in data or 'drugs' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing patient_id or drugs"
            }), 400
        
        # Kreiraj lijekove
        drugs_list = []
        for i, drug_data in enumerate(data['drugs']):
            drug = Drug(
                drug_id=drug_data.get('drug_id', f"DB{i+1:05d}"),
                name=drug_data.get('name', f"Lijek {i+1}"),
                dosage=drug_data.get('dosage', "1x dnevno")
            )
            drugs_list.append(drug)
        
        # Kreiraj terapiju
        therapy = Therapy(
            patient_id=data['patient_id'],
            drugs=drugs_list,
            status=data.get('status', 'ACTIVE'),
            risk_tolerance=float(data.get('risk_tolerance', 3.0))
        )
        
        # Sačuvaj
        db = Database(DB_PATH)
        repo = TherapyRepository(db)
        saved_therapy = repo.save(therapy)
        
        return jsonify({
            "status": "created",
            "message": f"Terapija za pacijenta {saved_therapy.patient_id} je kreirana",
            "therapy": {
                "id": saved_therapy.id,
                "patient_id": saved_therapy.patient_id,
                "drug_count": saved_therapy.drug_count,
                "status": saved_therapy.status,
                "risk_tolerance": saved_therapy.risk_tolerance
            },
            "database": DB_PATH
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Test API endpoint"""
    return jsonify({
        "status": "ok",
        "message": "API radi",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "agent_initialized": runner is not None,
        "csv_available": os.path.exists(CSV_PATH)
    })

# ============================================
# NOVI WEB UI ROUTES
# ============================================

@app.route('/therapy/create', methods=['GET'])
def create_therapy_page():
    """Prikaži formu za kreiranje terapije"""
    return render_template('create_therapy.html')

@app.route('/therapy/<int:therapy_id>', methods=['GET'])
def view_therapy_page(therapy_id):
    """Prikaži detalje terapije i agentovu procjenu"""
    try:
        from DDIAgent.infrastructure.database import Database
        from DDIAgent.infrastructure.therapy_repository import TherapyRepository
        from DDIAgent.domain.entities import TherapyPercept
        
        db = Database(DB_PATH)
        repo = TherapyRepository(db)
        
        # 1. PRVO: Eksplicitno refresh terapije iz baze
        therapy = repo.find_by_id(therapy_id)
        if therapy:
            # Eksplicitno refresh da dobijemo najnovije podatke
            therapy = repo.refresh(therapy)
        
        if not therapy:
            return render_template('error.html', 
                                 message=f"Terapija ID {therapy_id} nije pronađena"), 404
        
        # 2. Inicijalizuj agenta ako već nije
        global runner
        if not runner:
            initialize_agent()
        
        # 3. Procjeni rizik za ovu terapiju
        assessment = None
        action = None
        warning = None
        
        if runner:
            # Kreiraj percept
            percept = TherapyPercept(
                therapy=therapy,
                requires_assessment=True,
                last_assessment_time=therapy.last_assessment_time,
                source="MANUAL_ASSESSMENT"
            )
            
            # THINK: Procjeni rizik i donesi odluku
            try:
                assessment, action = runner._think(percept)
                
                # ACT: Kreiraj warning ako je potrebno
                if action and action.name != "INFORM":
                    warning = runner._act(percept, assessment, action)
                    
                    # LEARN: Sačuvaj u historiju
                    runner._learn(percept, assessment, warning)
                else:
                    # Za INFORM akcije, samo sačuvaj u historiju
                    runner._learn(percept, assessment, None)
                    
            except Exception as e:
                print(f"Greška pri procjeni terapije {therapy_id}: {e}")
        
        # 4. Formatiraj podatke za template - UVEK direktno iz atributa
        therapy_data = {
            "id": therapy.id,
            "patient_id": therapy.patient_id,
            "drug_count": therapy.drug_count,
            "status": therapy.status,
            "risk_tolerance": therapy.risk_tolerance,
            "ignored_warnings_count": therapy.ignored_warnings_count,
            "previous_incidents": therapy.previous_incidents,
            "confirmed_warnings_count": getattr(therapy, 'confirmed_warnings_count', 0),
            "false_alarms_count": getattr(therapy, 'false_alarms_count', 0),
            "feedback_history": getattr(therapy, 'feedback_history', []),
            "drugs": [
                {
                    "drug_id": drug.drug_id,
                    "name": drug.name,
                    "dosage": drug.dosage or "Nije navedeno"
                }
                for drug in therapy.drugs
            ],
            "risk_history": therapy.risk_history or []
        }
        
        # 5. Dodaj debug info
        therapy_data["debug_info"] = {
            "feedback_history_length": len(therapy_data["feedback_history"]),
            "timestamp": datetime.now().isoformat(),
            "runner_initialized": runner is not None
        }
        
        # 6. Formatiraj assessment ako postoji
        assessment_data = None
        if assessment:
            assessment_data = assessment.to_dict()
        
        # 7. Formatiraj warning ako postoji
        warning_data = None
        if warning:
            warning_data = warning.to_dict()
        
        return render_template('view_therapy.html',
                             therapy=therapy_data,
                             assessment=assessment_data,
                             action=action.value if action else None,
                             warning=warning_data)
        
    except Exception as e:
        print(f"Greška pri učitavanju terapije: {e}")
        return render_template('error.html', 
                             message=f"Greška pri učitavanju terapije: {str(e)}"), 500
    
@app.route('/therapy/view/<int:therapy_id>')
def redirect_to_therapy(therapy_id):
    """Redirect legacy /therapy/view/ routes to new /therapy/ routes"""
    from flask import redirect
    return redirect(f'/therapy/{therapy_id}')

@app.route('/api/warning/<warning_id>/feedback', methods=['POST'])
def submit_feedback(warning_id):
    """Korisnik daje feedback na upozorenje"""
    try:
        data = request.json or request.form
        feedback_type = data.get('feedback_type', '')  # 'confirmed', 'false_alarm', 'ignored'
        notes = data.get('notes', '')
        
        # Ovdje bi trebali ažurirati warning u bazi
        # Za sada samo logujemo
        print(f"📝 Feedback primljen za warning {warning_id}: {feedback_type}")
        
        # Ažuriraj globalni runner ako postoji
        global runner
        if runner and hasattr(runner, 'user_feedback_history'):
            runner.user_feedback_history.append({
                'warning_id': warning_id,
                'feedback_type': feedback_type,
                'notes': notes,
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # Adaptacija na osnovu feedbacka
            if feedback_type == 'ignored' and hasattr(runner, 'adaptive_threshold'):
                runner.adaptive_threshold += 0.1  # Postani manje osjetljiv
                print(f"📈 Prag povećan na {runner.adaptive_threshold:.2f} zbog ignorisanog upozorenja")
            elif feedback_type == 'confirmed' and hasattr(runner, 'adaptive_threshold'):
                runner.adaptive_threshold = max(1.0, runner.adaptive_threshold - 0.1)  # Postani osjetljiviji
                print(f"📉 Prag smanjen na {runner.adaptive_threshold:.2f} zbog potvrđenog upozorenja")
        
        return jsonify({
            "status": "success",
            "message": "Hvala na povratnoj informaciji!",
            "warning_id": warning_id,
            "feedback_type": feedback_type
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/dashboard', methods=['GET'])
def dashboard_page():
    """Dashboard sa svim terapijama i statistikama"""
    try:
        from DDIAgent.infrastructure.database import Database
        from DDIAgent.infrastructure.therapy_repository import TherapyRepository
        
        db = Database(DB_PATH)
        repo = TherapyRepository(db)
        therapies = repo.find_all()
        
        # Izračunaj statistike
        stats = {
            'total_therapies': len(therapies),
            'active_therapies': len([t for t in therapies if t.status == 'ACTIVE']),
            'therapies_with_drugs': len([t for t in therapies if t.drug_count > 0]),
            'avg_drugs_per_therapy': sum(t.drug_count for t in therapies) / len(therapies) if therapies else 0,
            'high_risk_count': len([t for t in therapies if t.last_risk_level and t.last_risk_level.value in ['HIGH', 'CRITICAL']])
        }
        
        # Pripremi terapije za prikaz
        therapies_display = []
        for therapy in therapies[:20]:  # Prikaži prvih 20
            therapies_display.append({
                'id': therapy.id,
                'patient_id': therapy.patient_id,
                'drug_count': therapy.drug_count,
                'status': therapy.status,
                'last_assessment': therapy.last_assessment_time.strftime("%Y-%m-%d %H:%M") if therapy.last_assessment_time else 'Nikad',
                'last_risk_level': therapy.last_risk_level.value if therapy.last_risk_level else 'N/A',
                'ignored_warnings': therapy.ignored_warnings_count
            })
        
        # Agent statistike
        agent_stats = {
            'initialized': runner is not None,
            'running_in_background': agent_thread is not None and agent_thread.is_alive(),
            'total_ticks': len(tick_history),
            'adaptive_threshold': runner.adaptive_threshold if runner and hasattr(runner, 'adaptive_threshold') else None
        }
        
        return render_template('dashboard.html',
                             therapies=therapies_display,
                             stats=stats,
                             agent_stats=agent_stats)
        
    except Exception as e:
        print(f"Greška pri učitavanju dashboarda: {e}")
        return render_template('error.html',
                             message=f"Greška pri učitavanju dashboarda: {str(e)}"), 500

# DODAJTE OVO U app.py ispod postojećih ruta

@app.route('/agent/history')
def agent_history_page():
    """HTML stranica sa historijom agent tick-ova"""
    try:
        # Poboljšana verzija: koristi globalni tick_history
        global tick_history
        
        # Pripremi podatke za template - KORISTITE DRUGO IME
        history_data = []  
        for item in tick_history:
            simplified = {
                "patient_id": item.get("patient_id", "N/A"),
                "therapy_id": item.get("therapy_id"),
                "action_taken": item.get("action_taken"),
                "timestamp": item.get("timestamp"),
                "risk_level": item.get("assessment", {}).get("risk_level") if item.get("assessment") else "NONE",
                "interaction_count": item.get("assessment", {}).get("interaction_count") if item.get("assessment") else 0
            }
            history_data.append(simplified)
        
        # Izračunaj statistike
        stats = {
            'escalate_count': sum(1 for item in history_data if item.get('action_taken') == 'ESCALATE'),
            'warn_count': sum(1 for item in history_data if item.get('action_taken') == 'WARN'),
            'patients': list(set(item.get('patient_id') for item in history_data if item.get('patient_id')))
        }
        
        # Sortiraj po vremenu (najnovije prvo)
        history_data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # PROSLIJEDI SA DRUGIM IMENOM
        return render_template('history.html',
                             history_items=history_data,  # OVO JE PROMJENA: history_items umjesto history
                             stats=stats,
                             total_count=len(tick_history))
                             
    except Exception as e:
        print(f"Greška pri učitavanju historije: {e}")
        return render_template('error.html',
                             message=f"Greška pri učitavanju historije: {str(e)}"), 500

@app.route('/therapies', methods=['GET'])
def therapies_page():
    """HTML stranica sa svim terapijama"""
    try:
        from DDIAgent.infrastructure.database import Database
        from DDIAgent.infrastructure.therapy_repository import TherapyRepository
        
        db = Database(DB_PATH)
        repo = TherapyRepository(db)
        therapies = repo.find_all()
        
        # Pripremi terapije za prikaz
        therapies_display = []
        for therapy in therapies:
            # Pronađi posljednju procjenu
            last_assessment_info = "Nikad"
            if therapy.risk_history:
                last_record = therapy.risk_history[-1]
                if 'assessment_time' in last_record:
                    try:
                        time_str = last_record['assessment_time']
                        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                        last_assessment_info = dt.strftime("%d.%m.%Y %H:%M")
                    except:
                        last_assessment_info = "Nedavno"
            
            therapies_display.append({
                'id': therapy.id,
                'patient_id': therapy.patient_id,
                'drug_count': therapy.drug_count,
                'status': therapy.status,
                'risk_tolerance': therapy.risk_tolerance,
                'last_assessment': last_assessment_info,
                'last_risk_level': therapy.last_risk_level.value if therapy.last_risk_level else 'N/A',
                'ignored_warnings': therapy.ignored_warnings_count
            })
        
        return render_template('therapies.html',
                             therapies=therapies_display,
                             total_count=len(therapies))
        
    except Exception as e:
        print(f"Greška pri učitavanju terapija: {e}")
        return render_template('error.html',
                             message=f"Greška pri učitavanju terapija: {str(e)}"), 500



@app.route('/api/feedback/submit', methods=['POST'])
def submit_feedback_to_runner():
    """Feedback endpoint koji direktno poziva runnerov learn_from_feedback"""
    try:
        data = request.json or request.form
        feedback_type = data.get('feedback_type', '').lower()
        therapy_id = data.get('therapy_id')
        notes = data.get('notes', '')
        
        if not feedback_type:
            return jsonify({
                "status": "error",
                "message": "feedback_type je obavezan (confirmed/false_alarm/ignored)"
            }), 400
        
        if not therapy_id:
            return jsonify({
                "status": "error",
                "message": "therapy_id je obavezan"
            }), 400
        
        # Validiraj feedback_type
        valid_types = ['confirmed', 'false_alarm', 'ignored']
        if feedback_type not in valid_types:
            return jsonify({
                "status": "error",
                "message": f"feedback_type mora biti jedan od: {', '.join(valid_types)}"
            }), 400
        
        from DDIAgent.infrastructure.database import Database
        from DDIAgent.infrastructure.therapy_repository import TherapyRepository
        
        db = Database(DB_PATH)
        repo = TherapyRepository(db)
        
        # 1. PRVO: Ažuriraj feedback u bazi (JEDAN PUT!)
        success = repo.update_feedback_counts(int(therapy_id), feedback_type, notes)
        
        if not success:
            return jsonify({
                "status": "error",
                "message": f"Terapija {therapy_id} nije pronađena"
            }), 404
        
        # 2. DRUGO: Učitaj ažuriranu terapiju
        therapy = repo.find_by_id(int(therapy_id))
        
        if not therapy:
            return jsonify({
                "status": "error",
                "message": f"Terapija {therapy_id} nije pronađena nakon ažuriranja"
            }), 404
        
        # 3. TREĆE: Pozovi runner za učenje (ako postoji)
        global runner
        agent_learning_data = {}
        
        if runner:
            # Odredi severity na osnovu posljednje procjene
            warning_severity = "MEDIUM"
            if therapy.risk_history:
                latest = therapy.risk_history[-1]
                warning_severity = latest.get('risk_level', 'MEDIUM')
            
            print(f"[FEEDBACK] Pozivam runner.learn_from_feedback za terapiju {therapy.id}, feedback: {feedback_type}")
            
            try:
                if hasattr(runner, 'learn_from_feedback'):
                    # SAMO prilagodi prag, NE ažuriraj terapiju ponovo
                    runner._adjust_threshold_from_feedback(feedback_type, warning_severity)
                    runner._update_learning_stats(feedback_type)
                    runner._save_threshold_to_db()
                    
                    # Prikupi podatke o učenju
                    agent_learning_data = {
                        "adaptive_threshold": runner.adaptive_threshold if hasattr(runner, 'adaptive_threshold') else None,
                        "learning_applied": True,
                        "feedback_type": feedback_type
                    }
                    print(f"[FEEDBACK] Runner je učio iz feedback-a, novi prag: {runner.adaptive_threshold}")
                else:
                    agent_learning_data = {"learning_applied": False, "reason": "runner nema learn_from_feedback"}
                    
            except Exception as e:
                print(f"[FEEDBACK] Greška u runner.learn_from_feedback: {e}")
                agent_learning_data = {"learning_applied": False, "error": str(e)}
        else:
            agent_learning_data = {"learning_applied": False, "reason": "runner nije inicijaliziran"}
        
        # 4. Vrati success response
        return jsonify({
            "status": "success",
            "message": "Feedback uspješno primljen! Agent će učiti iz vašeg odgovora.",
            "therapy": {
                "id": therapy.id,
                "patient_id": therapy.patient_id,
                "confirmed_warnings": getattr(therapy, 'confirmed_warnings_count', 0),
                "false_alarms": getattr(therapy, 'false_alarms_count', 0),
                "ignored_warnings": therapy.ignored_warnings_count,
                "total_feedback": len(getattr(therapy, 'feedback_history', []))
            },
            "feedback_saved": True,
            "agent_learning": agent_learning_data
        })
        
    except Exception as e:
        print(f"❌ Greška pri slanju feedback-a: {e}")
        return jsonify({
            "status": "error",
            "message": f"Greška pri slanju feedback-a: {str(e)}"
        }), 500
    
@app.route('/api/debug/runner-state', methods=['GET'])
def debug_runner_state():
    """Provjeri stanje runnera"""
    global runner
    
    try:
        if not runner:
            return jsonify({"error": "Runner nije inicijaliziran"}), 404
        
        # Učitaj neku terapiju sa feedback-om
        from DDIAgent.infrastructure.database import Database
        from DDIAgent.infrastructure.therapy_repository import TherapyRepository
        
        db = Database(DB_PATH)
        repo = TherapyRepository(db)
        
        # Pronađi terapiju sa feedback-om
        therapies = repo.find_all()
        therapy_with_feedback = None
        
        for therapy in therapies:
            if hasattr(therapy, 'confirmed_warnings_count') and therapy.confirmed_warnings_count > 0:
                therapy_with_feedback = therapy
                break
        
        return jsonify({
            "runner": {
                "adaptive_threshold": runner.adaptive_threshold if hasattr(runner, 'adaptive_threshold') else None,
                "learning_stats": runner.learning_stats if hasattr(runner, 'learning_stats') else None,
                "type": type(runner).__name__
            },
            "therapy_with_feedback": {
                "id": therapy_with_feedback.id if therapy_with_feedback else None,
                "patient_id": therapy_with_feedback.patient_id if therapy_with_feedback else None,
                "confirmed_warnings": getattr(therapy_with_feedback, 'confirmed_warnings_count', 0) if therapy_with_feedback else 0,
                "feedback_history_length": len(getattr(therapy_with_feedback, 'feedback_history', [])) if therapy_with_feedback else 0
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/feedback/success')
def feedback_success_page():
    """Stranica za prikaz uspješnog feedback submissiona"""
    feedback_type = request.args.get('type', 'unknown')
    therapy_id = request.args.get('therapy_id', '0')
    threshold = request.args.get('threshold', '3.0')
    
    # Pronađi terapiju za prikaz detalja
    try:
        from DDIAgent.infrastructure.database import Database
        from DDIAgent.infrastructure.therapy_repository import TherapyRepository
        
        db = Database(DB_PATH)
        repo = TherapyRepository(db)
        therapy = repo.find_by_id(int(therapy_id)) if therapy_id.isdigit() else None
        
        # DODAJ OVO: Nakon što pronadješ terapiju, provjeri feedback statistike
        if therapy:
            # Pripremi dictionary sa ažuriranim statistikama
            therapy_data = {
                "id": therapy.id,
                "patient_id": therapy.patient_id,
                "drug_count": therapy.drug_count,
                "status": therapy.status,
                "risk_tolerance": therapy.risk_tolerance,
                "confirmed_warnings_count": getattr(therapy, 'confirmed_warnings_count', 0),
                "false_alarms_count": getattr(therapy, 'false_alarms_count', 0),
                "ignored_warnings_count": therapy.ignored_warnings_count,
                "feedback_history": getattr(therapy, 'feedback_history', []),
                "drugs": [
                    {
                        "drug_id": drug.drug_id,
                        "name": drug.name,
                        "dosage": drug.dosage or "Nije navedeno"
                    }
                    for drug in therapy.drugs
                ],
                "risk_history": therapy.risk_history or []
            }
            # Proslijedi dictionary umjesto ORM objekta
            therapy = therapy_data
    except Exception as e:
        print(f"Greška pri učitavanju terapije: {e}")
        therapy = None
    
    # Pripremi poruku na osnovu feedback tipa
    messages = {
        'confirmed': {
            'title': '✅ Potvrđeno upozorenje',
            'message': 'Hvala što ste potvrdili upozorenje! Agent će postati osjetljiviji na slične slučajeve.',
            'icon': 'check-circle',
            'color': 'success'
        },
        'false_alarm': {
            'title': '⚠️ Lažna uzbuna',
            'message': 'Hvala što ste prijavili lažnu uzbunu! Agent će postati manje osjetljiv na slične slučajeve.',
            'icon': 'exclamation-triangle',
            'color': 'warning'
        },
        'ignored': {
            'title': '🔕 Ignorisano upozorenje',
            'message': 'Hvala na feedback-u! Agent će uzeti u obzir da ste ignorisali ovo upozorenje.',
            'icon': 'eye-slash',
            'color': 'secondary'
        }
    }
    
    feedback_info = messages.get(feedback_type, {
        'title': '📝 Feedback primljen',
        'message': 'Hvala na feedback-u!',
        'icon': 'chat-left-text',
        'color': 'info'
    })

    current_time = datetime.now()
    
    return render_template('feedback_success.html',
                         feedback_info=feedback_info,
                         therapy=therapy,
                         feedback_type=feedback_type,
                         threshold=threshold,
                         current_time=current_time)


@app.route('/api/test/create-sample', methods=['GET', 'POST'])
def create_sample_therapy():
    """Kreiraj test terapiju za demo i prikaži success stranicu"""
    try:
        from DDIAgent.infrastructure.database import Database
        from DDIAgent.infrastructure.therapy_repository import TherapyRepository
        from DDIAgent.domain.entities import Therapy, Drug
        
        db = Database(DB_PATH)
        repo = TherapyRepository(db)
        
        # PRVO: Provjeri da li već postoji TEST terapija
        existing_therapies = repo.find_all()
        test_therapy = None
        
        for therapy in existing_therapies:
            if therapy.patient_id == "TEST001":
                test_therapy = therapy
                break
        
        # Ako postoji, koristi postojeću
        if test_therapy:
            saved_therapy = test_therapy
            message = "Korištena postojeća test terapija"
        else:
            # Ako ne postoji, kreiraj novu
            test_drugs = [
                Drug(drug_id="DB00619", name="Aspirin", dosage="100mg 1x dnevno"),
                Drug(drug_id="DB00682", name="Warfarin", dosage="5mg 1x dnevno"),
                Drug(drug_id="DB01050", name="Ibuprofen", dosage="400mg 3x dnevno")
            ]
            
            therapy = Therapy(
                patient_id="TEST001",
                drugs=test_drugs,
                status="ACTIVE",
                risk_tolerance=3.0
            )
            
            saved_therapy = repo.save(therapy)
            message = "Kreirana nova test terapija"
        
        # Automatski pokreni agentov tick za ovu terapiju
        global runner
        if runner:
            from DDIAgent.domain.entities import TherapyPercept
            
            percept = TherapyPercept(
                therapy=saved_therapy,
                requires_assessment=True,
                last_assessment_time=None,
                source="TEST_THERAPY"
            )
            
            assessment, action = runner._think(percept)
            warning = None
            if action and action.name != "INFORM":
                warning = runner._act(percept, assessment, action)
            
            runner._learn(percept, assessment, warning)
        
        # Renderuj HTML stranicu
        therapy_data = {
            "id": saved_therapy.id,
            "patient_id": saved_therapy.patient_id,
            "drug_count": saved_therapy.drug_count,
            "status": saved_therapy.status,
            "risk_tolerance": saved_therapy.risk_tolerance,
            "message": message
        }
        
        return render_template('test_created.html', therapy=therapy_data)
        
    except Exception as e:
        return render_template('error.html',
                             message=f"Greška pri kreiranju test terapije: {str(e)}"), 500

@app.route('/agent/status')
def agent_status_page():
    """HTML stranica sa statusom agenta"""
    try:
        global runner
        
        is_running = agent_thread is not None and agent_thread.is_alive()
        runner_type = type(runner).__name__ if runner else None
        adaptive_threshold = runner.adaptive_threshold if runner and hasattr(runner, 'adaptive_threshold') else None
        
        # Prepare data for template
        agent_data = {
            "initialized": runner is not None,
            "type": runner_type,
            "running_in_background": is_running,
            "adaptive_threshold": adaptive_threshold,
            "database": DB_PATH if os.path.exists(DB_PATH) else "N/A",
            "csv_available": os.path.exists(CSV_PATH)
        }
        
        # Prepare history for template
        history_data = {
            "total_ticks": len(tick_history),
            "recent_ticks": len(tick_history[-10:]),
            "last_actions": tick_history[-5:] if tick_history else []
        }
        
        return render_template('agent_status.html', 
                             agent=agent_data, 
                             history=history_data)
                             
    except Exception as e:
        return render_template('error.html', 
                             message=f"Greška pri učitavanju statusa agenta: {str(e)}"), 500


@app.route('/api/test/repository/<int:therapy_id>', methods=['GET'])
def test_repository_feedback(therapy_id):
    """Testiraj repository feedback funkcije"""
    try:
        from DDIAgent.infrastructure.database import Database
        from DDIAgent.infrastructure.therapy_repository import TherapyRepository
        
        db = Database(DB_PATH)
        repo = TherapyRepository(db)
        
        # Učitaj terapiju
        therapy = repo.find_by_id(therapy_id)
        if not therapy:
            return jsonify({"error": "Terapija ne postoji"}), 404
        
        # Testiraj update feedback counts
        success = repo.update_feedback_counts(therapy_id, 'confirmed')
        
        # Ponovo učitaj da vidimo promjene
        therapy_updated = repo.find_by_id(therapy_id)
        
        return jsonify({
            "status": "success" if success else "error",
            "original": {
                "confirmed_count": getattr(therapy, 'confirmed_warnings_count', 0),
                "false_alarms_count": getattr(therapy, 'false_alarms_count', 0),
                "feedback_history": getattr(therapy, 'feedback_history', [])
            },
            "updated": {
                "confirmed_count": getattr(therapy_updated, 'confirmed_warnings_count', 0),
                "false_alarms_count": getattr(therapy_updated, 'false_alarms_count', 0),
                "feedback_history": getattr(therapy_updated, 'feedback_history', [])
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/debug/session/<int:therapy_id>')
def debug_session_state(therapy_id):
    """Debug SQLAlchemy session state"""
    try:
        from DDIAgent.infrastructure.database import Database
        from DDIAgent.infrastructure.therapy_repository import TherapyRepository
        
        db = Database(DB_PATH)
        repo = TherapyRepository(db)
        
        # Uzmi dvaput da vidimo caching
        therapy1 = repo.find_by_id(therapy_id)
        
        if not therapy1:
            return "Therapy not found"
        
        result = f"<h1>Debug SQLAlchemy Session State - Therapy {therapy_id}</h1>"
        
        # Prvo učitavanje
        result += f"<h2>First load (maybe cached):</h2>"
        result += f"<p>confirmed_warnings_count: {getattr(therapy1, 'confirmed_warnings_count', 0)}</p>"
        result += f"<p>false_alarms_count: {getattr(therapy1, 'false_alarms_count', 0)}</p>"
        result += f"<p>feedback_history length: {len(getattr(therapy1, 'feedback_history', []))}</p>"
        
        # Eksplicitno refresh
        therapy_refreshed = repo.refresh(therapy1)
        result += f"<h2>After explicit refresh:</h2>"
        result += f"<p>confirmed_warnings_count: {getattr(therapy_refreshed, 'confirmed_warnings_count', 0)}</p>"
        result += f"<p>false_alarms_count: {getattr(therapy_refreshed, 'false_alarms_count', 0)}</p>"
        result += f"<p>feedback_history length: {len(getattr(therapy_refreshed, 'feedback_history', []))}</p>"
        
        # Direktno iz baze
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT confirmed_warnings_count, false_alarms_count FROM therapies WHERE id = ?", (therapy_id,))
        db_row = cursor.fetchone()
        conn.close()
        
        result += f"<h2>Direct from database:</h2>"
        if db_row:
            result += f"<p>confirmed_warnings_count: {db_row[0]}</p>"
            result += f"<p>false_alarms_count: {db_row[1]}</p>"
        else:
            result += "<p>Not found in database</p>"
        
        return result
        
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/agent/tick', methods=['GET', 'POST'])
def execute_tick_page():
    """HTML stranica za izvršavanje tick-a i prikaz rezultata"""
    try:
        from datetime import datetime
        
        # GET parametri za specificnu terapiju
        therapy_id = request.args.get('therapy_id')
        
        # Ako je POST request, izvrši tick
        if request.method == 'POST':
            runner = initialize_agent()
            
            # Ako je specificirana terapija, procesuiraj SAMO tu
            if therapy_id:
                try:
                    from DDIAgent.infrastructure.database import Database
                    from DDIAgent.infrastructure.therapy_repository import TherapyRepository
                    from DDIAgent.domain.entities import TherapyPercept
                    from DDIAgent.application.runners.risk_assessment_runner import TickResult  
                    therapy_id_int = int(therapy_id)
                    db = Database(DB_PATH)
                    repo = TherapyRepository(db)
                    therapy = repo.find_by_id(therapy_id_int)
                    
                    if therapy:
                        # Process SAMO ovu terapiju
                        percept = TherapyPercept(
                            therapy=therapy,
                            requires_assessment=True,
                            last_assessment_time=therapy.last_assessment_time,
                            source="MANUAL_REQUEST"
                        )
                        
                        # THINK
                        assessment, action = runner._think(percept)
                        
                        # ACT
                        warning = None
                        if action and action.name != "INFORM":
                            warning = runner._act(percept, assessment, action)
                        
                        # LEARN
                        runner._learn(percept, assessment, warning)
                        
                        # Kreiraj result objekat - KORISTI TICKResult, NE RiskAssessmentResult
                        result = TickResult(
                            has_work=True,
                            therapy_id=therapy.id,
                            patient_id=therapy.patient_id,
                            drug_count=therapy.drug_count,
                            assessment=assessment,
                            action_taken=action,
                            warning=warning,
                            timestamp=datetime.now()
                        )
                    else:
                        result = None
                        response_data = {
                            "tick_executed": False,
                            "error": f"Terapija ID {therapy_id} nije pronađena",
                            "message": "Terapija ne postoji"
                        }
                except Exception as e:
                    result = None
                    response_data = {
                        "tick_executed": False,
                        "error": str(e),
                        "message": f"Greška pri obradi terapije {therapy_id}"
                    }
            else:
                # Regular tick - uzima prvu terapiju iz queue
                result = runner.tick()
            
            # Ako ima result (regular tick ili uspješan specificni)
            if result and hasattr(result, 'has_work') and result.has_work:
                # Snimi u historiju
                tick_history.append(result.to_dict())
                if len(tick_history) > 50:
                    tick_history.pop(0)
                
                response_data = {
                    "tick_executed": True,
                    "agent_cycle": "Sense → Think → Act → Learn",
                    "result": result.to_dict(),
                    "message": f"Agent je obradio terapiju za pacijenta {result.patient_id}"
                }
            elif not therapy_id and result and hasattr(result, 'has_work') and not result.has_work:
                # Nema terapija za obradu
                response_data = {
                    "tick_executed": True,
                    "agent_cycle": "Sense (no work)",
                    "result": None,
                    "message": "Nema terapija za obradu u ovom tick-u"
                }
            elif therapy_id and not result:  # Greška pri specificnom tick-u
                # response_data je već postavljen u try-catch bloku
                pass
            else:
                response_data = {
                    "tick_executed": False,
                    "agent_cycle": "Nije izvršen",
                    "result": None,
                    "message": "Nepoznata greška"
                }
                
        else:
            # Ako je GET request, pokaži praznu stranicu
            response_data = {
                "tick_executed": False,
                "agent_cycle": "Nije izvršen",
                "result": None,
                "message": "Kliknite 'Novi tick' da pokrenete agenta"
            }
        
        return render_template('tick_result.html',
                             result=response_data,
                             timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                             
    except Exception as e:
        error_data = {
            "tick_executed": False,
            "error": str(e),
            "message": "Greška pri izvršavanju agent tick-a"
        }
        return render_template('tick_result.html',
                             result=error_data,
                             timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# ============================================
# ERROR HANDLER
# ============================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message="Stranica nije pronađena"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', message="Interna serverska greška"), 500

# ============================================
# POKRETANJE
# ============================================
if __name__ == '__main__':
    try:
        # Inicijalizuj agenta
        initialize_agent()
        print("✅ Aplikacija spremna!")
        
    except FileNotFoundError as e:
        print(f"\n🔴 KRITIČNA GREŠKA: {e}")
        print(f"\n🛠️  HITNO RJEŠENJE:")
        print(f"   Pokreni ovu komandu u terminalu:")
        print(f"   copy '{PROJECT_ROOT}\\data\\DDI_with_scores.csv' '{CENTRAL_DATA_DIR}\\'")
        print(f"\n📁 CSV bi trebao biti na: {CSV_PATH}")
        print(f"📁 Trenutno se nalazi na: {PROJECT_ROOT}\\data\\DDI_with_scores.csv")
        print(f"\n⚠️  API će raditi, ali agent neće moći analizirati interakcije!")
        
    except Exception as e:
        print(f"⚠️  Greška pri inicijalizaciji: {e}")
        print("⚠️  API će raditi, ali agent funkcionalnosti možda neće")
    
    print("\n" + "="*60)
    print("🌐 DDI AGENT WEB API")
    print("="*60)
    print(f"📍 Server: http://127.0.0.1:5000")
    print(f"📊 Baza: {DB_PATH}")
    print(f"📁 CSV: {'✅ Dostupan' if os.path.exists(CSV_PATH) else '❌ Nedostaje - agent neće raditi'}")
    print("="*60)
    
    app.run(debug=True, port=5000, use_reloader=False)