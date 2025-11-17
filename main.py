from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import httpx
import json
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from supabase import create_client, Client
from external_search import ExternalExpertSearch
from admin_requests import AdminRequestHandler
from orcid_service import ORCIDService
from ai_service import ai_service
from utils import sanitize_input, validate_email, validate_orcid

app = FastAPI(title="CuraLink API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Set to False when using allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

# Pydantic models
class PatientProfile(BaseModel):
    condition: str
    location: str
    additional_conditions: Optional[List[str]] = []

class ResearcherProfile(BaseModel):
    name: str
    institution: str
    specialties: List[str]
    research_interests: List[str]
    orcid: Optional[str] = None
    research_gate: Optional[str] = None
    available_for_meetings: bool = False

class ClinicalTrial(BaseModel):
    title: str
    phase: str
    status: str
    location: str
    description: Optional[str] = None
    eligibility_criteria: Optional[str] = None

class Publication(BaseModel):
    title: str
    journal: str
    authors: List[str]
    date: str
    doi: Optional[str] = None
    abstract: Optional[str] = None

class MeetingRequest(BaseModel):
    patient_name: str
    email: str
    phone: Optional[str] = None
    preferred_date: Optional[str] = None
    preferred_time: Optional[str] = None
    meeting_type: str = 'video'
    message: Optional[str] = None
    urgency: str = 'normal'
    researcher_id: str

class ORCIDSyncRequest(BaseModel):
    orcid_id: str

class AIAnalysisRequest(BaseModel):
    text: str
    analysis_type: str  # 'condition', 'trial_summary', 'collaboration'

class ConnectionRequest(BaseModel):
    from_researcher_id: str
    to_researcher_id: str
    message: str

class ChatMessage(BaseModel):
    connection_id: int
    sender_id: str
    message: str

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.user_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: int, user_id: str):
        await websocket.accept()
        if connection_id not in self.active_connections:
            self.active_connections[connection_id] = []
        self.active_connections[connection_id].append(websocket)
        self.user_connections[user_id] = websocket
    
    def disconnect(self, websocket: WebSocket, connection_id: int, user_id: str):
        if connection_id in self.active_connections:
            self.active_connections[connection_id].remove(websocket)
        if user_id in self.user_connections:
            del self.user_connections[user_id]
    
    async def send_message(self, message: str, connection_id: int):
        if connection_id in self.active_connections:
            for connection in self.active_connections[connection_id]:
                await connection.send_text(message)
    
    async def send_notification(self, user_id: str, notification: dict):
        if user_id in self.user_connections:
            await self.user_connections[user_id].send_text(json.dumps(notification))

manager = ConnectionManager()

# Global storage for admin requests when Supabase is not available
global_admin_requests = []

# Routes
@app.get("/")
async def root():
    return {"message": "CuraLink API is running"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/admin/test")
async def test_admin():
    return {"test": "working", "requests": [{"id": "test1", "type": "test", "status": "pending"}]}

@app.post("/api/patients/profile")
async def create_patient_profile(profile: PatientProfile):
    """Create or update patient profile"""
    try:
        # Sanitize inputs
        profile.condition = sanitize_input(profile.condition)
        profile.location = sanitize_input(profile.location)
        
        if supabase:
            result = supabase.table("patient_profiles").insert(profile.dict()).execute()
            return {"message": "Profile created successfully", "data": result.data}
        return {"message": "Profile saved locally", "data": profile.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create profile")

@app.post("/api/researchers/profile")
async def create_researcher_profile(profile: ResearcherProfile):
    """Create or update researcher profile"""
    try:
        if supabase:
            result = supabase.table("researcher_profiles").insert(profile.dict()).execute()
            return {"message": "Profile created successfully", "data": result.data}
        return {"message": "Profile saved locally", "data": profile.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clinical-trials")
async def get_clinical_trials(condition: Optional[str] = None, location: Optional[str] = None):
    """Get clinical trials from ClinicalTrials.gov API and database"""
    trials = []
    
    # First, get trials from Supabase database
    if supabase:
        try:
            query = supabase.table("clinical_trials").select("*")
            
            if condition:
                # Enhanced search for clinical trials
                condition_lower = condition.lower()
                result = query.execute()
                filtered_trials = []
                
                for trial in result.data:
                    title_lower = trial.get("title", "").lower()
                    desc_lower = trial.get("description", "").lower()
                    
                    # Direct match
                    direct_match = condition_lower in title_lower or condition_lower in desc_lower
                    
                    # Related term matching
                    related_match = False
                    if any(term in condition_lower for term in ["ductal", "carcinoma", "dcis", "breast"]):
                        # Breast cancer related search
                        related_match = any(term in title_lower or term in desc_lower for term in ["dcis", "ductal", "breast", "vaccine"])
                    elif any(term in condition_lower for term in ["parkinson", "movement", "deep brain"]):
                        # Parkinson's related search  
                        related_match = any(term in title_lower or term in desc_lower for term in ["parkinson", "movement", "gait", "freezing"])
                    elif any(term in condition_lower for term in ["neurofeedback", "adhd", "methylphenidate", "medication response"]):
                        # ADHD related search
                        related_match = any(term in title_lower or term in desc_lower for term in ["adhd", "neurofeedback", "amsterdam", "medication response"])
                    elif any(term in condition_lower for term in ["brain stimulation", "depression", "ketamine", "psilocybin", "depressive", "tms", "deep brain"]):
                        # Depression related search
                        related_match = any(term in title_lower or term in desc_lower for term in ["depression", "psilocybin", "therapy", "amsterdam", "ketamine", "tms", "deep brain stimulation", "treatment-resistant"])
                    elif any(term in condition_lower for term in ["bevacizumab", "glioma", "radiotherapy", "proteomics", "recurrent"]):
                        # Glioma related search
                        related_match = any(term in title_lower or term in desc_lower for term in ["bevacizumab", "glioma", "radiotherapy", "recurrent", "proteomics"])
                    elif any(term in condition_lower for term in ["dopamine", "modulation", "amsterdam"]):
                        # Enhanced ADHD dopamine search
                        related_match = any(term in title_lower or term in desc_lower for term in ["dopamine", "modulation", "adhd", "amsterdam"])
                    elif any(term in condition_lower for term in ["long-term", "outcomes", "treatment"]):
                        # Long-term outcomes search
                        related_match = any(term in title_lower or term in desc_lower for term in ["long-term", "outcomes", "treatment", "depression"])
                    
                    if direct_match or related_match:
                        filtered_trials.append(trial)
                        
                result.data = filtered_trials
            else:
                result = query.execute()
            
            # Convert to expected format
            for trial in result.data:
                trials.append({
                    "id": trial.get("id"),
                    "title": trial.get("title"),
                    "phase": trial.get("phase"),
                    "status": trial.get("status"),
                    "location": trial.get("location"),
                    "description": trial.get("description")
                })
        except Exception as e:
            print(f"Database query failed: {e}")
    
    # Then try ClinicalTrials.gov API for additional results
    try:
        if condition and len(trials) < 5:
            # Clean the condition search term - remove extra words that might confuse the API
            clean_condition = condition.split()[0] if condition else condition
            
            ct_url = "https://clinicaltrials.gov/api/query/study_fields"
            params = {
                "expr": clean_condition,
                "fields": "NCTId,BriefTitle,Phase,OverallStatus,LocationCountry,BriefSummary",
                "min_rnk": "1",
                "max_rnk": "5",
                "fmt": "json"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(ct_url, params=params)
                data = response.json()
                
                if "StudyFieldsResponse" in data and "StudyFields" in data["StudyFieldsResponse"]:
                    existing_ids = {t["id"] for t in trials}
                    
                    for i, study in enumerate(data["StudyFieldsResponse"]["StudyFields"][:3]):
                        trial_id = 1000 + i  # Use high IDs for external trials
                        if trial_id not in existing_ids:
                            title = study.get("BriefTitle", [""])[0] if study.get("BriefTitle") else f"Clinical Trial for {condition}"
                            # Avoid duplicate/similar titles
                            if not any(title.lower() in t["title"].lower() for t in trials):
                                trials.append({
                                    "id": trial_id,
                                    "title": title,
                                    "phase": study.get("Phase", [""])[0] if study.get("Phase") else "Phase Unknown",
                                    "status": study.get("OverallStatus", [""])[0] if study.get("OverallStatus") else "Status Unknown",
                                    "location": study.get("LocationCountry", [""])[0] if study.get("LocationCountry") else "Multiple Locations",
                                    "description": study.get("BriefSummary", [""])[0][:200] + "..." if study.get("BriefSummary") and study.get("BriefSummary")[0] else f"Clinical trial studying {condition}"
                                })
    except Exception as e:
        print(f"ClinicalTrials.gov API failed: {e}")
    
    # If no trials found, return relevant fallback
    if not trials and condition:
        trials = [{
            "id": 1,
            "title": f"Clinical Trial for {condition}",
            "phase": "Phase II",
            "status": "Recruiting",
            "location": "Multiple Locations",
            "description": f"Clinical trial studying treatments for {condition}."
        }]
    
    return {"trials": trials}

@app.get("/api/health-experts")
async def get_health_experts(specialty: Optional[str] = None, location: Optional[str] = None, include_external: bool = False):
    """Get health experts based on specialty and location"""
    experts = []
    
    # First, get experts from Supabase database
    if supabase:
        try:
            query = supabase.table("researcher_profiles").select("*")
            
            # Apply filters if provided
            if specialty:
                # Enhanced search logic for better matching
                specialty_lower = specialty.lower()
                result = query.execute()
                filtered_experts = []
                
                # Define related terms for better matching
                breast_cancer_terms = ["breast cancer", "breast", "oncology", "ductal carcinoma", "dcis"]
                parkinsons_terms = ["parkinson", "movement disorders", "neurology", "deep brain stimulation", "dbs"]
                adhd_terms = ["adhd", "neurofeedback", "child psychiatry", "neuroimaging", "methylphenidate", "attention-deficit"]
                depression_terms = ["depression", "psychiatry", "brain stimulation", "ketamine", "deep brain stimulation"]
                
                for expert in result.data:
                    # Check direct matches first
                    direct_match = (
                        any(specialty_lower in s.lower() for s in expert.get("specialties", [])) or
                        any(specialty_lower in r.lower() for r in expert.get("research_interests", [])) or
                        specialty_lower in expert.get("name", "").lower() or
                        specialty_lower in expert.get("institution", "").lower()
                    )
                    
                    # Check for related terms
                    related_match = False
                    if any(term in specialty_lower for term in ["ductal", "carcinoma", "breast"]):
                        # This is breast cancer related search
                        related_match = any(
                            any(term in s.lower() for term in breast_cancer_terms) for s in expert.get("specialties", [])
                        ) or any(
                            any(term in r.lower() for term in breast_cancer_terms) for r in expert.get("research_interests", [])
                        )
                    elif any(term in specialty_lower for term in ["deep brain", "stimulation", "parkinson"]):
                        # This is Parkinson's related search
                        related_match = any(
                            any(term in s.lower() for term in parkinsons_terms) for s in expert.get("specialties", [])
                        ) or any(
                            any(term in r.lower() for term in parkinsons_terms) for r in expert.get("research_interests", [])
                        )
                    elif any(term in specialty_lower for term in ["neurofeedback", "adhd", "methylphenidate", "neuroimaging", "netherlands"]):
                        # This is ADHD related search
                        related_match = any(
                            any(term in s.lower() for term in adhd_terms) for s in expert.get("specialties", [])
                        ) or any(
                            any(term in r.lower() for term in adhd_terms) for r in expert.get("research_interests", [])
                        ) or "netherlands" in expert.get("institution", "").lower()
                    elif any(term in specialty_lower for term in ["brain stimulation", "depression", "ketamine", "neuroimaging", "netherlands", "depressive", "psilocybin", "amsterdam"]):
                        # This is depression related search
                        related_match = any(
                            any(term in s.lower() for term in depression_terms) for s in expert.get("specialties", [])
                        ) or any(
                            any(term in r.lower() for term in depression_terms) for r in expert.get("research_interests", [])
                        ) or "netherlands" in expert.get("institution", "").lower() or "amsterdam" in expert.get("institution", "").lower()
                    
                    if direct_match or related_match:
                        filtered_experts.append(expert)
                        
                result.data = filtered_experts
            else:
                result = query.execute()
            
            # Convert to expected format
            for expert in result.data:
                institution = expert.get("institution", "")
                # Extract location from institution if it contains location info
                if ", " in institution:
                    parts = institution.split(", ")
                    location = ", ".join(parts[1:])  # Everything after first comma
                    institution_name = parts[0]  # Just the institution name
                else:
                    location = "Various Locations"
                    institution_name = institution
                
                experts.append({
                    "id": expert.get("id"),
                    "name": expert.get("name"),
                    "specialty": expert.get("specialties", [])[0] if expert.get("specialties") else "General",
                    "institution": institution_name,
                    "location": location,
                    "available_for_meetings": expert.get("available_for_meetings", True),
                    "research_interests": expert.get("research_interests", []),
                    "profile_type": "registered",
                    "contact_available": expert.get("available_for_meetings", True),
                    "needs_admin_review": False,
                    "data_source": "CuraLink Profile"
                })
        except Exception as e:
            print(f"Database query failed: {e}")
    
    # Add external search if requested
    if include_external and specialty:
        external_search = ExternalExpertSearch()
        try:
            pubmed_experts = await external_search.search_pubmed_authors(specialty, limit=3)
            orcid_experts = await external_search.search_orcid_researchers(specialty, limit=2)
            
            # Add unique IDs and profile visibility flags for external experts
            for i, expert in enumerate(pubmed_experts):
                expert["id"] = 1000 + i
                expert["profile_type"] = "external_pubmed"
                expert["contact_available"] = False
                expert["needs_admin_review"] = True
                expert["data_source"] = "PubMed"
                
            for i, expert in enumerate(orcid_experts):
                expert["id"] = 2000 + i
                expert["profile_type"] = "external_orcid"
                expert["contact_available"] = False
                expert["needs_admin_review"] = True
                expert["data_source"] = "ORCID"
            
            experts.extend(pubmed_experts)
            experts.extend(orcid_experts)
        except Exception as e:
            print(f"External search failed: {e}")
    
    return {"experts": experts}

@app.get("/api/publications")
async def get_publications(keyword: Optional[str] = None, journal: Optional[str] = None):
    """Get publications from PubMed API"""
    try:
        if keyword:
            # PubMed API integration
            pubmed_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            search_params = {
                "db": "pubmed",
                "term": keyword,
                "retmax": "10",
                "retmode": "json"
            }
            
            async with httpx.AsyncClient() as client:
                search_response = await client.get(pubmed_url, params=search_params)
                search_data = search_response.json()
                
                if "esearchresult" in search_data and "idlist" in search_data["esearchresult"]:
                    pmids = search_data["esearchresult"]["idlist"][:5]  # Limit to 5 results
                    
                    if pmids:
                        # Fetch details for each PMID
                        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                        fetch_params = {
                            "db": "pubmed",
                            "id": ",".join(pmids),
                            "retmode": "xml"
                        }
                        
                        details_response = await client.get(fetch_url, params=fetch_params)
                        
                        # Parse XML and extract publication data
                        import xml.etree.ElementTree as ET
                        import html
                        publications = []
                        
                        try:
                            parser = ET.XMLParser(resolve_entities=False)
                            root = ET.fromstring(details_response.text, parser)
                            articles = root.findall(".//PubmedArticle")
                            
                            seen_titles = set()  # Track titles to avoid duplicates
                            
                            for i, article in enumerate(articles[:5]):
                                pmid = pmids[i] if i < len(pmids) else str(i+1)
                                
                                # Extract title
                                title_elem = article.find(".//ArticleTitle")
                                title = html.unescape(title_elem.text) if title_elem is not None else f"{keyword} Research Study"
                                
                                # Skip duplicates
                                title_lower = title.lower()
                                if title_lower in seen_titles:
                                    continue
                                seen_titles.add(title_lower)
                                
                                # Extract journal name
                                journal_elem = article.find(".//Journal/Title")
                                if journal_elem is None:
                                    journal_elem = article.find(".//Journal/ISOAbbreviation")
                                journal = html.unescape(journal_elem.text) if journal_elem is not None else "Medical Journal"
                                
                                # Extract authors
                                authors = []
                                author_list = article.findall(".//Author")
                                for author in author_list[:3]:  # Limit to 3 authors
                                    lastname = author.find("LastName")
                                    forename = author.find("ForeName")
                                    if lastname is not None and forename is not None:
                                        authors.append(f"{forename.text} {lastname.text}")
                                    elif lastname is not None:
                                        authors.append(lastname.text)
                                
                                if not authors:
                                    # Try collective name
                                    collective = article.find(".//CollectiveName")
                                    if collective is not None:
                                        authors = [collective.text]
                                    else:
                                        authors = ["Authors not listed"]
                                
                                # Extract publication date
                                date_elem = article.find(".//PubDate/Year")
                                date = f"{date_elem.text}-01-01" if date_elem is not None else "2024-01-01"
                                
                                # Extract abstract
                                abstract_elem = article.find(".//Abstract/AbstractText")
                                abstract = abstract_elem.text[:300] + "..." if abstract_elem is not None and abstract_elem.text else f"Research study on {keyword}."
                                
                                publications.append({
                                    "id": int(pmid),
                                    "title": title,
                                    "journal": journal,
                                    "authors": authors,
                                    "date": date,
                                    "pmid": pmid,
                                    "abstract": abstract
                                })
                        except Exception as parse_error:
                            # Fallback if XML parsing fails
                            for i, pmid in enumerate(pmids[:5]):
                                publications.append({
                                    "id": int(pmid),
                                    "title": f"{keyword} Research Study",
                                    "journal": "Medical Research Journal",
                                    "authors": ["Research Team"],
                                    "date": "2024-01-01",
                                    "pmid": pmid,
                                    "abstract": f"Research article about {keyword}."
                                })
                        
                        return {"publications": publications}
        
        # Fallback to mock data
        mock_publications = [
            {
                "id": 1,
                "title": "Recent Advances in Brain Cancer Treatment",
                "journal": "Nature Medicine",
                "authors": ["Dr. Sarah Johnson", "Dr. Michael Chen"],
                "date": "2024-01-15",
                "doi": "10.1038/nm.2024.001",
                "abstract": "This study presents recent advances in brain cancer treatment..."
            },
            {
                "id": 2,
                "title": "Immunotherapy Breakthrough in Oncology",
                "journal": "NEJM",
                "authors": ["Dr. Emily Rodriguez", "Dr. James Wilson"],
                "date": "2024-01-10",
                "doi": "10.1056/nejm.2024.001",
                "abstract": "A breakthrough study on immunotherapy applications..."
            }
        ]
        
        if keyword:
            mock_publications = [p for p in mock_publications if keyword.lower() in p["title"].lower()]
        
        return {"publications": mock_publications}
        
    except Exception as e:
        # Return mock data on error
        return {"publications": [
            {
                "id": 1,
                "title": f"Research on {keyword or 'Medical Topics'}",
                "journal": "Medical Journal",
                "authors": ["Research Team"],
                "date": "2024-01-01",
                "doi": "10.1000/example.001",
                "abstract": "Medical research article from external database."
            }
        ]}

@app.get("/api/collaborators")
async def get_collaborators(specialty: Optional[str] = None, research_interest: Optional[str] = None, location: Optional[str] = None):
    """Get potential collaborators for researchers"""
    collaborators = []
    
    # First, get collaborators from Supabase database
    if supabase:
        try:
            query = supabase.table("researcher_profiles").select("*")
            
            # Apply filters if provided
            if specialty:
                # Enhanced search logic for collaborators
                specialty_lower = specialty.lower()
                result = query.execute()
                filtered_collaborators = []
                
                for researcher in result.data:
                    # Check direct matches first
                    direct_match = (
                        any(specialty_lower in s.lower() for s in researcher.get("specialties", [])) or
                        any(specialty_lower in r.lower() for r in researcher.get("research_interests", [])) or
                        specialty_lower in researcher.get("name", "").lower() or
                        specialty_lower in researcher.get("institution", "").lower()
                    )
                    
                    # Check for related terms
                    related_match = False
                    if any(term in specialty_lower for term in ["pediatric neurology", "movement disorders"]):
                        # This is pediatric neurology related search
                        related_match = any(
                            any(term in s.lower() for term in ["pediatric neurology", "pediatric neurosurgery", "movement disorders"]) for s in researcher.get("specialties", [])
                        ) or any(
                            any(term in r.lower() for term in ["pediatric neurology", "movement disorders", "epilepsy"]) for r in researcher.get("research_interests", [])
                        )
                    elif any(term in specialty_lower for term in ["proteomics", "recurrent glioma", "glioma"]):
                        # This is proteomics/glioma related search
                        related_match = any(
                            any(term in s.lower() for term in ["proteomics", "cancer research", "chemical biology"]) for s in researcher.get("specialties", [])
                        ) or any(
                            any(term in r.lower() for term in ["proteomics", "recurrent glioma", "drug discovery"]) for r in researcher.get("research_interests", [])
                        )
                    elif any(term in specialty_lower for term in ["neuroimaging", "depression", "netherlands", "amsterdam", "psilocybin", "ketamine", "brain stimulation"]):
                        # This is depression/neuroimaging related search
                        related_match = any(
                            any(term in s.lower() for term in ["psychiatry", "neuroimaging", "clinical psychology"]) for s in researcher.get("specialties", [])
                        ) or any(
                            any(term in r.lower() for term in ["depression", "brain stimulation", "cognitive therapy", "long-term outcomes"]) for r in researcher.get("research_interests", [])
                        ) or "netherlands" in researcher.get("institution", "").lower() or "amsterdam" in researcher.get("institution", "").lower()
                    
                    if direct_match or related_match:
                        filtered_collaborators.append(researcher)
                        
                result.data = filtered_collaborators
            else:
                result = query.execute()
            
            # Convert to expected format
            for researcher in result.data:
                institution = researcher.get("institution", "")
                # Extract location from institution if it contains location info
                if ", " in institution:
                    parts = institution.split(", ")
                    location_part = ", ".join(parts[1:])  # Everything after first comma
                    institution_name = parts[0]  # Just the institution name
                else:
                    location_part = "Various Locations"
                    institution_name = institution
                
                collaborators.append({
                    "id": researcher.get("id"),
                    "name": researcher.get("name"),
                    "specialty": researcher.get("specialties", [])[0] if researcher.get("specialties") else "General",
                    "institution": institution_name,
                    "location": location_part,
                    "researchInterests": researcher.get("research_interests", []),
                    "publications": 25 + (researcher.get("id", 0) * 3),  # Mock publication count
                    "available_for_collaboration": researcher.get("available_for_meetings", True),
                    "collaborationStatus": "selective"
                })
        except Exception as e:
            print(f"Database query failed: {e}")
    
    return {"collaborators": collaborators}


@app.post("/api/meeting-requests")
async def create_meeting_request(request: MeetingRequest):
    """Create a new meeting request"""
    try:
        # Check if researcher is registered on platform
        researcher_registered = False
        is_external = request.researcher_id.startswith(('1000', '2000'))  # External expert IDs
        
        print(f"Meeting request for researcher_id: {request.researcher_id}, is_external: {is_external}")
        
        if not is_external:
            # Check if researcher exists in our database
            if supabase:
                result = supabase.table("researcher_profiles").select("id").eq("id", request.researcher_id).execute()
                researcher_registered = len(result.data) > 0
            else:
                # For demo purposes, assume researchers with IDs 1-8 are registered
                researcher_registered = request.researcher_id in ['1', '2', '3', '4', '5', '6', '7', '8']
        
        print(f"Researcher registered: {researcher_registered}")
        
        # If researcher not registered or is external, route to admin
        if is_external or not researcher_registered:
            import datetime
            admin_request = {
                "type": "external_expert_contact",
                "patient_name": request.patient_name,
                "patient_email": request.email,
                "phone": request.phone,
                "preferred_date": request.preferred_date,
                "preferred_time": request.preferred_time,
                "meeting_type": request.meeting_type,
                "expert_name": f"Expert ID: {request.researcher_id}",
                "expert_id": request.researcher_id,
                "message": request.message or "Patient requesting meeting",
                "urgency": request.urgency,
                "status": "pending_admin_review"
            }
            
            print(f"Admin request created: {admin_request}")
            
            if supabase:
                try:
                    result = supabase.table("admin_requests").insert(admin_request).execute()
                    print(f"Supabase insert result: {result}")
                    return {
                        "message": "Request forwarded to admin - researcher not on platform", 
                        "type": "admin_request", 
                        "data": result.data[0] if result.data else admin_request
                    }
                except Exception as e:
                    print(f"Supabase insert failed: {e}")
            
            # Store in global list when Supabase is not available
            admin_request["id"] = f"req_{len(global_admin_requests) + 1}_{request.researcher_id}"
            admin_request["created_at"] = datetime.datetime.now().isoformat()
            global_admin_requests.append(admin_request)
            print(f"Added to global requests. Total: {len(global_admin_requests)}")
            
            return {
                "message": "Request forwarded to admin - researcher not on platform", 
                "type": "admin_request", 
                "data": admin_request
            }
        
        # Both parties on platform - direct meeting request
        if supabase:
            result = supabase.table("meeting_requests").insert({
                "patient_name": request.patient_name,
                "patient_contact": request.email,
                "phone": request.phone,
                "preferred_date": request.preferred_date,
                "preferred_time": request.preferred_time,
                "meeting_type": request.meeting_type,
                "message": request.message,
                "urgency": request.urgency,
                "researcher_id": request.researcher_id,
                "status": "pending"
            }).execute()
            
            # Send real-time notification
            notification = {
                "type": "meeting_request",
                "title": "New Meeting Request",
                "message": f"Meeting request from {request.patient_name}"
            }
            await manager.send_notification(request.researcher_id, notification)
            
            return {
                "message": "Meeting request sent directly to researcher", 
                "type": "direct_request", 
                "data": result.data
            }
        
        return {"message": "Meeting request saved locally", "data": request.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/meeting-requests/{researcher_id}")
async def get_meeting_requests(researcher_id: str):
    """Get meeting requests for a researcher"""
    try:
        if supabase:
            result = supabase.table("meeting_requests").select("*").eq("researcher_id", researcher_id).order("created_at", desc=True).execute()
            
            if result.data:
                requests = []
                for req in result.data:
                    requests.append({
                        "id": req.get("id"),
                        "patient_name": req.get("patient_name"),
                        "email": req.get("patient_contact"),
                        "phone": req.get("phone"),
                        "preferred_date": req.get("preferred_date"),
                        "preferred_time": req.get("preferred_time"),
                        "meeting_type": req.get("meeting_type", "video"),
                        "message": req.get("message"),
                        "urgency": req.get("urgency", "normal"),
                        "status": req.get("status", "pending"),
                        "requested_at": req.get("created_at")
                    })
                return {"requests": requests}
        
        # Fallback mock data
        mock_requests = [
            {
                "id": 1,
                "patient_name": "John Doe",
                "email": "john@example.com",
                "phone": "+1-555-0123",
                "preferred_date": "2024-02-15",
                "preferred_time": "morning",
                "meeting_type": "video",
                "message": "I would like to discuss treatment options for my condition.",
                "urgency": "normal",
                "status": "pending",
                "requested_at": "2024-01-15T10:00:00Z"
            }
        ]
        return {"requests": mock_requests}
        
    except Exception as e:
        print(f"Error fetching meeting requests: {e}")
        return {"requests": []}

@app.put("/api/meeting-requests/{request_id}")
async def update_meeting_request(request_id: int, status: str):
    """Update meeting request status"""
    try:
        if supabase:
            result = supabase.table("meeting_requests").update({
                "status": status,
                "responded_at": "now()"
            }).eq("id", request_id).execute()
            return {"message": "Request updated", "data": result.data}
        return {"message": "Request updated locally"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/flag-missing-contact")
async def flag_missing_contact(expert_data: dict):
    """Flag external expert for missing contact info"""
    try:
        admin_handler = AdminRequestHandler()
        flag_request = {
            "type": "missing_contact_info",
            "expert_name": expert_data.get("name"),
            "expert_id": expert_data.get("id"),
            "data_source": expert_data.get("data_source", "External"),
            "specialty": expert_data.get("specialty"),
            "institution": expert_data.get("institution"),
            "status": "pending_admin_review",
            "priority": "normal"
        }
        
        if supabase:
            result = supabase.table("admin_requests").insert(flag_request).execute()
        
        return {"message": "Expert flagged for missing contact info", "data": flag_request}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/nudge-expert")
async def nudge_expert_to_join(expert_data: dict):
    """Send nudge invitation to external expert"""
    try:
        admin_handler = AdminRequestHandler()
        invitation = admin_handler.create_nudge_invitation(expert_data)
        
        # In production, this would send actual emails
        # For now, just log the invitation
        print(f"Nudge invitation created for {expert_data.get('name')}")
        
        return {"message": "Nudge invitation sent", "invitation": invitation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/requests")
async def get_admin_requests():
    """Get all admin requests for review"""
    try:
        if supabase:
            result = supabase.table("admin_requests").select("*").order("created_at", desc=True).execute()
            return {"requests": result.data}
        else:
            # Return global storage when Supabase not available
            return {"requests": global_admin_requests}
    except Exception as e:
        print(f"Error fetching admin requests: {e}")
        return {"requests": global_admin_requests}

@app.put("/api/admin/requests/{request_id}")
async def update_admin_request_status(request_id: str, status_data: dict):
    """Update admin request status"""
    try:
        new_status = status_data.get("status")
        if supabase:
            result = supabase.table("admin_requests").update({
                "status": new_status,
                "updated_at": "now()"
            }).eq("id", request_id).execute()
            return {"message": "Request status updated", "data": result.data}
        else:
            # Update in global storage
            for request in global_admin_requests:
                if request["id"] == request_id:
                    request["status"] = new_status
                    break
            return {"message": "Request status updated locally"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/connections/request")
async def send_connection_request(request: ConnectionRequest):
    """Send a connection request to another researcher"""
    try:
        if supabase:
            result = supabase.table("connection_requests").insert({
                "from_researcher_id": request.from_researcher_id,
                "to_researcher_id": request.to_researcher_id,
                "message": request.message,
                "status": "pending"
            }).execute()
            return {"message": "Connection request sent", "data": result.data}
        return {"message": "Connection request sent locally", "data": request.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/connections/requests/{researcher_id}")
async def get_connection_requests(researcher_id: str):
    """Get connection requests for a researcher"""
    mock_requests = [
        {
            "id": 1,
            "from_researcher": {
                "id": "researcher_2",
                "name": "Dr. Sarah Chen",
                "specialty": "Neurology",
                "institution": "Johns Hopkins"
            },
            "message": "Interested in collaborating on precision medicine research",
            "status": "pending",
            "created_at": "2024-01-15T10:00:00Z"
        }
    ]
    return {"requests": mock_requests}

@app.put("/api/connections/requests/{request_id}")
async def respond_to_connection_request(request_id: int, action: str):
    """Accept or decline a connection request"""
    try:
        if supabase:
            result = supabase.table("connection_requests").update({
                "status": "accepted" if action == "accept" else "declined"
            }).eq("id", request_id).execute()
            
            if action == "accept":
                # Create connection record
                connection_result = supabase.table("connections").insert({
                    "researcher1_id": "current_researcher",
                    "researcher2_id": "other_researcher",
                    "status": "active"
                }).execute()
            
            return {"message": f"Connection request {action}ed", "data": result.data}
        return {"message": f"Connection request {action}ed locally"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/connections/{researcher_id}")
async def get_connections(researcher_id: str):
    """Get active connections for a researcher"""
    mock_connections = [
        {
            "id": 1,
            "researcher": {
                "id": "researcher_2",
                "name": "Dr. Emily Rodriguez",
                "specialty": "Immunology",
                "institution": "Stanford University"
            },
            "status": "online",
            "last_message": "Hi! I saw your work on immunotherapy.",
            "last_message_time": "2024-01-15T10:30:00Z"
        }
    ]
    return {"connections": mock_connections}

@app.post("/api/chat/messages")
async def send_chat_message(message: ChatMessage):
    """Send a chat message"""
    try:
        if supabase:
            result = supabase.table("chat_messages").insert({
                "connection_id": message.connection_id,
                "sender_id": message.sender_id,
                "message": message.message,
                "sent_at": "now()"
            }).execute()
            return {"message": "Message sent", "data": result.data}
        return {"message": "Message sent locally", "data": message.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/chat/{connection_id}/{user_id}")
async def websocket_chat(websocket: WebSocket, connection_id: int, user_id: str):
    await manager.connect(websocket, connection_id, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Save message to database
            if supabase:
                supabase.table("chat_messages").insert({
                    "connection_id": connection_id,
                    "sender_id": user_id,
                    "message": message_data["message"]
                }).execute()
            
            # Broadcast to all users in this connection
            await manager.send_message(data, connection_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, connection_id, user_id)

@app.websocket("/ws/notifications/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: str):
    await websocket.accept()
    manager.user_connections[user_id] = websocket
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if user_id in manager.user_connections:
            del manager.user_connections[user_id]

@app.websocket("/ws/forum/updates")
async def websocket_forum_updates(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            update_data = json.loads(data)
            
            # Broadcast forum update to all connected users
            for user_ws in manager.user_connections.values():
                try:
                    await user_ws.send_text(json.dumps({
                        "type": "forum_update",
                        "title": "Forum Update",
                        "message": f"New {update_data['type'].replace('_', ' ')}",
                        "data": update_data
                    }))
                except:
                    pass  # Handle disconnected clients
    except WebSocketDisconnect:
        pass

@app.get("/api/chat/messages/{connection_id}")
async def get_chat_messages(connection_id: int):
    """Get chat messages for a connection"""
    mock_messages = [
        {
            "id": 1,
            "sender_id": "researcher_2",
            "sender_name": "Dr. Emily Rodriguez",
            "message": "Hi! I saw your work on immunotherapy. Very impressive!",
            "sent_at": "2024-01-15T10:30:00Z",
            "is_me": False
        },
        {
            "id": 2,
            "sender_id": "current_researcher",
            "sender_name": "Me",
            "message": "Thank you! I'd love to discuss potential collaboration opportunities.",
            "sent_at": "2024-01-15T10:35:00Z",
            "is_me": True
        }
    ]
    return {"messages": mock_messages}

@app.options("/api/orcid/sync")
async def orcid_sync_options():
    return {"message": "OK"}

@app.post("/api/orcid/sync")
async def sync_orcid_data(orcid_request: ORCIDSyncRequest):
    """Sync researcher data from ORCID"""
    try:
        orcid_id = orcid_request.orcid_id
        if not orcid_id:
            raise HTTPException(status_code=400, detail="ORCID ID is required")
        
        orcid_service = ORCIDService()
        
        # Fetch real profile and publications
        profile = await orcid_service.get_researcher_profile(orcid_id)
        publications = await orcid_service.get_publications(orcid_id)
        
        if "error" in profile:
            raise HTTPException(status_code=400, detail=profile["error"])
        
        return {
            "message": "ORCID data synced successfully",
            "profile": profile,
            "publications": publications,
            "publications_count": len(publications)
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid ORCID data: {str(e)}")
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail="ORCID service unavailable")
    except Exception as e:
        raise HTTPException(status_code=500, detail="ORCID sync failed")

@app.post("/api/ai/analyze-condition")
async def analyze_condition(request: AIAnalysisRequest):
    """AI-powered condition analysis"""
    try:
        result = ai_service.analyze_condition(request.text)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/trial-summary")
async def generate_trial_summary(trial_data: dict):
    """Generate AI summary for clinical trial"""
    try:
        summary = ai_service.generate_trial_summary(trial_data)
        return {"success": True, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/research-suggestions")
async def get_research_suggestions(researcher_profile: dict):
    """Get AI-powered research collaboration suggestions"""
    try:
        suggestions = ai_service.suggest_research_collaborations(researcher_profile)
        return {"success": True, "suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/test")
async def test_ai():
    """Test if AI service is working"""
    try:
        result = ai_service.analyze_condition("Hello, test question")
        return {"success": True, "test_result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)