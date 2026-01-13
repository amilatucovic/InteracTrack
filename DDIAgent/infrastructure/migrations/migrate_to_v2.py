# DDIAgent/infrastructure/migrations/migrate_to_v2.py
"""
Jednostavna migracija koja sigurno radi
"""
import sys
import os

# Dodaj putanju
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.join(current_dir, '..', '..', '..')
if root_dir not in sys.path:
    sys.path.append(root_dir)

def migrate_database():
    print("🔄 Pokrećem jednostavnu migraciju baze...")
    
    try:
        # Učitaj novu Database klasu
        from DDIAgent.infrastructure.database import Database
        
        # Samo inicijalizacija će kreirati tabele
        db = Database("data/ddi_agent.db")
        
        print("✅ Migracija završena! Nove tabele kreirane.")
        return True
        
    except Exception as e:
        print(f"❌ Greška pri migraciji: {e}")
        return False

if __name__ == "__main__":
    migrate_database()