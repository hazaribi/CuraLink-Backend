import os
import requests
from typing import List, Dict, Any

class AIService:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_AI_API_KEY")
        if not self.api_key:
            print("WARNING: GOOGLE_AI_API_KEY not found!")
        else:
            print(f"Configuring Gemini with API key: {self.api_key[:10]}...")
    
    def analyze_condition(self, condition_text: str) -> Dict[str, Any]:
        """Analyze patient condition input and extract structured data or answer questions"""
        try:
            print(f"Analyzing condition: {condition_text}")
            
            if not self.api_key:
                raise Exception("API key missing")
            
            # Check if it's a question or condition statement
            if '?' in condition_text or condition_text.lower().startswith(('what', 'how', 'why', 'when', 'where', 'can', 'should', 'is', 'are', 'hi', 'hello', 'help')):
                # It's a question - provide medical advice
                prompt = f"Answer this medical question in simple terms for a patient: '{condition_text}'. Be helpful but remind them to consult healthcare professionals. Keep response under 100 words."
                
                response = self._call_gemini_api(prompt)
                if response:
                    return {
                        "primaryCondition": response,
                        "identifiedConditions": [condition_text]
                    }
                else:
                    raise Exception("No response from API")
            else:
                # Extract condition
                prompt = f"Extract the primary medical condition from this text: '{condition_text}'. Return only the main condition name in simple terms."
                
                response = self._call_gemini_api(prompt)
                if response:
                    return {
                        "primaryCondition": response,
                        "identifiedConditions": [response]
                    }
                else:
                    raise Exception("No response from API")
                    
        except Exception as e:
            print(f"AI analysis failed: {e}")
            # Fallback responses
            if '?' in condition_text or condition_text.lower().startswith(('what', 'how', 'why', 'when', 'where', 'can', 'should', 'is', 'are', 'hi', 'hello', 'help')):
                return {
                    "primaryCondition": "I'm here to help with medical questions and finding researchers. What specific condition or research area interests you?",
                    "identifiedConditions": [condition_text]
                }
            else:
                return {
                    "primaryCondition": condition_text,
                    "identifiedConditions": [condition_text]
                }
    
    def generate_trial_summary(self, trial_data: Dict) -> str:
        """Generate patient-friendly trial summary"""
        try:
            prompt = f"Explain this clinical trial in simple terms for patients: {trial_data['title']} - {trial_data.get('description', '')}. Keep it under 200 words and be encouraging but honest."
            response = self._call_gemini_api(prompt)
            return response if response else f"This trial studies {trial_data['title']}. Contact the research team for more details."
        except Exception as e:
            return f"This trial studies {trial_data['title']}. Contact the research team for more details."
    
    def suggest_research_collaborations(self, researcher_profile: Dict) -> List[str]:
        """Suggest collaboration opportunities for researchers"""
        try:
            print(f"Research profile: {researcher_profile}")
            
            if 'question' in researcher_profile:
                # Answer specific question
                prompt = f"Answer this research question: '{researcher_profile['question']}' for a researcher with specialties: {researcher_profile.get('specialties', [])} and interests: {researcher_profile.get('research_interests', [])}. Provide helpful advice in 2-3 sentences."
                response = self._call_gemini_api(prompt)
                
                if response:
                    return [response]
                else:
                    raise Exception("No response from API")
            else:
                # General suggestions
                prompt = f"Suggest 3 research collaboration ideas for a researcher with specialties: {researcher_profile.get('specialties', [])} and interests: {researcher_profile.get('research_interests', [])}. List them as bullet points."
                response = self._call_gemini_api(prompt)
                
                if response:
                    suggestions = [s.strip('- •').strip() for s in response.split('\n') if s.strip()]
                    return suggestions[:3] if suggestions else ["Consider interdisciplinary collaborations", "Explore international partnerships", "Join research networks in your field"]
                else:
                    raise Exception("No response from API")
                    
        except Exception as e:
            print(f"Research AI failed: {e}")
            specialties = researcher_profile.get('specialties', [])
            if specialties:
                return [f"I can help with research in {', '.join(specialties)}. What specific research challenge are you facing?"]
            else:
                return ["I can help with research collaboration and academic questions. What would you like to know?"]
    
    def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API using REST requests"""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.api_key}"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            print(f"Calling Gemini API with prompt: {prompt[:50]}...")
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'candidates' in data and len(data['candidates']) > 0:
                    content = data['candidates'][0]['content']['parts'][0]['text']
                    print(f"Gemini API response: {content[:100]}...")
                    return content.strip()
                else:
                    print("No candidates in response")
                    return None
            else:
                print(f"API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"API call failed: {e}")
            return None

ai_service = AIService()