# DDIAgent/infrastructure/migrations/add_feedback_columns.py
"""
Migracija za dodavanje novih kolona u postojeću bazu - ISPRAVLJENA
"""
import sqlite3
import sys
import os

def add_missing_columns():
    print("🔄 Dodajem nove kolone u postojeću bazu...")
    
    db_path = "data/ddi_agent.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Baza ne postoji: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Provjeri koje kolone već postoje u 'therapies' tabeli
        cursor.execute("PRAGMA table_info(therapies)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        print(f"Postojeće kolone: {existing_columns}")
        
        # Lista kolona koje treba dodati
        columns_to_add = [
            ("feedback_history", "TEXT", "'[]'"),  # Obratite pažnju na navodnike!
            ("confirmed_warnings_count", "INTEGER", "0"),
            ("false_alarms_count", "INTEGER", "0")
        ]
        
        for col_name, col_type, default_value in columns_to_add:
            if col_name not in existing_columns:
                sql = f"ALTER TABLE therapies ADD COLUMN {col_name} {col_type} DEFAULT {default_value}"
                print(f"  Dodajem: {sql}")
                cursor.execute(sql)
                print(f"  ✅ Dodana kolona: {col_name}")
            else:
                print(f"  ℹ️  Kolona već postoji: {col_name}")
        
        # Provjeri 'warnings' tabelu
        cursor.execute("PRAGMA table_info(warnings)")
        warning_columns = [col[1] for col in cursor.fetchall()]
        print(f"Warnings kolone: {warning_columns}")
        
        # Dodaj kolone u warnings ako ne postoje - ISPRAVLJENO!
        warning_columns_to_add = [
            ("details", "TEXT", "'{}'"),  # STRING '{}', ne JSON {}
            ("feedback_type", "TEXT", "NULL"),
            ("feedback_notes", "TEXT", "NULL"),
            ("feedback_at", "DATETIME", "NULL"),
            ("acknowledged_at", "DATETIME", "NULL")
        ]
        
        for col_name, col_type, default_value in warning_columns_to_add:
            if col_name not in warning_columns:
                if default_value == "NULL":
                    sql = f"ALTER TABLE warnings ADD COLUMN {col_name} {col_type}"
                else:
                    sql = f"ALTER TABLE warnings ADD COLUMN {col_name} {col_type} DEFAULT {default_value}"
                print(f"  Dodajem u warnings: {sql}")
                cursor.execute(sql)
                print(f"  ✅ Dodana kolona u warnings: {col_name}")
            else:
                print(f"  ℹ️  Kolona već postoji u warnings: {col_name}")
        
        conn.commit()
        conn.close()
        
        print("✅ Migracija uspješno završena!")
        return True
        
    except Exception as e:
        print(f"❌ Greška pri migraciji: {e}")
        return False

def create_new_tables():
    """Kreiraj nove tabele ako ne postoje"""
    print("\n🔄 Kreiranje novih tabela...")
    
    try:
        # Dinamički import da izbjegnemo probleme
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from DDIAgent.infrastructure.database import Database
        
        # Ovo će kreirati sve tabele koje nedostaju
        db = Database("data/ddi_agent.db")
        
        print("✅ Sve tabele kreirane/verifikovane!")
        return True
        
    except Exception as e:
        print(f"⚠️  Greška pri kreiranju tabela: {e}")
        return False

def update_existing_data():
    """Ažuriraj postojeće podatke sa default vrijednostima"""
    print("\n🔄 Ažuriranje postojećih podataka...")
    
    try:
        conn = sqlite3.connect("data/ddi_agent.db")
        cursor = conn.cursor()
        
        # Ažuriraj postojeće terapije - ISPRAVLJENO!
        cursor.execute("""
            UPDATE therapies 
            SET feedback_history = '[]',
                confirmed_warnings_count = 0,
                false_alarms_count = 0
            WHERE feedback_history IS NULL OR feedback_history = ''
        """)
        
        updated_rows = cursor.rowcount
        print(f"  Ažurirano {updated_rows} terapija")
        
        # Ažuriraj postojeća upozorenja - ISPRAVLJENO!
        cursor.execute("""
            UPDATE warnings 
            SET details = '{}',
                feedback_type = NULL,
                feedback_notes = NULL,
                feedback_at = NULL,
                acknowledged_at = NULL
            WHERE details IS NULL OR details = ''
        """)
        
        updated_warnings = cursor.rowcount
        print(f"  Ažurirano {updated_warnings} upozorenja")
        
        conn.commit()
        conn.close()
        
        print("✅ Podaci ažurirani!")
        return True
        
    except Exception as e:
        print(f"⚠️  Greška pri ažuriranju podataka: {e}")
        return False

def main():
    print("=" * 60)
    print("DATABASE MIGRATION TOOL")
    print("=" * 60)
    
    # 1. Dodaj nove kolone
    if not add_missing_columns():
        print("❌ Migracija nije uspjela!")
        return
    
    # 2. Kreiraj nove tabele
    if not create_new_tables():
        print("⚠️  Neke tabele nisu kreirane, ali možemo nastaviti...")
    
    # 3. Ažuriraj postojeće podatke
    update_existing_data()
    
    # 4. Testiraj bazu
    print("\n🧪 Testiranje baze...")
    try:
        # Dinamički import
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from DDIAgent.infrastructure.database import Database
        
        db = Database("data/ddi_agent.db")
        
        # Provjeri terapije
        with db.get_session() as session:
            from DDIAgent.infrastructure.database import TherapyDB
            
            therapy_count = session.query(TherapyDB).count()
            print(f"✅ Ukupno terapija: {therapy_count}")
            
            # Provjeri da li kolone postoje
            sample = session.query(TherapyDB).first()
            if sample:
                print(f"✅ Kolone verificirane:")
                print(f"   • feedback_history: {sample.feedback_history}")
                print(f"   • confirmed_warnings_count: {sample.confirmed_warnings_count}")
                print(f"   • false_alarms_count: {sample.false_alarms_count}")
        
        print("\n" + "=" * 60)
        print("🎉 MIGRACIJA USPJEŠNO ZAVRŠENA!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Testiranje nije uspjelo: {e}")

if __name__ == "__main__":
    main()