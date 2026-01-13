# create_new_tables.py
"""
Kreiraj nove tabele ručno nakon migracije
"""
import sqlite3
import json

print("🔄 Kreiranje novih tabela...")

conn = sqlite3.connect("data/ddi_agent.db")
cursor = conn.cursor()


print("1. Kreiranje 'feedbacks' tabele...")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        warning_id INTEGER NOT NULL,
        therapy_id INTEGER NOT NULL,
        patient_id TEXT NOT NULL,
        feedback_type TEXT NOT NULL,
        notes TEXT,
        threshold_before REAL NOT NULL,
        threshold_after REAL NOT NULL,
        warning_severity TEXT,
        feedback_metadata TEXT DEFAULT '{}',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")


cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedbacks_warning_id ON feedbacks(warning_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedbacks_therapy_id ON feedbacks(therapy_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedbacks_feedback_type ON feedbacks(feedback_type)")


print("2. Kreiranje 'agent_learning' tabele...")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_learning (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adaptive_threshold REAL DEFAULT 3.0,
        total_feedbacks INTEGER DEFAULT 0,
        confirmed_count INTEGER DEFAULT 0,
        ignored_count INTEGER DEFAULT 0,
        false_alarm_count INTEGER DEFAULT 0,
        current_accuracy REAL DEFAULT 0.0,
        accuracy_history TEXT DEFAULT '[]',
        learning_metrics_data TEXT DEFAULT '{}',
        recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")


print("3. Dodavanje početnog agent learning record-a...")
cursor.execute("SELECT COUNT(*) FROM agent_learning")
count = cursor.fetchone()[0]

if count == 0:
    learning_metrics = json.dumps({
        'learning_rate': 0.1,
        'confirmed_adjustment': -0.2,
        'ignored_adjustment': 0.3,
        'false_alarm_penalty': 0.5
    })
    
    cursor.execute("""
        INSERT INTO agent_learning 
        (adaptive_threshold, learning_metrics_data)
        VALUES (?, ?)
    """, (3.0, learning_metrics))
    print("   ✅ Početni record dodan")
else:
    print("   ℹ️  Record već postoji")

conn.commit()


print("\n4. Provjera tabela...")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
print("Postojeće tabele:")
for table in tables:
    print(f"   • {table[0]}")


print("\n5. Provjera kolona:")
for table_name in ['therapies', 'warnings', 'feedbacks', 'agent_learning']:
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print(f"\n{table_name}:")
    for col in columns:
        col_name = col[1]
        col_type = col[2]
        print(f"   • {col_name} ({col_type})")

conn.close()

print("\n" + "="*60)
print("🎉 NOVE TABELE USPJEŠNO KREIRANE!")
print("="*60)