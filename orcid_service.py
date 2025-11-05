import httpx
import json
from typing import Dict, List, Any

class ORCIDService:
    def __init__(self):
        self.base_url = "https://pub.orcid.org/v3.0"
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "CuraLink/1.0"
        }
    
    async def get_researcher_profile(self, orcid_id: str) -> Dict[str, Any]:
        """Get researcher profile from ORCID"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/{orcid_id}/person",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    name_data = data.get("name", {})
                    given_names = name_data.get("given-names", {}).get("value", "")
                    family_name = name_data.get("family-name", {}).get("value", "")
                    
                    return {
                        "name": f"{given_names} {family_name}".strip() or "ORCID Researcher",
                        "orcid_id": orcid_id,
                        "verified": True
                    }
                else:
                    return {"error": f"ORCID profile not found: {response.status_code}"}
                    
        except Exception as e:
            return {"error": f"Failed to fetch ORCID profile: {str(e)}"}
    
    async def get_publications(self, orcid_id: str) -> List[Dict[str, Any]]:
        """Get publications from ORCID"""
        try:
            async with httpx.AsyncClient() as client:
                # Get works summary
                response = await client.get(
                    f"{self.base_url}/{orcid_id}/works",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    return []
                
                works_data = response.json()
                publications = []
                
                # Get details for each work (limit to first 5)
                work_groups = works_data.get("group", [])[:5]
                
                for group in work_groups:
                    work_summaries = group.get("work-summary", [])
                    if work_summaries:
                        work_summary = work_summaries[0]
                        put_code = work_summary.get("put-code")
                        
                        if put_code:
                            # Get detailed work information
                            detail_response = await client.get(
                                f"{self.base_url}/{orcid_id}/work/{put_code}",
                                headers=self.headers,
                                timeout=10.0
                            )
                            
                            if detail_response.status_code == 200:
                                work_detail = detail_response.json()
                                
                                # Extract publication info
                                title = ""
                                if work_detail.get("title") and work_detail["title"].get("title"):
                                    title = work_detail["title"]["title"].get("value", "")
                                
                                journal = ""
                                if work_detail.get("journal-title") and work_detail["journal-title"].get("value"):
                                    journal = work_detail["journal-title"]["value"]
                                
                                # Extract publication date
                                date = "2024-01-01"
                                pub_date = work_detail.get("publication-date")
                                if pub_date:
                                    year = pub_date.get("year", {}).get("value", "2024")
                                    month = pub_date.get("month", {}).get("value", "01")
                                    day = pub_date.get("day", {}).get("value", "01")
                                    date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                                
                                # Extract DOI
                                doi = ""
                                external_ids = work_detail.get("external-ids", {}).get("external-id", [])
                                for ext_id in external_ids:
                                    if ext_id.get("external-id-type") == "doi":
                                        doi = ext_id.get("external-id-value", "")
                                        break
                                
                                if title:  # Only add if we have a title
                                    publications.append({
                                        "title": title,
                                        "journal": journal or "Academic Journal",
                                        "date": date,
                                        "doi": doi
                                    })
                
                return publications
                
        except Exception as e:
            print(f"Error fetching ORCID publications: {e}")
            return []