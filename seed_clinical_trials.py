#!/usr/bin/env python3
"""
Seed script for specific clinical trials mentioned in requirements
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Specific trials from requirements
specific_trials = [
    {
        "title": "Multiple System Atrophy Natural History Study",
        "phase": "Phase II",
        "status": "Recruiting",
        "location": "Toronto, Canada",
        "description": "Longitudinal study tracking disease progression in multiple system atrophy patients."
    },
    {
        "title": "DCIS Vaccine Prevention Trial", 
        "phase": "Phase II",
        "status": "Recruiting",
        "location": "Los Angeles, California",
        "description": "Testing preventive vaccine for ductal carcinoma in situ recurrence."
    },
    {
        "title": "Neurofeedback Training for ADHD in Amsterdam",
        "phase": "Phase III", 
        "status": "Recruiting",
        "location": "Amsterdam, Netherlands",
        "description": "Comparing neurofeedback training to standard ADHD treatments."
    },
    {
        "title": "Freezing of Gait in Parkinson's Disease: Intervention Study",
        "phase": "Phase II",
        "status": "Recruiting", 
        "location": "Toronto, Ontario, Canada",
        "description": "Testing novel interventions for freezing of gait episodes in PD."
    },
    {
        "title": "Bevacizumab Plus Radiotherapy for Recurrent Glioma",
        "phase": "Phase III",
        "status": "Recruiting",
        "location": "New York, NY, USA", 
        "description": "Combination therapy with bevacizumab and radiation for recurrent glioblastoma."
    },
    {
        "title": "Psilocybin-Assisted Therapy for Treatment-Resistant Depression",
        "phase": "Phase II",
        "status": "Recruiting",
        "location": "Amsterdam, Netherlands",
        "description": "Safety and efficacy of psilocybin-assisted therapy for depression in Amsterdam medical centers."
    }
]

def seed_clinical_trials():
    try:
        print("🌱 Seeding specific clinical trials...")
        result = supabase.table("clinical_trials").insert(specific_trials).execute()
        
        if result.data:
            print(f"✅ Successfully inserted {len(result.data)} clinical trials")
        else:
            print("❌ Failed to insert clinical trials")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    seed_clinical_trials()