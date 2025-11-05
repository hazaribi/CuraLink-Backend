from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import httpx
import json
from dotenv import load_dotenv
from supabase import create_client, Client
from external_search import ExternalExpertSearch
from admin_requests import AdminRequestHandler
from orcid_service import ORCIDService

load_dotenv()

app = FastAPI(title="CuraLink API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for deployment
    allow_credentials=True,
    allow_methods=["*"],
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

@app.get("/api/admin/test")
async def test_admin():
    return {"test": "working", "requests": [{"id": "test1", "type": "test", "status": "pending"}]}

@app.post("/api/patients/profile")
async def create_patient_profile(profile: PatientProfile):
    """Create or update patient profile"""
    try:
        if supabase:
            result = supabase.table("patient_profiles").insert(profile.dict()).execute()
            return {"message": "Profile created successfully", "data": result.data}
        return {"message": "Profile saved locally", "data": profile.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    """Get clinical trials from ClinicalTrials.gov API"""
    try:
        if condition:
            # ClinicalTrials.gov API integration
            ct_url = "https://clinicaltrials.gov/api/query/study_fields"
            params = {
                "expr": condition,
                "fields": "NCTId,BriefTitle,Phase,OverallStatus,LocationCountry,BriefSummary",
                "min_rnk": "1",
                "max_rnk": "10",
                "fmt": "json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(ct_url, params=params)
                data = response.json()
                
                trials = []
                if "StudyFieldsResponse" in data and "StudyFields" in data["StudyFieldsResponse"]:
                    for i, study in enumerate(data["StudyFieldsResponse"]["StudyFields"][:5]):
                        trials.append({
                            "id": i + 1,
                            "title": study.get("BriefTitle", [""])[0] if study.get("BriefTitle") else f"Clinical Trial for {condition}",
                            "phase": study.get("Phase", [""])[0] if study.get("Phase") else "Phase Unknown",
                            "status": study.get("OverallStatus", [""])[0] if study.get("OverallStatus") else "Status Unknown",
                            "location": study.get("LocationCountry", [""])[0] if study.get("LocationCountry") else "Location Unknown",
                            "description": study.get("BriefSummary", [""])[0][:200] + "..." if study.get("BriefSummary") and study.get("BriefSummary")[0] else f"Clinical trial studying {condition}"
                        })
                    
                    if trials:
                        return {"trials": trials}
        
        # Fallback to mock data
        mock_trials = [
            {
                "id": 1,
                "title": "Immunotherapy Trial for Brain Cancer",
                "phase": "Phase II",
                "status": "Recruiting",
                "location": "New York, USA",
                "description": "Testing new immunotherapy approach for brain cancer patients"
            },
            {
                "id": 2,
                "title": "Novel Treatment for Glioblastoma",
                "phase": "Phase III",
                "status": "Recruiting",
                "location": "Boston, USA",
                "description": "Advanced treatment protocol for glioblastoma patients"
            }
        ]
        
        if condition:
            mock_trials = [t for t in mock_trials if condition.lower() in t["title"].lower()]
        
        return {"trials": mock_trials}
        
    except Exception as e:
        # Return mock data on error
        return {"trials": [
            {
                "id": 1,
                "title": f"Clinical Trial for {condition or 'Medical Condition'}",
                "phase": "Phase II",
                "status": "Recruiting",
                "location": "Multiple Locations",
                "description": f"Clinical trial studying treatments for {condition or 'various medical conditions'}."
            }
        ]}

@app.get("/api/health-experts")
async def get_health_experts(specialty: Optional[str] = None, location: Optional[str] = None, include_external: bool = False):
    """Get health experts based on specialty and location"""
    mock_experts = [
        {
            "id": 1,
            "name": "Dr. Sarah Johnson",
            "specialty": "Neuro-Oncology",
            "institution": "Memorial Sloan Kettering",
            "location": "New York, USA",
            "available_for_meetings": True,
            "research_interests": ["Brain Cancer", "Immunotherapy"]
        },
        {
            "id": 2,
            "name": "Dr. Michael Chen",
            "specialty": "Brain Cancer Research",
            "institution": "Johns Hopkins",
            "location": "Baltimore, USA",
            "available_for_meetings": False,
            "research_interests": ["Glioblastoma", "Gene Therapy"]
        },
        {
            "id": 3,
            "name": "Dr. Priya Sharma",
            "specialty": "Oncology",
            "institution": "AIIMS Delhi",
            "location": "Delhi, India",
            "available_for_meetings": True,
            "research_interests": ["Cancer Research", "Clinical Trials"]
        },
        {
            "id": 4,
            "name": "Dr. James Wilson",
            "specialty": "Cardiology",
            "institution": "Mayo Clinic",
            "location": "Rochester, USA",
            "available_for_meetings": True,
            "research_interests": ["Heart Disease", "Preventive Care"]
        },
        {
            "id": 5,
            "name": "Dr. Emma Thompson",
            "specialty": "Neurology",
            "institution": "Oxford University",
            "location": "Oxford, UK",
            "available_for_meetings": False,
            "research_interests": ["Alzheimer", "Parkinson"]
        },
        {
            "id": 6,
            "name": "Dr. Raj Patel",
            "specialty": "Diabetes Research",
            "institution": "Mumbai Medical College",
            "location": "Mumbai, India",
            "available_for_meetings": True,
            "research_interests": ["Diabetes", "Endocrinology"]
        },
        {
            "id": 7,
            "name": "Dr. Lisa Anderson",
            "specialty": "Psychiatry",
            "institution": "Harvard Medical School",
            "location": "Boston, USA",
            "available_for_meetings": True,
            "research_interests": ["Depression", "Anxiety"]
        },
        {
            "id": 8,
            "name": "Dr. David Brown",
            "specialty": "Orthopedics",
            "institution": "Toronto General Hospital",
            "location": "Toronto, Canada",
            "available_for_meetings": False,
            "research_interests": ["Arthritis", "Joint Surgery"]
        }
    ]
    
    if specialty:
        mock_experts = [e for e in mock_experts if specialty.lower() in e["specialty"].lower()]
    
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
            
            mock_experts.extend(pubmed_experts)
            mock_experts.extend(orcid_experts)
        except Exception as e:
            print(f"External search failed: {e}")
    
    # Add profile visibility flags to registered experts
    for expert in mock_experts:
        if "profile_type" not in expert:
            expert["profile_type"] = "registered"
            expert["contact_available"] = expert.get("available_for_meetings", False)
            expert["needs_admin_review"] = False
            expert["data_source"] = "CuraLink Profile"
    
    return {"experts": mock_experts}

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
                            root = ET.fromstring(details_response.text)
                            articles = root.findall(".//PubmedArticle")
                            
                            for i, article in enumerate(articles[:5]):
                                pmid = pmids[i] if i < len(pmids) else str(i+1)
                                
                                # Extract title
                                title_elem = article.find(".//ArticleTitle")
                                title = html.unescape(title_elem.text) if title_elem is not None else f"{keyword} Research Study"
                                
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
                                
                                if not authors:
                                    authors = ["Research Team"]
                                
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
async def get_collaborators(specialty: Optional[str] = None, research_interest: Optional[str] = None):
    """Get potential collaborators for researchers"""
    mock_collaborators = [
        {
            "id": 1,
            "name": "Dr. Emily Rodriguez",
            "specialty": "Immunology",
            "institution": "Stanford University",
            "research_interests": ["Immunotherapy", "Clinical AI"],
            "publications_count": 45,
            "available_for_collaboration": True
        },
        {
            "id": 2,
            "name": "Dr. James Wilson",
            "specialty": "Oncology",
            "institution": "Mayo Clinic",
            "research_interests": ["Gene Therapy", "Drug Discovery"],
            "publications_count": 67,
            "available_for_collaboration": True
        }
    ]
    
    if specialty:
        mock_collaborators = [c for c in mock_collaborators if specialty.lower() in c["specialty"].lower()]
    
    return {"collaborators": mock_collaborators}

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
                "id": f"req_{len(global_admin_requests) + 1}_{request.researcher_id}",
                "type": "external_expert_contact",
                "patient_name": request.patient_name,
                "patient_email": request.email,
                "expert_name": f"Expert ID: {request.researcher_id}",
                "message": request.message or "Patient requesting meeting",
                "urgency": request.urgency,
                "status": "pending_admin_review",
                "created_at": datetime.datetime.now().isoformat()
            }
            
            print(f"Admin request created: {admin_request}")
            
            if supabase:
                try:
                    result = supabase.table("admin_requests").insert(admin_request).execute()
                    print(f"Supabase insert result: {result}")
                except Exception as e:
                    print(f"Supabase insert failed: {e}")
            else:
                # Store in global list when Supabase is not available
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
                "researcher_id": request.researcher_id,
                "message": request.message,
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

@app.post("/api/orcid/sync")
async def sync_orcid_data(orcid_data: dict):
    """Sync researcher data from ORCID"""
    try:
        orcid_id = orcid_data.get("orcid_id")
        if not orcid_id:
            raise HTTPException(status_code=400, detail="ORCID ID is required")
        
        orcid_service = ORCIDService()
        
        # Fetch profile and publications
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ORCID sync failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)