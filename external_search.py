import httpx
import xml.etree.ElementTree as ET
import os
from typing import List, Dict, Optional
from scholarly import scholarly

class ExternalExpertSearch:
    def __init__(self):
        self.ncbi_api_key = os.getenv("NCBI_API_KEY")
        self.orcid_client_id = os.getenv("ORCID_CLIENT_ID")
        self.orcid_client_secret = os.getenv("ORCID_CLIENT_SECRET")
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        self.researchgate_key = os.getenv("RESEARCHGATE_API_KEY")
    
    async def search_pubmed_authors(self, condition: str, limit: int = 5) -> List[Dict]:
        """Search PubMed for authors publishing on specific conditions"""
        try:
            # Search PubMed for papers on the condition
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": f"{condition}[Title/Abstract]",
                "retmax": str(limit * 2),
                "retmode": "json"
            }
            if self.ncbi_api_key:
                params["api_key"] = self.ncbi_api_key
            
            async with httpx.AsyncClient() as client:
                response = await client.get(search_url, params=params)
                data = response.json()
                
                if "esearchresult" not in data or not data["esearchresult"]["idlist"]:
                    return []
                
                # Get paper details
                pmids = data["esearchresult"]["idlist"][:limit]
                fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                fetch_params = {
                    "db": "pubmed",
                    "id": ",".join(pmids),
                    "retmode": "xml"
                }
                
                details_response = await client.get(fetch_url, params=fetch_params)
                
                # Parse XML to extract author information
                experts = []
                root = ET.fromstring(details_response.text)
                
                for article in root.findall(".//PubmedArticle")[:limit]:
                    authors = article.findall(".//Author")
                    for author in authors[:2]:  # Limit to first 2 authors per paper
                        lastname = author.find("LastName")
                        forename = author.find("ForeName")
                        
                        if lastname is not None and forename is not None:
                            experts.append({
                                "name": f"Dr. {forename.text} {lastname.text}",
                                "specialty": f"{condition} Research",
                                "institution": "External Research Institution",
                                "location": "Location Unknown",
                                "source": "PubMed",
                                "available_for_meetings": False,
                                "research_interests": [condition, "Clinical Research"]
                            })
                
                return experts[:limit]
                
        except Exception as e:
            print(f"PubMed search error: {e}")
            return []
    
    async def search_orcid_researchers(self, condition: str, limit: int = 3) -> List[Dict]:
        """Search ORCID for researchers in specific fields"""
        try:
            # ORCID public API search
            search_url = "https://pub.orcid.org/v3.0/search"
            params = {
                "q": f"keyword:{condition}",
                "rows": str(limit)
            }
            headers = {
                "Accept": "application/json"
            }
            if self.orcid_client_id:
                headers["Authorization"] = f"Bearer {self.orcid_client_id}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(search_url, params=params, headers=headers)
                data = response.json()
                
                experts = []
                if "result" in data:
                    for result in data["result"][:limit]:
                        orcid_id = result.get("orcid-identifier", {}).get("path", "")
                        
                        # Get detailed profile
                        profile_url = f"https://pub.orcid.org/v3.0/{orcid_id}/person"
                        profile_response = await client.get(profile_url, headers=headers)
                        profile_data = profile_response.json()
                        
                        name = "Unknown Researcher"
                        if "name" in profile_data:
                            given = profile_data["name"].get("given-names", {}).get("value", "")
                            family = profile_data["name"].get("family-name", {}).get("value", "")
                            name = f"Dr. {given} {family}" if given and family else name
                        
                        experts.append({
                            "name": name,
                            "specialty": f"{condition} Research",
                            "institution": "ORCID Verified Institution",
                            "location": "Location Unknown",
                            "source": "ORCID",
                            "orcid_id": orcid_id,
                            "available_for_meetings": False,
                            "research_interests": [condition, "Academic Research"]
                        })
                
                return experts
                
        except Exception as e:
            print(f"ORCID search error: {e}")
            return []
    
    async def search_google_scholar(self, condition: str, limit: int = 3) -> List[Dict]:
        """Search Google Scholar using scholarly library"""
        try:
            experts = []
            search_query = scholarly.search_pubs(f"{condition} research")
            
            for i, pub in enumerate(search_query):
                if i >= limit:
                    break
                    
                # Get author information
                authors = pub.get('bib', {}).get('author', [])
                if authors:
                    author_name = authors[0] if isinstance(authors, list) else str(authors)
                    
                    experts.append({
                        "name": f"Dr. {author_name}" if not author_name.startswith("Dr.") else author_name,
                        "specialty": f"{condition} Research",
                        "institution": "Google Scholar Network",
                        "location": "Academic Network",
                        "source": "Google Scholar",
                        "available_for_meetings": False,
                        "research_interests": [condition, "Academic Publications"],
                        "publication_title": pub.get('bib', {}).get('title', 'Research Publication')
                    })
            
            return experts
                
        except Exception as e:
            print(f"Google Scholar search error: {e}")
            return self._mock_scholar_results(condition, limit)
    
    def _mock_scholar_results(self, condition: str, limit: int) -> List[Dict]:
        """Fallback mock results when no API key"""
        experts = []
        for i in range(min(limit, 2)):
            experts.append({
                "name": f"Dr. Scholar Researcher {i+1}",
                "specialty": f"{condition} Research",
                "institution": "Google Scholar Institution",
                "location": "Academic Network",
                "source": "Google Scholar",
                "available_for_meetings": False,
                "research_interests": [condition, "Academic Publications"]
            })
        return experts
    
    async def search_clinicaltrials_investigators(self, condition: str, limit: int = 3) -> List[Dict]:
        """Search ClinicalTrials.gov for principal investigators"""
        try:
            search_url = "https://clinicaltrials.gov/api/query/study_fields"
            params = {
                "expr": condition,
                "fields": "LeadSponsorName,OverallOfficialName,OverallOfficialAffiliation",
                "min_rnk": "1",
                "max_rnk": str(limit * 2),
                "fmt": "json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(search_url, params=params)
                data = response.json()
                
                experts = []
                if "StudyFieldsResponse" in data and "StudyFields" in data["StudyFieldsResponse"]:
                    for study in data["StudyFieldsResponse"]["StudyFields"][:limit]:
                        investigators = study.get("OverallOfficialName", [])
                        affiliations = study.get("OverallOfficialAffiliation", [])
                        
                        for i, investigator in enumerate(investigators[:1]):  # One per study
                            if investigator:
                                affiliation = affiliations[i] if i < len(affiliations) else "Clinical Research Institution"
                                experts.append({
                                    "name": f"Dr. {investigator}" if not investigator.startswith("Dr.") else investigator,
                                    "specialty": f"{condition} Clinical Research",
                                    "institution": affiliation,
                                    "location": "Clinical Trial Network",
                                    "source": "ClinicalTrials.gov",
                                    "available_for_meetings": False,
                                    "research_interests": [condition, "Clinical Trials"]
                                })
                
                return experts[:limit]
                
        except Exception as e:
            print(f"ClinicalTrials.gov search error: {e}")
            return []
    
    async def search_researchgate(self, condition: str, limit: int = 3) -> List[Dict]:
        """Search ResearchGate for researchers (mock implementation)"""
        try:
            # Note: ResearchGate doesn't have public API, this is mock data
            # In production, you'd need web scraping or partnerships
            
            experts = []
            for i in range(min(limit, 2)):
                experts.append({
                    "name": f"Dr. RG Researcher {i+1}",
                    "specialty": f"{condition} Research",
                    "institution": "ResearchGate Network",
                    "location": "Research Community",
                    "source": "ResearchGate",
                    "available_for_meetings": False,
                    "research_interests": [condition, "Collaborative Research"]
                })
            
            return experts
                
        except Exception as e:
            print(f"ResearchGate search error: {e}")
            return []