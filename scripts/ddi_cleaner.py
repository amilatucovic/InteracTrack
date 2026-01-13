import pandas as pd
import numpy as np

# Učitavanje podataka
df = pd.read_csv('data/DDI_data.csv')
print(f"Ukupno redova: {len(df)}")
print(f"Kolone: {df.columns.tolist()}")
print("\nPrvih 5 redova:")
print(df.head())

# Provjera duplikata
print(f"\nBroj duplikata: {df.duplicated().sum()}")

# Provjera različitih interakcija
print(f"\nBroj jedinstvenih interakcija: {len(df[['drug1_id', 'drug2_id']].drop_duplicates())}")
print(f"Broj jedinstvenih lijekova: {len(set(df['drug1_id'].tolist() + df['drug2_id'].tolist()))}")

def clean_ddi_data(df):
    """
    Čišćenje DDI podataka:
    1. Uklanjanje potpunih duplikata
    2. Provjera i uklanjanje simetričnih duplikata (A-B i B-A)
    """
    
    print(f"Početno: {len(df)} redova")
    
    # 1. Ukloni potpune duplikate
    df_clean = df.drop_duplicates()
    print(f"Poslije uklanjanja potpunih duplikata: {len(df_clean)} redova")
    
    # 2. Provjeri da li ima simetričnih duplikata
    # Kreiraj normalizovanu kolonu za provjeru
    def create_symmetric_key(row):
        ids = sorted([row['drug1_id'], row['drug2_id']])
        return f"{ids[0]}|{ids[1]}|{row['interaction_type']}"
    
    df_clean = df_clean.copy()
    df_clean['symmetric_key'] = df_clean.apply(create_symmetric_key, axis=1)
    
    # Koliko ima simetričnih duplikata?
    before = len(df_clean)
    df_clean = df_clean.drop_duplicates(subset=['symmetric_key'])
    after = len(df_clean)
    
    print(f"Simetričnih duplikata pronađeno: {before - after}")
    print(f"Poslije uklanjanja simetričnih duplikata: {after} redova")
    
    # Ukloni pomoćnu kolonu
    df_clean = df_clean.drop(columns=['symmetric_key'])
    
    return df_clean

df_clean = clean_ddi_data(df)

def standardize_drug_names(df):
    """
    Standardizuje nazive lijekova:
    1. Sve velika slova u prvo veliko
    2. Uklanjanje suvišnih razmaka
    3. Kreiranje lookup tabele za konzistentnost
    """
    
    # Funkcija za standardizaciju naziva
    def standardize_name(name):
        if pd.isna(name):
            return name
        # Prvo veliko slovo, ostala mala
        name = name.strip()
        if len(name) > 1:
            return name[0].upper() + name[1:].lower()
        return name.upper()
    
    # Primijeni na oba naziva
    df['drug1_name'] = df['drug1_name'].apply(standardize_name)
    df['drug2_name'] = df['drug2_name'].apply(standardize_name)
    
    # Kreiraj lookup tabelu lijekova
    drugs = {}
    for _, row in df.iterrows():
        drugs[row['drug1_id']] = row['drug1_name']
        drugs[row['drug2_id']] = row['drug2_name']
    
    # Provjeri konzistentnost (isti ID uvijek ima isti naziv)
    drug_consistency = {}
    for drug_id, name in drugs.items():
        if drug_id in drug_consistency:
            if drug_consistency[drug_id] != name:
                print(f"Upozorenje: ID {drug_id} ima različite nazive: {drug_consistency[drug_id]} vs {name}")
        else:
            drug_consistency[drug_id] = name
    
    print(f"Broj jedinstvenih lijekova: {len(drug_consistency)}")
    
    return df, drug_consistency

df_clean, drug_lookup = standardize_drug_names(df_clean)

# Dodajte ovo nakon čišćenja:

def analyze_interaction_types(df):
    """Analiza tipova interakcija"""
    print("\n" + "="*60)
    print("ANALIZA TIPOVA INTERAKCIJA")
    print("="*60)
    
    # Broj različitih tipova interakcija
    interaction_counts = df['interaction_type'].value_counts()
    print(f"\nBroj različitih tipova interakcija: {len(interaction_counts)}")
    
    # Top 10 najčešćih interakcija
    print("\n🔝 TOP 10 NAJČEŠĆIH INTERAKCIJA:")
    for i, (interaction, count) in enumerate(interaction_counts.head(10).items(), 1):
        percentage = (count / len(df)) * 100
        print(f"{i:2}. {interaction:50} {count:6} ({percentage:.1f}%)")
    
    # Analiza po lijekovima
    print("\n🏆 TOP 5 LIJEKOVA SA NAJVIŠE INTERAKCIJA:")
    
    # Računaj interakcije po lijeku
    drug_interactions = {}
    for _, row in df.iterrows():
        drug_interactions[row['drug1_id']] = drug_interactions.get(row['drug1_id'], 0) + 1
        drug_interactions[row['drug2_id']] = drug_interactions.get(row['drug2_id'], 0) + 1
    
    # Sortiraj
    top_drugs = sorted(drug_interactions.items(), key=lambda x: x[1], reverse=True)[:5]
    
    for i, (drug_id, count) in enumerate(top_drugs, 1):
        # Pronađi ime lijeka
        drug_rows = df[(df['drug1_id'] == drug_id) | (df['drug2_id'] == drug_id)]
        if len(drug_rows) > 0:
            drug_name = drug_rows.iloc[0]['drug1_name'] if drug_rows.iloc[0]['drug1_id'] == drug_id else drug_rows.iloc[0]['drug2_name']
        else:
            drug_name = "Unknown"
        
        print(f"{i}. {drug_name:30} ({drug_id}): {count:5} interakcija")
    
    return interaction_counts

# Pozovite funkciju
interaction_counts = analyze_interaction_types(df_clean)

# Sačuvaj očišćene podatke
output_file = 'data/DDI_data_cleaned.csv'
df_clean.to_csv(output_file, index=False)
print(f"\n Očišćeni podaci sačuvani u: {output_file}")

# Kreiraj i sačuvaj lookup tabelu lijekova
print("📋 KREIRAM LOOKUP TABELU LIJEKOVA...")

import json

# Već imate drug_lookup iz standardize_drug_names
print(f"Pronađeno {len(drug_lookup)} jedinstvenih lijekova")

# Sačuvaj kao JSON
with open('data/drug_lookup.json', 'w', encoding='utf-8') as f:
    json.dump(drug_lookup, f, ensure_ascii=False, indent=2)
print(f"💾 Lookup tabela sačuvana u: data/drug_lookup.json")

# Kreiraj i sačuvaj statistiku
stats = {
    'total_interactions': len(df_clean),
    'unique_drugs': len(drug_lookup),
    'interaction_types': len(interaction_counts),
    'top_interactions': interaction_counts.head(20).to_dict(),
    'top_drugs': {}
}

# Dodaj top lijekove u statistiku
drug_interactions = {}
for _, row in df_clean.iterrows():
    drug_interactions[row['drug1_id']] = drug_interactions.get(row['drug1_id'], 0) + 1
    drug_interactions[row['drug2_id']] = drug_interactions.get(row['drug2_id'], 0) + 1

top_10_drugs = sorted(drug_interactions.items(), key=lambda x: x[1], reverse=True)[:10]
for drug_id, count in top_10_drugs:
    stats['top_drugs'][drug_id] = {
        'name': drug_lookup.get(drug_id, 'Unknown'),
        'interaction_count': count
    }

with open('data/ddi_stats.json', 'w', encoding='utf-8') as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)
print(f"💾 Statistika sačuvana u: data/ddi_stats.json")

# Dodaj još jednu korisnu analizu
print("\n📊 DODATNA ANALIZA:")

# Analiza rizika po tipovima interakcija
interaction_risk_groups = {
    'HIGH_RISK': ['bleeding', 'cardiotoxic', 'nephrotoxic', 'hepatotoxic', 'qtc', 'arrhythmia'],
    'MODERATE_RISK': ['serum concentration', 'metabolism', 'excretion'],
    'THERAPEUTIC': ['therapeutic efficacy', 'hypotensive', 'antihypertensive'],
    'OTHER': []
}

high_risk_count = 0
for interaction in df_clean['interaction_type'].unique():
    interaction_lower = interaction.lower()
    for risk_group, keywords in interaction_risk_groups.items():
        if any(keyword in interaction_lower for keyword in keywords):
            if risk_group == 'HIGH_RISK':
                high_risk_count += df_clean[df_clean['interaction_type'] == interaction].shape[0]
            break

print(f"Visoko rizičnih interakcija: {high_risk_count} ({high_risk_count/len(df_clean)*100:.1f}%)")

# Provjera za najopasnije kombinacije
print("\n 5 NAJČEŠĆIH VISOKO RIZIČNIH INTERAKCIJA:")
high_risk_interactions = []
for interaction_type, count in interaction_counts.items():
    interaction_lower = interaction_type.lower()
    if any(keyword in interaction_lower for keyword in interaction_risk_groups['HIGH_RISK']):
        high_risk_interactions.append((interaction_type, count))

high_risk_interactions.sort(key=lambda x: x[1], reverse=True)
for i, (interaction, count) in enumerate(high_risk_interactions[:5], 1):
    print(f"{i}. {interaction}: {count}")

print("\n" + "="*60)
print("✅ ČIŠĆENJE I ANALIZA ZAVRŠENI!")
print("="*60)

