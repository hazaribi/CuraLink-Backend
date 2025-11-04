import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional

class ORCIDService:
    
    def __init__(self):
        self.base_url = "https://pub.orcid.org/v3.0"
        self.headers = {
            "Accept": "application/json"
        }
    
    async def get_researcher_profile(self, orcid_id: str) -> Dict:
        """Fetch researcher profile from ORCID"""
        try:
            async with httpx.AsyncClient() as client:
                # Get person details
                person_url = f"{self.base_url}/{orcid_id}/person"
                person_response = await client.get(person_url, headers=self.headers)
                person_data = person_response.json()
                
                # Extract profile information
                profile = {
                    "orcid_id": orcid_id,
                    "name": self._extract_name(person_data),
                    "institutions": self._extract_institutions(person_data),
                    "credentials_verified": True
                }
                
                return profile
                
        except Exception as e:
            print(f"ORCID profile fetch error: {e}")
            return {"error": f"Failed to fetch ORCID profile: {str(e)}"}
    
    async def get_publications(self, orcid_id: str) -> List[Dict]:
        """Fetch publications from ORCID"""
        try:
            async with httpx.AsyncClient() as client:
                # Get works summary
                works_url = f"{self.base_url}/{orcid_id}/works"
                works_response = await client.get(works_url, headers=self.headers)
                works_data = works_response.json()
                
                publications = []
                
                if "group" in works_data:
                    for group in works_data["group"][:10]:  # Limit to 10 publications
                        for work_summary in group.get("work-summary", []):
                            put_code = work_summary.get("put-code")
                            
                            # Get detailed work information
                            work_detail_url = f"{self.base_url}/{orcid_id}/work/{put_code}"
                            work_response = await client.get(work_detail_url, headers=self.headers)
                            work_data = work_response.json()
                            
                            publication = self._parse_publication(work_data)
                            if publication:
                                publications.append(publication)
                
                return publications
                
        except Exception as e:
            print(f"ORCID publications fetch error: {e}")
            return []
    
    def _extract_name(self, person_data: Dict) -> str:
        """Extract full name from ORCID person data"""
        try:
            name_data = person_data.get("name", {})
            given_names = name_data.get("given-names", {}).get("value", "")
            family_name = name_data.get("family-name", {}).get("value", "")
            return f"{given_names} {family_name}".strip()
        except:
            return "Unknown Researcher"
    
    def _extract_institutions(self, person_data: Dict) -> List[str]:
        """Extract institutions from ORCID person data"""
        try:
            institutions = []
            employments = person_data.get("activities-summary", {}).get("employments", {}).get("employment-summary", [])
            
            for employment in employments:
                org_name = employment.get("organization", {}).get("name", "")
                if org_name:
                    institutions.append(org_name)
            
            return institutions[:3]  # Limit to 3 institutions
        except:
            return []
    
    def _parse_publication(self, work_data: Dict) -> Optional[Dict]:
        """Parse ORCID work data into publication format"""
        try:
            title = work_data.get("title", {}).get("title", {}).get("value", "")
            if not title:
                return None
            
            # Extract journal
            journal = ""
            journal_title = work_data.get("journal-title")
            if journal_title:
                journal = journal_title.get("value", "")
            
            # Extract publication date
            pub_date = work_data.get("publication-date")
            date_str = "Unknown"
            if pub_date:
                year = pub_date.get("year", {}).get("value", "")
                month = pub_date.get("month", {}).get("value", "")
                if year:
                    date_str = f"{year}-{month.zfill(2) if month else '01'}-01"
            
            # Extract DOI
            doi = ""
            external_ids = work_data.get("external-ids", {}).get("external-id", [])
            for ext_id in external_ids:
                if ext_id.get("external-id-type") == "doi":
                    doi = ext_id.get("external-id-value", "")
                    break
            
            # Extract authors (simplified - ORCID doesn't always have full author lists)
            authors = ["ORCID Author"]  # Placeholder since ORCID often doesn't have complete author lists
            
            return {
                "title": title,
                "journal": journal or "Unknown Journal",
                "authors": authors,
                "date": date_str,
                "doi": doi,
                "abstract": f"Publication from ORCID: {title[:100]}...",
                "source": "ORCID"
            }
            
        except Exception as e:
            print(f"Publication parsing error: {e}")
            return None