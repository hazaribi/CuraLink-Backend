#!/usr/bin/env python3
"""
Seed script for specific researchers mentioned in requirements
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Specific researchers from requirements
specific_researchers = [
    # Parkinson's Disease Experts (Toronto)
    {
        "name": "Dr. Alfonso Fasano",
        "institution": "University Health Network",
        "specialties": ["Movement Disorders", "Neurology"],
        "research_interests": ["Deep Brain Stimulation", "Parkinson's Disease", "Movement Disorders"],
        "orcid": "0000-0002-1234-5001",
        "available_for_meetings": True
    },
    {
        "name": "Dr. Renato Munhoz", 
        "institution": "University of Toronto",
        "specialties": ["Movement Disorders", "Neurology"],
        "research_interests": ["Parkinson's Disease", "Deep Brain Stimulation", "Dystonia"],
        "available_for_meetings": True
    },
    {
        "name": "Dr. Anthony Lang",
        "institution": "Toronto Western Hospital", 
        "specialties": ["Movement Disorders", "Neurology"],
        "research_interests": ["Parkinson's Disease", "Neurodegeneration", "Stem Cell Therapy"],
        "available_for_meetings": True
    },
    {
        "name": "Dr. Mandar Jog",
        "institution": "Western University",
        "specialties": ["Movement Disorders", "Neurology"], 
        "research_interests": ["Parkinson's Disease", "Deep Brain Stimulation", "Gait Analysis"],
        "available_for_meetings": True
    },
    {
        "name": "Dr. Suneil Kalia",
        "institution": "University Health Network",
        "specialties": ["Movement Disorders", "Neurology"],
        "research_interests": ["Parkinson's Disease", "Neurodegeneration", "Stem Cell Therapy"],
        "available_for_meetings": True
    },
    {
        "name": "Dr. Andres Lozano",
        "institution": "University Health Network",
        "specialties": ["Neurosurgery"],
        "research_interests": ["Deep Brain Stimulation", "Parkinson's Disease", "Neurosurgery"],
        "available_for_meetings": True
    },
    
    # Breast Cancer Experts (Los Angeles)
    {
        "name": "Dr. Laura J. Esserman",
        "institution": "UCSF",
        "specialties": ["Breast Cancer", "Oncology"],
        "research_interests": ["Breast Cancer", "Ductal Carcinoma in Situ", "Precision Medicine"],
        "available_for_meetings": True
    },
    {
        "name": "Dr. Hope S. Rugo",
        "institution": "UCSF", 
        "specialties": ["Breast Cancer", "Oncology"],
        "research_interests": ["Breast Cancer", "Immunotherapy", "Clinical Trials"],
        "available_for_meetings": True
    },
    {
        "name": "Dr. Jo Chien",
        "institution": "Cedars-Sinai Medical Center",
        "specialties": ["Breast Cancer", "Research"],
        "research_interests": ["Breast Cancer", "Ductal Carcinoma in Situ", "Biomarkers"],
        "available_for_meetings": True
    },
    
    # ADHD Experts (Amsterdam)
    {
        "name": "Dr. Jan Buitelaar",
        "institution": "Radboud University",
        "specialties": ["Child Psychiatry", "ADHD"],
        "research_interests": ["ADHD", "Neurofeedback Training", "Developmental Disorders"],
        "available_for_meetings": True
    },
    {
        "name": "Dr. Sarah Durston",
        "institution": "University Medical Center Utrecht",
        "specialties": ["Neuroimaging", "ADHD"],
        "research_interests": ["ADHD", "Neuroimaging", "Brain Development"],
        "available_for_meetings": True
    },
    {
        "name": "Dr. Catharina Hartman",
        "institution": "University of Groningen", 
        "specialties": ["Child Psychiatry", "ADHD"],
        "research_interests": ["ADHD", "Neurofeedback Training", "Behavioral Interventions"],
        "available_for_meetings": True
    },
    {
        "name": "Dr. Anouk Schrantee",
        "institution": "Amsterdam UMC",
        "specialties": ["Neuroimaging", "ADHD"],
        "research_interests": ["ADHD", "Neuroimaging", "Methylphenidate Brain Connectivity"],
        "available_for_meetings": True
    },
    
    # Depression Experts (Amsterdam)
    {
        "name": "Dr. Guido van Wingen",
        "institution": "Amsterdam UMC",
        "specialties": ["Psychiatry", "Neuroimaging"],
        "research_interests": ["Depression", "Brain Stimulation", "Neuroimaging"],
        "available_for_meetings": True
    },
    {
        "name": "Dr. Brenda Penninx",
        "institution": "Vrije Universiteit Amsterdam",
        "specialties": ["Psychiatry", "Epidemiology"],
        "research_interests": ["Depression", "Long-term Outcomes", "Epidemiology"],
        "available_for_meetings": True
    }
]

def seed_specific_researchers():
    try:
        print("🌱 Seeding specific researchers...")
        result = supabase.table("researcher_profiles").insert(specific_researchers).execute()
        
        if result.data:
            print(f"✅ Successfully inserted {len(result.data)} specific researchers")
        else:
            print("❌ Failed to insert specific researchers")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    seed_specific_researchers()