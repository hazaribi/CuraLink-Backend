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
            print(f"Analyzing condition: {condition_text}")
            
            # Check if it's a question or condition statement
            if '?' in condition_text or condition_text.lower().startswith(('what', 'how', 'why', 'when', 'where', 'can', 'should', 'is', 'are', 'hi', 'hello', 'help')):
                # It's a question - provide medical advice
                prompt = f"Answer this medical question in simple terms for a patient: '{condition_text}'. Be helpful but remind them to consult healthcare professionals. Keep response under 100 words."
                response = self.model.generate_content(prompt)
                answer = response.text.strip() if response.text else "I can help you with medical questions. Please consult with your healthcare provider for specific medical advice."
                print(f"AI response: {answer}")
                return {
                    "primaryCondition": answer,
                    "identifiedConditions": [condition_text]
                }
            else:
                # Extract condition
                prompt = f"Extract the primary medical condition from this text: '{condition_text}'. Return only the main condition name in simple terms."
                response = self.model.generate_content(prompt)
                primary_condition = response.text.strip() if response.text else condition_text
                print(f"Extracted condition: {primary_condition}")
                return {
                    "primaryCondition": primary_condition,
                    "identifiedConditions": [primary_condition]
                }
        except Exception as e:
            print(f"AI analysis failed: {e}")
            return {
                "primaryCondition": f"I can help you with medical questions about {condition_text}. What would you like to know?",
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
            print(f"Research profile: {researcher_profile}")
            
            if 'question' in researcher_profile:
                # Answer specific question
                prompt = f"Answer this research question: '{researcher_profile['question']}' for a researcher with specialties: {researcher_profile.get('specialties', [])} and interests: {researcher_profile.get('research_interests', [])}. Provide helpful advice in 2-3 sentences."
                response = self.model.generate_content(prompt)
                answer = response.text.strip() if response.text else f"I can help with questions about {researcher_profile.get('specialties', ['research'])}. What specific challenge are you facing?"
                print(f"Research AI response: {answer}")
                return [answer]
            else:
                # General suggestions
                prompt = f"Suggest 3 research collaboration ideas for a researcher with specialties: {researcher_profile.get('specialties', [])} and interests: {researcher_profile.get('research_interests', [])}. List them as bullet points."
                response = self.model.generate_content(prompt)
                if response.text:
                    suggestions = [s.strip('- •').strip() for s in response.text.split('\n') if s.strip()]
                    print(f"Research suggestions: {suggestions}")
                    return suggestions[:3] if suggestions else ["Consider interdisciplinary collaborations", "Explore international partnerships", "Join research networks in your field"]
                else:
                    return ["Consider interdisciplinary collaborations", "Explore international partnerships", "Join research networks in your field"]
        except Exception as e:
            print(f"Research AI failed: {e}")
            return [f"I can help with research questions about {researcher_profile.get('specialties', ['your field'])}. What would you like to know?"]

ai_service = AIService()