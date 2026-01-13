import pandas as pd
import json
from collections import Counter

print("="*60)
print("DDI SCORING SISTEM")
print("="*60)

# Učitaj očišćene podatke
df = pd.read_csv('data/DDI_data_cleaned.csv')
print(f"✅ Učitano {len(df)} interakcija")

# Učitaj lookup tabelu lijekova
with open('data/drug_lookup.json', 'r', encoding='utf-8') as f:
    drug_lookup = json.load(f)
print(f"✅ Učitano {len(drug_lookup)} lijekova")

# Analiza tipova interakcija
print("\n📊 ANALIZA TIPOVA INTERAKCIJA:")
interaction_counts = df['interaction_type'].value_counts()
print(f"Broj različitih tipova: {len(interaction_counts)}")

print("\n🔝 TOP 15 NAJČEŠĆIH INTERAKCIJA:")
for i, (interaction, count) in enumerate(interaction_counts.head(15).items(), 1):
    percentage = (count / len(df)) * 100
    print(f"{i:2}. {interaction:45} {count:6} ({percentage:.1f}%)")

# Definišimo DETAILAN scoring sistem
print("\n⚖️ KREIRAM SCORING SISTEM...")

scoring_categories = {
    # KRITIČNE interakcije (score 5)
    'CRITICAL_BLEEDING': {
        'score': 5.0,
        'keywords': ['bleeding', 'hemorrhage', 'hemorrhagic'],
        'description': 'Rizik krvarenja - životno ugrožavajuće'
    },
    'ANTICOAGULANT': {
        'score': 5.0,
        'keywords': ['anticoagulant'],
        'description': 'Antikoagulantne interakcije'
    },
    
    # VISOK rizik (score 4)
    'CARDIAC_QTc': {
        'score': 4.5,
        'keywords': ['qtc', 'cardiotoxic', 'arrhythmogenic'],
        'description': 'Srčane aritmije - QTc prolongacija'
    },
    'ORGAN_TOXICITY': {
        'score': 4.0,
        'keywords': ['nephrotoxic', 'hepatotoxic', 'neurotoxic'],
        'description': 'Oštećenje organa (bubrezi, jetra, nervi)'
    },
    'NEUROEXCITATORY': {
        'score': 4.0,  # VISOK RIZIK
        'keywords': ['neuroexcitatory','seizure', 'convulsion'],
        'description': 'Neuroekscitatorne reakcije - visok rizik'
    },
    
    'SEROTONERGIC': {
        'score': 4.5,  # VRLO VISOK RIZIK
        'keywords': ['serotonergic', 'serotonin', 'ssri', 'maoi', 'tramadol'],
        'description': 'Serotonergične interakcije - visok rizik sindroma'
    },
    
    
    # UMJEREN rizik (score 3)
    'SERUM_LEVEL': {
        'score': 3.0,
        'keywords': ['serum concentration', 'serum level', 'concentration of'],
        'description': 'Promjena koncentracije lijeka'
    },
    'METABOLISM': {
        'score': 3.0,
        'keywords': ['metabolism', 'excretion', 'absorption'],
        'description': 'Uticaj na metabolizam lijeka'
    },
    
    # NIZAK rizik (score 2)
    'THERAPEUTIC': {
        'score': 2.0,
        'keywords': ['therapeutic efficacy', 'therapeutic effect'],
        'description': 'Uticaj na efikasnost terapije'
    },
    
    # MINIMALAN rizik (score 1)
    'OTHER': {
        'score': 1.0,
        'keywords': [],
        'description': 'Ostale interakcije'
    },
   
    'ADVERSE_EFFECTS': {
      'score': 3.5,  # Umjereno visok
      'keywords': ['adverse effects', 'adverse reactions', 'side effects'],
      'description': 'Rizik od nuspojava'
  },
   'CARDIAC_OTHER': {
      'score': 3.0,
      'keywords': ['cardiac', 'hypotensive', 'antihypertensive'],
      'description': 'Ostale srčane interakcije'
    }
}

def assign_score_and_category(interaction_type):
    """Dodijeli score i kategoriju za interakciju"""
    interaction_lower = interaction_type.lower()
    
    for category_name, category_info in scoring_categories.items():
        for keyword in category_info['keywords']:
            if keyword.lower() in interaction_lower:
                return category_info['score'], category_name
    
    # Ako nije pronađeno, vrati OTHER
    return scoring_categories['OTHER']['score'], 'OTHER'

# Testiraj scoring
print("\n🧪 TEST SCORINGA:")
test_cases = [
    "risk or severity of bleeding",
    "anticoagulant activities", 
    "QTc-prolonging activities",
    "serum concentration",
    "nephrotoxic activities",
    "therapeutic efficacy",
    "metabolism",
    "risk or severity of adverse effects"
]

for test in test_cases:
    score, category = assign_score_and_category(test)
    print(f"  {test:45} → Score: {score}, Kategorija: {category}")

# Primijeni scoring na sve podatke
print("\n📝 PRIMJENA SCORINGA NA SVE INTERAKCIJE...")
df[['risk_score', 'risk_category']] = df['interaction_type'].apply(
    lambda x: pd.Series(assign_score_and_category(x))
)

# Sačuvaj podatke sa score-ovima
output_file = 'DDI_with_scores.csv'
df.to_csv(output_file, index=False)
print(f"💾 Podaci sa score-ovima sačuvani u: {output_file}")

# Prikaži distribuciju
print("\n📈 DISTRIBUCIJA SCORE-OVA:")
score_dist = df['risk_score'].value_counts().sort_index()
for score, count in score_dist.items():
    percentage = (count / len(df)) * 100
    print(f"  Score {score}: {count:8} interakcija ({percentage:5.1f}%)")

# Analiza po kategorijama
print("\n🏷️ DISTRIBUCIJA PO KATEGORIJAMA:")
category_dist = df['risk_category'].value_counts()
for category, count in category_dist.items():
    for cat_name, cat_info in scoring_categories.items():
        if cat_name == category:
            description = cat_info['description']
            break
    else:
        description = "Nepoznato"
    
    percentage = (count / len(df)) * 100
    print(f"  {category:20} ({description[:30]}...): {count:6} ({percentage:5.1f}%)")

# Analiza najopasnijih lijekova
print("\n⚠️ TOP 10 NAJOPASNIJIH LIJEKOVA (prosječan score):")
drug_scores = {}

for _, row in df.iterrows():
    # Dodaj score za prvi lijek
    drug_scores[row['drug1_id']] = drug_scores.get(row['drug1_id'], {'total': 0, 'count': 0})
    drug_scores[row['drug1_id']]['total'] += row['risk_score']
    drug_scores[row['drug1_id']]['count'] += 1
    
    # Dodaj score za drugi lijek
    drug_scores[row['drug2_id']] = drug_scores.get(row['drug2_id'], {'total': 0, 'count': 0})
    drug_scores[row['drug2_id']]['total'] += row['risk_score']
    drug_scores[row['drug2_id']]['count'] += 1

# Izračunaj prosječne score-ove
drug_avg_scores = []
for drug_id, scores in drug_scores.items():
    if scores['count'] > 0:
        avg_score = scores['total'] / scores['count']
        drug_name = drug_lookup.get(drug_id, "Unknown")
        drug_avg_scores.append((drug_id, drug_name, avg_score, scores['count']))

# Sortiraj po prosječnom score-u
drug_avg_scores.sort(key=lambda x: x[2], reverse=True)

# Prikaži top 10
for i, (drug_id, drug_name, avg_score, count) in enumerate(drug_avg_scores[:10], 1):
    print(f"{i:2}. {drug_name:30} ({drug_id}): Prosjek: {avg_score:.2f}, Interakcija: {count}")

# Kreiraj i sačuvaj scoring konfiguraciju
scoring_config = {
    'categories': scoring_categories,
    'statistics': {
        'total_interactions': len(df),
        'average_score': df['risk_score'].mean(),
        'high_risk_count': len(df[df['risk_score'] >= 4]),
        'critical_risk_count': len(df[df['risk_score'] == 5])
    },
    'top_risky_drugs': [
        {
            'drug_id': drug_id,
            'drug_name': drug_name,
            'avg_score': float(avg_score),
            'interaction_count': count
        }
        for drug_id, drug_name, avg_score, count in drug_avg_scores[:20]
    ]
}

with open('scoring_config.json', 'w', encoding='utf-8') as f:
    json.dump(scoring_config, f, ensure_ascii=False, indent=2)
print(f"\n💾 Scoring konfiguracija sačuvana u: scoring_config.json")

print("\n" + "="*60)
print("✅ SCORING SISTEM ZAVRŠEN!")
print("="*60)
