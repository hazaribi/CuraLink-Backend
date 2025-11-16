#!/usr/bin/env python3
"""
Complete seed script - run this after creating tables in Supabase
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")

if not supabase_url or not supabase_key:
    print("❌ Missing SUPABASE_URL or SUPABASE_ANON_KEY in .env file")
    exit(1)

supabase: Client = create_client(supabase_url, supabase_key)

# All researchers from requirements
researchers = [
    # Parkinson's Disease Experts (Toronto)
    {"name": "Dr. Alfonso Fasano", "institution": "University Health Network", "specialties": ["Movement Disorders", "Neurology"], "research_interests": ["Deep Brain Stimulation", "Parkinson's Disease"], "available_for_meetings": True},
    {"name": "Dr. Renato Munhoz", "institution": "University of Toronto", "specialties": ["Movement Disorders", "Neurology"], "research_interests": ["Parkinson's Disease", "Deep Brain Stimulation"], "available_for_meetings": True},
    {"name": "Dr. Anthony Lang", "institution": "Toronto Western Hospital", "specialties": ["Movement Disorders", "Neurology"], "research_interests": ["Parkinson's Disease", "Stem Cell Therapy"], "available_for_meetings": True},
    {"name": "Dr. Mandar Jog", "institution": "Western University", "specialties": ["Movement Disorders", "Neurology"], "research_interests": ["Parkinson's Disease", "Deep Brain Stimulation"], "available_for_meetings": True},
    {"name": "Dr. Suneil Kalia", "institution": "University Health Network", "specialties": ["Movement Disorders", "Neurology"], "research_interests": ["Parkinson's Disease", "Stem Cell Therapy"], "available_for_meetings": True},
    {"name": "Dr. Andres Lozano", "institution": "University Health Network", "specialties": ["Neurosurgery"], "research_interests": ["Deep Brain Stimulation", "Parkinson's Disease"], "available_for_meetings": True},
    
    # Breast Cancer Experts (Los Angeles)
    {"name": "Dr. Laura J. Esserman", "institution": "UCSF", "specialties": ["Breast Cancer", "Oncology"], "research_interests": ["Breast Cancer", "Ductal Carcinoma in Situ"], "available_for_meetings": True},
    {"name": "Dr. Hope S. Rugo", "institution": "UCSF", "specialties": ["Breast Cancer", "Oncology"], "research_interests": ["Breast Cancer", "Immunotherapy"], "available_for_meetings": True},
    {"name": "Dr. Jo Chien", "institution": "Cedars-Sinai Medical Center", "specialties": ["Breast Cancer", "Research"], "research_interests": ["Breast Cancer", "Ductal Carcinoma in Situ"], "available_for_meetings": True},
    
    # ADHD Experts (Amsterdam)
    {"name": "Dr. Jan Buitelaar", "institution": "Radboud University", "specialties": ["Child Psychiatry", "ADHD"], "research_interests": ["ADHD", "Neurofeedback Training"], "available_for_meetings": True},
    {"name": "Dr. Sarah Durston", "institution": "University Medical Center Utrecht", "specialties": ["Neuroimaging", "ADHD"], "research_interests": ["ADHD", "Neuroimaging"], "available_for_meetings": True},
    {"name": "Dr. Catharina Hartman", "institution": "University of Groningen", "specialties": ["Child Psychiatry", "ADHD"], "research_interests": ["ADHD", "Neurofeedback Training"], "available_for_meetings": True},
    {"name": "Dr. Anouk Schrantee", "institution": "Amsterdam UMC", "specialties": ["Neuroimaging", "ADHD"], "research_interests": ["ADHD", "Methylphenidate Brain Connectivity"], "available_for_meetings": True},
    
    # Depression Experts (Amsterdam)
    {"name": "Dr. Guido van Wingen", "institution": "Amsterdam UMC", "specialties": ["Psychiatry", "Neuroimaging"], "research_interests": ["Depression", "Brain Stimulation"], "available_for_meetings": True},
    {"name": "Dr. Brenda Penninx", "institution": "Vrije Universiteit Amsterdam", "specialties": ["Psychiatry", "Epidemiology"], "research_interests": ["Depression", "Long-term Outcomes"], "available_for_meetings": True},
    {"name": "Dr. Claudi Bockting", "institution": "University of Amsterdam", "specialties": ["Clinical Psychology"], "research_interests": ["Depression", "Cognitive Therapy"], "available_for_meetings": True},
    {"name": "Dr. Jan Spijker", "institution": "Radboudumc", "specialties": ["Psychiatry"], "research_interests": ["Depression", "Treatment Resistance"], "available_for_meetings": True},
    
    # Collaborators
    {"name": "Dr. Carolina Gorodetsky", "institution": "Hospital for Sick Children", "specialties": ["Pediatric Neurology"], "research_interests": ["Pediatric Neurology", "Movement Disorders"], "available_for_meetings": True},
    {"name": "Dr. George Ibrahim", "institution": "Hospital for Sick Children", "specialties": ["Pediatric Neurosurgery"], "research_interests": ["Pediatric Neurology", "Epilepsy Surgery"], "available_for_meetings": True},
    {"name": "Dr. Amanda Paulovich", "institution": "Fred Hutchinson Cancer Center", "specialties": ["Proteomics"], "research_interests": ["Proteomics", "Recurrent Glioma"], "available_for_meetings": True},
    {"name": "Dr. Benjamin Cravatt III", "institution": "Scripps Research", "specialties": ["Chemical Biology"], "research_interests": ["Proteomics", "Drug Discovery"], "available_for_meetings": True}
]

# Clinical trials from requirements
trials = [
    {"title": "Multiple System Atrophy Natural History Study", "phase": "Phase II", "status": "Recruiting", "location": "Toronto, Canada", "description": "Longitudinal study tracking disease progression in multiple system atrophy patients."},
    {"title": "DCIS Vaccine Prevention Trial", "phase": "Phase II", "status": "Recruiting", "location": "Los Angeles, California", "description": "Testing preventive vaccine for ductal carcinoma in situ recurrence."},
    {"title": "Neurofeedback Training for ADHD in Amsterdam", "phase": "Phase III", "status": "Recruiting", "location": "Amsterdam, Netherlands", "description": "Comparing neurofeedback training to standard ADHD treatments."},
    {"title": "Freezing of Gait in Parkinson's Disease: Intervention Study", "phase": "Phase II", "status": "Recruiting", "location": "Toronto, Ontario, Canada", "description": "Testing novel interventions for freezing of gait episodes in PD."},
    {"title": "Bevacizumab Plus Radiotherapy for Recurrent Glioma", "phase": "Phase III", "status": "Recruiting", "location": "New York, NY, USA", "description": "Combination therapy with bevacizumab and radiation for recurrent glioblastoma."},
    {"title": "Psilocybin-Assisted Therapy for Treatment-Resistant Depression", "phase": "Phase II", "status": "Recruiting", "location": "Amsterdam, Netherlands", "description": "Safety and efficacy of psilocybin-assisted therapy for depression."}
]

def seed_all():
    try:
        print("🌱 Seeding researchers...")
        result = supabase.table("researcher_profiles").insert(researchers).execute()
        print(f"✅ Inserted {len(result.data)} researchers")
        
        print("🌱 Seeding clinical trials...")
        result = supabase.table("clinical_trials").insert(trials).execute()
        print(f"✅ Inserted {len(result.data)} trials")
        
        print("🎉 All data seeded successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    seed_all()