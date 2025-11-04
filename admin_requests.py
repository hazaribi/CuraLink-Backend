from typing import Dict, List
import json
from datetime import datetime

class AdminRequestHandler:
    
    def create_admin_request(self, request_data: Dict) -> Dict:
        """Create admin request for external expert contact"""
        admin_request = {
            "id": f"admin_{int(datetime.now().timestamp())}",
            "type": "external_expert_contact",
            "patient_name": request_data.get("patientName"),
            "patient_email": request_data.get("email"),
            "patient_phone": request_data.get("phone"),
            "expert_name": request_data.get("expertName"),
            "expert_source": request_data.get("expertSource", "external"),
            "message": request_data.get("message"),
            "urgency": request_data.get("urgency", "normal"),
            "status": "pending_admin_review",
            "created_at": datetime.now().isoformat(),
            "actions_needed": [
                "Contact external expert",
                "Send platform invitation",
                "Forward meeting request",
                "Notify patient of progress"
            ]
        }
        
        return admin_request
    
    def create_nudge_invitation(self, expert_data: Dict) -> Dict:
        """Create invitation nudge for external expert"""
        invitation = {
            "expert_name": expert_data.get("name"),
            "expert_email": self._guess_email(expert_data.get("name")),
            "expert_institution": expert_data.get("institution"),
            "invitation_type": "platform_join",
            "source": expert_data.get("source"),
            "benefits": [
                "Connect directly with patients seeking your expertise",
                "Expand your research network",
                "Access to clinical trial opportunities",
                "Professional profile visibility"
            ],
            "call_to_action": "Join CuraLink to connect with patients and researchers",
            "created_at": datetime.now().isoformat()
        }
        
        return invitation
    
    def _guess_email(self, name: str) -> str:
        """Generate potential email for expert outreach"""
        if not name:
            return "unknown@institution.edu"
        
        # Simple email generation for demo
        parts = name.lower().replace("dr. ", "").split()
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[-1]}@institution.edu"
        return f"{parts[0]}@institution.edu"