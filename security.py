from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
import time
from collections import defaultdict

# Rate limiting
request_counts = defaultdict(list)
RATE_LIMIT = 100  # requests per minute
RATE_WINDOW = 60  # seconds

security = HTTPBearer(auto_error=False)

def rate_limit_check(request: Request):
    """Simple rate limiting"""
    client_ip = request.client.host
    now = time.time()
    
    # Clean old requests
    request_counts[client_ip] = [
        req_time for req_time in request_counts[client_ip] 
        if now - req_time < RATE_WINDOW
    ]
    
    # Check rate limit
    if len(request_counts[client_ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Add current request
    request_counts[client_ip].append(now)

def validate_content_type(request: Request):
    """Validate content type for POST requests"""
    if request.method == "POST":
        content_type = request.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            raise HTTPException(status_code=400, detail="Invalid content type")