#!/usr/bin/env python3
"""
Seed script to populate Supabase with sample researcher data
Run this once to add test collaborators to your database
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for admin operations
supabase: Client = create_client(supabase_url, supabase_key)

# Sample researcher data
sample_researchers = [
    {
        "name": "Dr. Emily Rodriguez",
        "institution": "Stanford University",
        "specialties": ["Immunology", "Oncology"],
        "research_interests": ["Immunotherapy", "Clinical AI", "Biomarkers"],
        "orcid": "0000-0002-1234-5678",
        "available_for_meetings": True
    },
    {
        "name": "Dr. James Wilson",
        "institution": "Mayo Clinic",
        "specialties": ["Oncology", "Gene Therapy"],
        "research_interests": ["Gene Therapy", "Drug Discovery", "Clinical Trials"],
        "orcid": "0000-0002-2345-6789",
        "available_for_meetings": True
    },
    {
        "name": "Dr. Sarah Chen",
        "institution": "Johns Hopkins",
        "specialties": ["Neurology", "Precision Medicine"],
        "research_interests": ["Precision Medicine", "Diagnostics", "Clinical AI"],
        "orcid": "0000-0002-3456-7890",
        "available_for_meetings": True
    },
    {
        "name": "Dr. Michael Park",
        "institution": "Cleveland Clinic",
        "specialties": ["Cardiology"],
        "research_interests": ["Heart Disease", "AI Imaging", "Preventive Care"],
        "available_for_meetings": False
    },
    {
        "name": "Dr. Lisa Thompson",
        "institution": "Harvard Medical School",
        "specialties": ["Psychiatry", "Mental Health"],
        "research_interests": ["Depression", "Anxiety", "Digital Health"],
        "available_for_meetings": True
    },
    {
        "name": "Dr. David Kumar",
        "institution": "AIIMS Delhi",
        "specialties": ["Endocrinology", "Diabetes Research"],
        "research_interests": ["Diabetes", "Metabolic Disorders", "Global Health"],
        "available_for_meetings": True
    },
    {
        "name": "Dr. Maria Garcia",
        "institution": "University of Barcelona",
        "specialties": ["Infectious Diseases"],
        "research_interests": ["Vaccine Development", "Epidemiology", "Public Health"],
        "available_for_meetings": True
    },
    {
        "name": "Dr. Robert Johnson",
        "institution": "University of Oxford",
        "specialties": ["Genetics", "Rare Diseases"],
        "research_interests": ["Genomics", "Rare Disease Research", "Personalized Medicine"],
        "available_for_meetings": False
    }
]

def seed_researchers():
    """Insert sample researchers into the database"""
    try:
        print("🌱 Seeding researcher data...")
        
        # Check if data already exists
        existing = supabase.table("researcher_profiles").select("id").limit(1).execute()
        if existing.data:
            print("⚠️  Researcher data already exists. Skipping seed.")
            return
        
        # Insert sample data
        result = supabase.table("researcher_profiles").insert(sample_researchers).execute()
        
        if result.data:
            print(f"✅ Successfully inserted {len(result.data)} researchers")
            for researcher in result.data:
                print(f"   - {researcher['name']} ({researcher['institution']})")
        else:
            print("❌ Failed to insert researcher data")
            
    except Exception as e:
        print(f"❌ Error seeding data: {e}")

if __name__ == "__main__":
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in .env file")
        exit(1)
    
    seed_researchers()
    print("🎉 Seeding complete!")