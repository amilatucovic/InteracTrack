# InteracTrack - Drug Interaction Risk Assessment Agent

An intelligent AI agent for assessing drug-drug interaction risks in clinical environments, implementing adaptive learning and real-time therapy monitoring.

## Overview

InteracTrack is an intelligent software agent designed to automatically detect potentially dangerous drug combinations, quantify their risk through an advanced rule-based scoring system, and generate clinically relevant alerts. 
Unlike static databases, this agent possesses adaptive learning capabilities, integrating clinician feedback and continuously adjusting sensitivity thresholds to minimize false alarms while maximizing precision in critical situations.

## Project Context

This project was developed as part of the **Artificial Intelligence** course at the Faculty of Information Technologies, University "Džemal Bijedić" in Mostar. 
The goal was to implement an AI agent that receives information from its environment, makes decisions, and executes actions following the **Sense → Think → Act → Learn** cycle.

## Key Features

### Core Functionalities

- **Real-time Therapy Scanning**: Continuously monitors active therapy database and automatically initiates risk assessment upon detection of new therapies or protocol changes
- **Semantic Scoring System**: Deep semantic analysis of pharmacological interaction descriptions using rule-based methodology
- **Adaptive Learning**: Dynamic adjustment of risk thresholds based on correlation between previous assessments and clinician feedback
- **Multi-factor Risk Assessment**: Holistic analysis considering total medication count (polypharmacy degree), specific drug classes, and cumulative effects
- **Contextual Alert Generation**: Structured warnings graded through four criticality levels with specific clinical action recommendations
- **Complete Audit Trail**: Maintains immutable history of all assessments and physician feedback

### Agent Classification

InteracTrack combines three types of agents:

1. **Classification Agent**: Classifies interaction risks into four levels (INFORM, REQUEST_INFO, WARN, ESCALATE)
2. **Learning Agent**: Continuously adapts decision thresholds based on user feedback and decision history
3. **Context-Aware Agent**: Considers contextual factors including therapy drug count, risk threshold, and current feedback status

### Agent Cycle Implementation

**SENSE (Perception)**
- Identifies active therapies requiring assessment
- Monitors temporal triggers and user actions
- Forms `TherapyPercept` objects for detected therapies

**THINK (Decision Making)**
- Analyzes all possible drug pairs
- Applies risk assessment policy
- Adjusts thresholds based on learned patterns

**ACT (Action)**
- Generates personalized actions based on risk level:
  - `INFORM`: Low risk informational message
  - `REQUEST_INFO`: Moderate risk requiring verification
  - `WARN`: High risk with action recommendations
  - `ESCALATE`: Critical interactions requiring immediate intervention

**LEARN (Adaptive Learning)**
- **Global Learning**: Improves accuracy across all therapies
- **Local Learning**: Builds trust for specific therapy patterns
- **Feedback Integration**: Adjusts behavior based on clinician responses

## 📊 Dataset

**Source:** [Drug-Drug Interaction Dataset (Mendeley Data)](https://data.mendeley.com/datasets/md5czfsfnd/1)  
**Origin:** DrugBank Database

### Dataset Characteristics

- **Initial Records:** 222,696 drug interactions
- **Final Records:** 222,646 (after cleaning)
- **Columns:**
  - `drug1_id`, `drug2_id`: Unique drug identifiers
  - `drug1_name`, `drug2_name`: Drug names
  - `interaction_type`: Textual description of interaction

### Data Processing

1. **Cleaning & Normalization**
   - Removed complete duplicates
   - Eliminated symmetric duplicates (A-B = B-A)
   - Standardized drug names
   - Created drug lookup table (`drug_lookup.json`)

2. **Semantic Scoring System**

Since the dataset lacks numerical severity indicators, a rule-based scoring system was implemented:

| Risk Category | Score | Examples |
|--------------|-------|----------|
| Critical | 5.0 | Bleeding risk, anticoagulant interactions |
| High | 4.0-4.5 | QTc prolongation, organ toxicity |
| Moderate | 3.0-3.5 | Drug concentration changes, side effects |
| Low | 2.0 | Reduced therapeutic efficacy |
| Minimal | 1.0 | Other interactions |

Each record receives:
- Numerical `risk_score`
- Semantic `risk_category`

## Technology Stack

- **Python 3.12** - Core implementation language
- **Flask** - Web framework (presentation layer only)
- **SQLite** - Relational database
- **Pandas** - Data processing and analysis
- **HTML5/CSS3** - Structure and styling
- **Bootstrap 5** - Responsive design
- **JavaScript** - Client-side interactivity

## Getting Started

### Prerequisites

- Python 3.12 or higher
- pip (Python package manager)
- Web browser

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/InteracTrack.git
cd InteracTrack
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
cd DDIAgent.Web
python app.py
```

4. **Access the application**
```
http://localhost:5000
```

The SQLite database is automatically created and used locally - no additional database configuration required.

## Future Enhancements

### Short-term
- **Patient-Specific Factors**: Age, renal/liver function, genetics, comorbidities
- **Enhanced Explanations**: Why agent made specific decisions
- **Confidence Scoring**: Quantified certainty levels

### Medium-term
- **Multi-Agent Architecture**: Specialized agents for scanning, assessment, validation, notification
- **Explainable AI (XAI)**: Detailed reasoning behind decisions
- **Alternative Therapy Suggestions**: Safer drug combinations

### Long-term
- **External System Integration**: HL7/FHIR API, DrugBank API, SNOMED CT
- **Predictive Analytics**: Adverse reaction prediction, trend analysis
- **Real-time Monitoring Dashboard**: Live streams, geospatial risk visualization

## ⚠️ Important Disclaimers

1. **Medical Disclaimer**: This agent is for educational purposes only. It does NOT replace consultation with a physician or pharmacist. Always consult healthcare professionals.

2. **Confidence Thresholds**: When confidence is low, system recommends physician consultation rather than making uncertain predictions.

## License

This project was created for educational purposes as part of university coursework.

## 👤 Author

**Amila Tucović**
- Institution: Faculty of Information Technologies, University "Džemal Bijedić"
- GitHub: [@amilatucovic](https://github.com/amilatucovic)
---

⭐ **If you find this project helpful or interesting, please consider giving it a star!**
