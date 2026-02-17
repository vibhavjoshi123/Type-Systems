"""Curated sample adverse events for demo/testing.

Real-world drug interactions and adverse events based on known
pharmacological interactions. Used when FAERS bulk data isn't downloaded.

These demonstrate WHY hypergraphs matter for drug safety:
- Warfarin + Aspirin → GI Bleeding (two-drug interaction)
- Warfarin + Aspirin + Metformin → severe outcome (three-drug, can't be pairwise)
- SSRIs + Tramadol → Serotonin Syndrome (class interaction)
"""

from __future__ import annotations

SAMPLE_EVENTS: list[dict] = [
    # ── Anticoagulant interactions ─────────────────────────────────
    {
        "case_id": "AE-001",
        "drugs": [
            {"name": "WARFARIN", "role": "PS", "indication": "atrial-fibrillation"},
            {"name": "ASPIRIN", "role": "SS", "indication": "pain"},
        ],
        "reactions": ["GASTROINTESTINAL HAEMORRHAGE"],
        "outcomes": ["HO"],  # Hospitalization
    },
    {
        "case_id": "AE-002",
        "drugs": [
            {"name": "WARFARIN", "role": "PS", "indication": "atrial-fibrillation"},
            {"name": "ASPIRIN", "role": "SS", "indication": "cardiovascular-prevention"},
            {"name": "METFORMIN", "role": "C", "indication": "type-2-diabetes"},
        ],
        "reactions": ["GASTROINTESTINAL HAEMORRHAGE", "HYPOGLYCAEMIA"],
        "outcomes": ["HO", "OT"],  # Hospitalization + Other
    },
    {
        "case_id": "AE-003",
        "drugs": [
            {"name": "WARFARIN", "role": "PS", "indication": "dvt-prophylaxis"},
            {"name": "IBUPROFEN", "role": "SS", "indication": "pain"},
        ],
        "reactions": ["GASTROINTESTINAL HAEMORRHAGE", "INR INCREASED"],
        "outcomes": ["HO"],
    },
    {
        "case_id": "AE-004",
        "drugs": [
            {"name": "WARFARIN", "role": "PS", "indication": "atrial-fibrillation"},
            {"name": "AMIODARONE", "role": "C", "indication": "arrhythmia"},
        ],
        "reactions": ["INR INCREASED", "HAEMORRHAGE"],
        "outcomes": ["HO"],
    },
    # ── Serotonin syndrome ─────────────────────────────────────────
    {
        "case_id": "AE-005",
        "drugs": [
            {"name": "SERTRALINE", "role": "PS", "indication": "depression"},
            {"name": "TRAMADOL", "role": "SS", "indication": "pain"},
        ],
        "reactions": ["SEROTONIN SYNDROME"],
        "outcomes": ["HO"],
    },
    {
        "case_id": "AE-006",
        "drugs": [
            {"name": "FLUOXETINE", "role": "PS", "indication": "depression"},
            {"name": "TRAMADOL", "role": "SS", "indication": "pain"},
            {"name": "LITHIUM", "role": "C", "indication": "bipolar-disorder"},
        ],
        "reactions": ["SEROTONIN SYNDROME", "SEIZURE"],
        "outcomes": ["HO", "LT"],  # Hospitalization + Life-Threatening
    },
    {
        "case_id": "AE-007",
        "drugs": [
            {"name": "PAROXETINE", "role": "PS", "indication": "anxiety"},
            {"name": "SUMATRIPTAN", "role": "SS", "indication": "migraine"},
        ],
        "reactions": ["SEROTONIN SYNDROME"],
        "outcomes": ["HO"],
    },
    # ── QT prolongation ────────────────────────────────────────────
    {
        "case_id": "AE-008",
        "drugs": [
            {"name": "AZITHROMYCIN", "role": "PS", "indication": "infection"},
            {"name": "HYDROXYCHLOROQUINE", "role": "SS", "indication": "rheumatoid-arthritis"},
        ],
        "reactions": ["QT PROLONGATION", "CARDIAC ARREST"],
        "outcomes": ["DE"],  # Death
    },
    {
        "case_id": "AE-009",
        "drugs": [
            {"name": "METHADONE", "role": "PS", "indication": "opioid-dependence"},
            {"name": "CIPROFLOXACIN", "role": "C", "indication": "uti"},
        ],
        "reactions": ["QT PROLONGATION", "TORSADE DE POINTES"],
        "outcomes": ["HO", "LT"],
    },
    # ── Renal toxicity ─────────────────────────────────────────────
    {
        "case_id": "AE-010",
        "drugs": [
            {"name": "IBUPROFEN", "role": "PS", "indication": "pain"},
            {"name": "LISINOPRIL", "role": "C", "indication": "hypertension"},
            {"name": "FUROSEMIDE", "role": "C", "indication": "edema"},
        ],
        "reactions": ["RENAL FAILURE ACUTE", "HYPERKALAEMIA"],
        "outcomes": ["HO"],
    },
    {
        "case_id": "AE-011",
        "drugs": [
            {"name": "GENTAMICIN", "role": "PS", "indication": "infection"},
            {"name": "VANCOMYCIN", "role": "SS", "indication": "mrsa"},
        ],
        "reactions": ["RENAL FAILURE ACUTE", "OTOTOXICITY"],
        "outcomes": ["HO"],
    },
    # ── Hepatotoxicity ─────────────────────────────────────────────
    {
        "case_id": "AE-012",
        "drugs": [
            {"name": "ACETAMINOPHEN", "role": "PS", "indication": "pain"},
            {"name": "ISONIAZID", "role": "C", "indication": "tuberculosis"},
        ],
        "reactions": ["HEPATOTOXICITY", "LIVER FUNCTION TEST ABNORMAL"],
        "outcomes": ["HO"],
    },
    {
        "case_id": "AE-013",
        "drugs": [
            {"name": "METHOTREXATE", "role": "PS", "indication": "rheumatoid-arthritis"},
            {"name": "TRIMETHOPRIM", "role": "SS", "indication": "uti"},
        ],
        "reactions": ["PANCYTOPENIA", "HEPATOTOXICITY"],
        "outcomes": ["HO", "LT"],
    },
    # ── Hypoglycemia cascade ───────────────────────────────────────
    {
        "case_id": "AE-014",
        "drugs": [
            {"name": "GLIPIZIDE", "role": "PS", "indication": "type-2-diabetes"},
            {"name": "FLUCONAZOLE", "role": "SS", "indication": "fungal-infection"},
        ],
        "reactions": ["HYPOGLYCAEMIA", "LOSS OF CONSCIOUSNESS"],
        "outcomes": ["HO"],
    },
    {
        "case_id": "AE-015",
        "drugs": [
            {"name": "INSULIN", "role": "PS", "indication": "type-1-diabetes"},
            {"name": "METFORMIN", "role": "C", "indication": "type-2-diabetes"},
            {"name": "LISINOPRIL", "role": "C", "indication": "diabetic-nephropathy"},
        ],
        "reactions": ["HYPOGLYCAEMIA"],
        "outcomes": ["HO"],
    },
    # ── Immunosuppressant interactions ─────────────────────────────
    {
        "case_id": "AE-016",
        "drugs": [
            {"name": "CYCLOSPORINE", "role": "PS", "indication": "transplant-rejection"},
            {"name": "ITRACONAZOLE", "role": "SS", "indication": "fungal-infection"},
        ],
        "reactions": ["NEPHROTOXICITY", "CYCLOSPORINE LEVEL INCREASED"],
        "outcomes": ["HO"],
    },
    {
        "case_id": "AE-017",
        "drugs": [
            {"name": "TACROLIMUS", "role": "PS", "indication": "transplant-rejection"},
            {"name": "ERYTHROMYCIN", "role": "SS", "indication": "infection"},
            {"name": "METFORMIN", "role": "C", "indication": "type-2-diabetes"},
        ],
        "reactions": ["NEPHROTOXICITY", "TACROLIMUS LEVEL INCREASED"],
        "outcomes": ["HO"],
    },
    # ── Bleeding risk ──────────────────────────────────────────────
    {
        "case_id": "AE-018",
        "drugs": [
            {"name": "RIVAROXABAN", "role": "PS", "indication": "atrial-fibrillation"},
            {"name": "ASPIRIN", "role": "C", "indication": "cardiovascular-prevention"},
            {"name": "CLOPIDOGREL", "role": "C", "indication": "stent"},
        ],
        "reactions": ["CEREBRAL HAEMORRHAGE"],
        "outcomes": ["DE"],  # Death
    },
    {
        "case_id": "AE-019",
        "drugs": [
            {"name": "DABIGATRAN", "role": "PS", "indication": "atrial-fibrillation"},
            {"name": "KETOCONAZOLE", "role": "SS", "indication": "fungal-infection"},
        ],
        "reactions": ["GASTROINTESTINAL HAEMORRHAGE"],
        "outcomes": ["HO"],
    },
    # ── CNS depression ─────────────────────────────────────────────
    {
        "case_id": "AE-020",
        "drugs": [
            {"name": "OXYCODONE", "role": "PS", "indication": "pain"},
            {"name": "ALPRAZOLAM", "role": "SS", "indication": "anxiety"},
            {"name": "GABAPENTIN", "role": "C", "indication": "neuropathy"},
        ],
        "reactions": ["RESPIRATORY DEPRESSION", "SOMNOLENCE"],
        "outcomes": ["DE"],  # Death
    },
]

# Outcome code descriptions
OUTCOME_CODES = {
    "DE": "Death",
    "LT": "Life-Threatening",
    "HO": "Hospitalization",
    "DS": "Disability",
    "CA": "Congenital Anomaly",
    "RI": "Required Intervention",
    "OT": "Other Serious",
}

# Drug role codes
DRUG_ROLES = {
    "PS": "Primary Suspect",
    "SS": "Secondary Suspect",
    "C": "Concomitant",
    "I": "Interacting",
}
