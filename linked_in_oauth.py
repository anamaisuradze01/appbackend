import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")


def get_auth_url() -> str:
    """
    Returns the LinkedIn OAuth URL for user redirection.
    """
    if not CLIENT_ID or not REDIRECT_URI:
        raise ValueError("LINKEDIN_CLIENT_ID and REDIRECT_URI must be set in environment variables")
    
    return (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=openid profile email"
    )


def get_access_token(code: str) -> dict:
    """
    Exchanges the OAuth code for an access token.
    Returns dict with access_token or error.
    """
    if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
        return {"error": "Missing LinkedIn OAuth credentials in environment variables"}
    
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        error_detail = e.response.text if e.response else str(e)
        return {"error": f"HTTP error: {e.response.status_code if e.response else 'unknown'}", "details": error_detail}
    except requests.RequestException as e:
        return {"error": "Network error", "details": str(e)}
    except Exception as e:
        return {"error": "Unexpected error", "details": str(e)}


def get_linkedin_profile(access_token: str) -> dict:
    """
    Fetches LinkedIn profile information using the access token.
    Returns a dictionary suitable for frontend consumption.
    """
    if not access_token:
        return {"error": "Access token is required"}
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        # Fetch basic profile using OpenID Connect userinfo endpoint
        profile_response = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers=headers,
            timeout=10
        )
        profile_response.raise_for_status()
        profile = profile_response.json()
        
        # Format the response
        return {
            "name": profile.get("name", ""),
            "firstName": profile.get("given_name", ""),
            "lastName": profile.get("family_name", ""),
            "email": profile.get("email", ""),
            "id": profile.get("sub", ""),
            "picture": profile.get("picture", ""),
            "full_profile": profile
        }
    except requests.HTTPError as e:
        error_detail = e.response.text if e.response else str(e)
        return {"error": f"HTTP error: {e.response.status_code if e.response else 'unknown'}", "details": error_detail}
    except requests.RequestException as e:
        return {"error": "Network error", "details": str(e)}
    except Exception as e:
        return {"error": "Unexpected error", "details": str(e)}
