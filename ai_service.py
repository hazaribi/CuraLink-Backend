import os
import google.generativeai as genai
from typing import List, Dict, Any
import json

class AIService:
    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-pro')
    
    def analyze_condition(self, condition_text: str) -> Dict[str, Any]:
        """Analyze patient condition input and extract structured data or answer questions"""
        try:
            # Check if it's a question or condition statement
            if '?' in condition_text or condition_text.lower().startswith(('what', 'how', 'why', 'when', 'where', 'can', 'should', 'is', 'are')):
                # It's a question - provide medical advice
                prompt = f"Answer this medical question in simple terms for a patient: '{condition_text}'. Be helpful but remind them to consult healthcare professionals."
                response = self.model.generate_content(prompt)
                answer = response.text.strip() if response.text else "Please consult with your healthcare provider for medical advice."
                return {
                    "primaryCondition": answer,
                    "identifiedConditions": [condition_text]
                }
            else:
                # Extract condition
                prompt = f"Extract the primary medical condition from this text: '{condition_text}'. Return only the main condition name in simple terms."
                response = self.model.generate_content(prompt)
                primary_condition = response.text.strip() if response.text else condition_text
                return {
                    "primaryCondition": primary_condition,
                    "identifiedConditions": [primary_condition]
                }
        except Exception as e:
            print(f"AI analysis failed: {e}")
            return {
                "primaryCondition": condition_text,
                "identifiedConditions": [condition_text]
            }
    
    def generate_trial_summary(self, trial_data: Dict) -> str:
        """Generate patient-friendly trial summary"""
        try:
            prompt = f"Explain this clinical trial in simple terms for patients: {trial_data['title']} - {trial_data.get('description', '')}. Keep it under 200 words and be encouraging but honest."
            response = self.model.generate_content(prompt)
            return response.text if response.text else f"This trial studies {trial_data['title']}. Contact the research team for more details."
        except Exception as e:
            return f"This trial studies {trial_data['title']}. Contact the research team for more details."
    
    def suggest_research_collaborations(self, researcher_profile: Dict) -> List[str]:
        """Suggest collaboration opportunities for researchers"""
        try:
            if 'question' in researcher_profile:
                # Answer specific question
                prompt = f"Answer this research question: '{researcher_profile['question']}' for a researcher with specialties: {researcher_profile['specialties']} and interests: {researcher_profile['research_interests']}. Provide helpful advice."
            else:
                # General suggestions
                prompt = f"Suggest 3 research collaboration ideas for a researcher with specialties: {researcher_profile['specialties']} and interests: {researcher_profile['research_interests']}. List them as bullet points."
            
            response = self.model.generate_content(prompt)
            if 'question' in researcher_profile:
                return [response.text] if response.text else [f"I can help with questions about {researcher_profile['specialties']}"]
            else:
                suggestions = response.text.split('\n') if response.text else []
                return [s.strip('- •') for s in suggestions if s.strip()][:3]
        except Exception as e:
            return ["Explore interdisciplinary research opportunities", "Consider international collaborations"]

ai_service = AIService()