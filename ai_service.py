import os
import requests
from typing import List, Dict, Any

class AIService:
    def __init__(self):
        self.api_key = None
        self._load_api_key()
    
    def _load_api_key(self):
        """Load API key from environment"""
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
                print("WARNING: No API key found, using fallback response")
                return self._get_fallback_response(condition_text)
            
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
                    return self._get_fallback_response(condition_text)
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
                    return self._get_fallback_response(condition_text)
                    
        except Exception as e:
            print(f"AI analysis failed: {e}")
            return self._get_fallback_response(condition_text)
    
    def _get_fallback_response(self, condition_text: str) -> Dict[str, Any]:
        """Provide fallback responses when AI is unavailable"""
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
            prompt = f"""Create a clear, patient-friendly summary of this clinical trial:
            
Title: {trial_data['title']}
Phase: {trial_data.get('phase', 'Unknown')}
Status: {trial_data.get('status', 'Unknown')}
Description: {trial_data.get('description', '')}
            
Format your response as:
1. What this trial is studying (1-2 sentences)
2. Who might be eligible (1 sentence)
3. Key benefits or goals (1 sentence)
4. Next steps for interested patients (1 sentence)
            
Use simple language, be encouraging but honest, and keep under 150 words."""
            
            response = self._call_gemini_api(prompt)
            return response if response else f"This {trial_data.get('phase', '')} trial is studying {trial_data['title']}. Contact the research team to learn about eligibility and participation details."
        except Exception as e:
            return f"This {trial_data.get('phase', '')} trial is studying {trial_data['title']}. Contact the research team to learn about eligibility and participation details."
    
    def suggest_research_collaborations(self, researcher_profile: Dict) -> List[str]:
        """Suggest collaboration opportunities for researchers"""
        try:
            print(f"Research profile: {researcher_profile}")
            
            if not self.api_key:
                print("WARNING: No API key found, using fallback response")
                return self._get_research_fallback(researcher_profile)
            
            if 'question' in researcher_profile:
                # Answer specific question
                prompt = f"Answer this research question: '{researcher_profile['question']}' for a researcher with specialties: {researcher_profile.get('specialties', [])} and interests: {researcher_profile.get('research_interests', [])}. Provide helpful advice in 2-3 sentences."
                response = self._call_gemini_api(prompt)
                
                if response:
                    return [response]
                else:
                    return self._get_research_fallback(researcher_profile)
            else:
                # General suggestions
                prompt = f"Suggest 3 research collaboration ideas for a researcher with specialties: {researcher_profile.get('specialties', [])} and interests: {researcher_profile.get('research_interests', [])}. List them as bullet points."
                response = self._call_gemini_api(prompt)
                
                if response:
                    suggestions = [s.strip('- •').strip() for s in response.split('\n') if s.strip()]
                    return suggestions[:3] if suggestions else self._get_research_fallback(researcher_profile)
                else:
                    return self._get_research_fallback(researcher_profile)
                    
        except Exception as e:
            print(f"Research AI failed: {e}")
            return self._get_research_fallback(researcher_profile)
    
    def _get_research_fallback(self, researcher_profile: Dict) -> List[str]:
        """Provide fallback responses for research questions"""
        if 'question' in researcher_profile:
            specialties = researcher_profile.get('specialties', [])
            if specialties:
                return [f"I can help with research in {', '.join(specialties)}. What specific research challenge are you facing?"]
            else:
                return ["I can help with research collaboration and academic questions. What would you like to know?"]
        else:
            return ["Consider interdisciplinary collaborations", "Explore international partnerships", "Join research networks in your field"]
    
    def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API using REST requests"""
        try:
            # Reload API key if not present
            if not self.api_key:
                self._load_api_key()
            
            if not self.api_key:
                print("ERROR: No API key available")
                return None
                
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
            
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
            
            print(f"API Key present: {bool(self.api_key)}")
            print(f"API Key length: {len(self.api_key) if self.api_key else 0}")
            print(f"Calling Gemini API with prompt: {prompt[:50]}...")
            print(f"URL: {url[:80]}...")
            
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response data keys: {list(data.keys())}")
                
                if 'candidates' in data and len(data['candidates']) > 0:
                    candidate = data['candidates'][0]
                    print(f"Candidate keys: {list(candidate.keys())}")
                    
                    if 'content' in candidate and 'parts' in candidate['content']:
                        content = candidate['content']['parts'][0]['text']
                        print(f"SUCCESS: Gemini API response: {content[:100]}...")
                        return content.strip()
                    else:
                        print(f"ERROR: Unexpected candidate structure: {candidate}")
                        return None
                else:
                    print(f"ERROR: No candidates in response: {data}")
                    return None
            else:
                print(f"ERROR: API call failed with status {response.status_code}")
                print(f"ERROR: Response text: {response.text}")
                return None
                
        except Exception as e:
            print(f"EXCEPTION: API call failed: {e}")
            import traceback
            print(f"TRACEBACK: {traceback.format_exc()}")
            return None

ai_service = AIService()