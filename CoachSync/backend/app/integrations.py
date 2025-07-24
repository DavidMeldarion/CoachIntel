# Fireflies/Zoom API integration helpers for CoachSync
import os
import httpx
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

FIREFLIES_API_KEY = os.getenv("FIREFLIES_API_KEY")
ZOOM_JWT = os.getenv("ZOOM_JWT")
FIREFLIES_API_URL = "https://api.fireflies.ai/graphql"

async def fetch_fireflies_meetings(user_email: str, api_key: str = None, limit: int = 10) -> Dict[str, Any]:
    """
    Fetch meetings from Fireflies.ai for a given user using GraphQL API.
    
    Args:
        user_email: Email of the user to fetch meetings for
        api_key: Fireflies API key (if not provided, uses env var)
        limit: Maximum number of meetings to fetch (default 10)
    
    Returns:
        Dict containing meetings data or error message    """
    if not api_key:
        api_key = FIREFLIES_API_KEY
    if not api_key:
        return {"error": "Fireflies API key not provided"}
    
    # GraphQL query to fetch transcripts (meetings) - optimized for timeline view
    query = """
    query GetTranscripts($limit: Int!, $hostEmail: String) {
        transcripts(limit: $limit, host_email: $hostEmail) {
            id
            title
            date
            duration
            meeting_link
            summary {
                keywords
                action_items
                outline
                shorthand_bullet
                overview
            }
            participants
        }
    }
    """
    
    variables = {
        "limit": limit,
        "hostEmail": user_email
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "query": query,
        "variables": variables
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                FIREFLIES_API_URL, 
                headers=headers, 
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Check for GraphQL errors
            if "errors" in result:
                return {
                    "error": "Fireflies API error",
                    "details": result["errors"]
                }
              # Transform the data for easier consumption
            transcripts = result.get("data", {}).get("transcripts", [])
            
            meetings = []
            for transcript in transcripts:
                summary = transcript.get("summary") or {}
                # Convert Fireflies transcript to our meeting format
                meeting = {
                    "id": transcript.get("id"),
                    "title": transcript.get("title", "Untitled Meeting"),
                    "date": transcript.get("date"),
                    "duration": transcript.get("duration"),
                    "meeting_url": transcript.get("meeting_link"),
                    "participants": [
                        {"name": name, "email": ""} 
                        for name in transcript.get("participants", [])
                    ],
                    "summary": {
                        "keywords": summary.get("keywords") if isinstance(summary.get("keywords"), list) else [],
                        "action_items": summary.get("action_items") if isinstance(summary.get("action_items"), list) else [],
                        "outline": summary.get("outline", ""),
                        "overview": summary.get("overview", ""),
                        "key_points": summary.get("shorthand_bullet") if isinstance(summary.get("shorthand_bullet"), list) else []
                    },                    "transcript_available": True,  # Assume transcripts are available for all meetings
                    "source": "fireflies"
                }
                meetings.append(meeting)
            
            return {
                "meetings": meetings,
                "total_count": len(meetings),
                "source": "fireflies"
            }
            
    except httpx.TimeoutException:
        return {"error": "Request timeout - Fireflies API took too long to respond"}
    except httpx.HTTPStatusError as e:
        return {
            "error": f"HTTP error {e.response.status_code}",
            "details": f"Fireflies API returned: {e.response.text}"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "error": "Unexpected error occurred",
            "details": str(e)
        }

def fetch_fireflies_meetings_sync(user_email: str, api_key: str = None, limit: int = 10) -> Dict[str, Any]:
    import requests
    if not api_key:
        api_key = FIREFLIES_API_KEY
    if not api_key:
        return {"error": "Fireflies API key not provided"}
    query = """
    query GetTranscripts($limit: Int!, $hostEmail: String) {
        transcripts(limit: $limit, host_email: $hostEmail) {
            id
            title
            date
            duration
            meeting_link
            summary {
                keywords
                action_items
                outline
                shorthand_bullet
                overview
            }
            participants
        }
    }
    """
    variables = {
        "limit": limit,
        "hostEmail": user_email
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "query": query,
        "variables": variables
    }
    try:
        response = requests.post(
            FIREFLIES_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        if "errors" in result:
            return {
                "error": "Fireflies API error",
                "details": result["errors"]
            }
        transcripts = result.get("data", {}).get("transcripts", [])
        meetings = []
        for transcript in transcripts:
            summary = transcript.get("summary") or {}
            meeting = {
                "id": transcript.get("id"),
                "title": transcript.get("title", "Untitled Meeting"),
                "date": transcript.get("date"),
                "duration": transcript.get("duration"),
                "meeting_url": transcript.get("meeting_link"),
                "participants": [
                    {"name": name, "email": ""}
                    for name in transcript.get("participants", [])
                ],
                "summary": {
                    "keywords": summary.get("keywords") if isinstance(summary.get("keywords"), list) else [],
                    "action_items": summary.get("action_items") if isinstance(summary.get("action_items"), list) else [],
                    "outline": summary.get("outline", ""),
                    "overview": summary.get("overview", ""),
                    "key_points": summary.get("shorthand_bullet") if isinstance(summary.get("shorthand_bullet"), list) else []
                },
                "transcript_available": True,
                "source": "fireflies"
            }
            meetings.append(meeting)
        return {
            "meetings": meetings,
            "total_count": len(meetings),
            "source": "fireflies"
        }
    except requests.Timeout:
        return {"error": "Request timeout - Fireflies API took too long to respond"}
    except requests.RequestException as e:
        return {"error": f"HTTP error {getattr(e.response, 'status_code', 'unknown')}", "details": str(e)}
    except Exception as e:
        return {"error": "Unexpected error occurred", "details": str(e)}

async def get_fireflies_meeting_details(transcript_id: str, api_key: str = None) -> Dict[str, Any]:
    """
    Get detailed information for a specific Fireflies meeting/transcript.
    
    Args:
        transcript_id: ID of the transcript to fetch details for
        api_key: Fireflies API key
    
    Returns:
        Dict containing detailed meeting data
    """
    if not api_key:
        api_key = FIREFLIES_API_KEY
    
    if not api_key:
        return {"error": "Fireflies API key not provided"}
    
    query = """
    query GetTranscript($transcriptId: String!) {
        transcript(id: $transcriptId) {
            id
            title
            date
            duration
            meeting_url
            audio_url
            summary {
                keywords
                action_items
                outline
                shorthand_bullet
                overview
                bullet_gist
            }
            participants {
                name
                email
                user_id
            }
            sentences {
                text
                speaker_name
                start_time
                end_time
                speaker_id
            }
            chapters {
                title
                start_time
                end_time
                gist
            }
        }
    }
    """
    
    variables = {"transcriptId": transcript_id}
    
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "query": query,
        "variables": variables
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                FIREFLIES_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "errors" in result:
                return {
                    "error": "Fireflies API error", 
                    "details": result["errors"]
                }
            
            transcript = result.get("data", {}).get("transcript")
            if not transcript:
                return {"error": "Transcript not found"}
            
            return {
                "meeting": transcript,
                "source": "fireflies"
            }
            
    except Exception as e:
        return {
            "error": "Failed to fetch meeting details",
            "details": str(e)
        }

async def fetch_zoom_meetings(user_id: str, jwt: str = None):
    """Fetch meetings from Zoom for a given user."""
    url = f"https://api.zoom.us/v2/users/{user_id}/meetings"
    headers = {"Authorization": f"Bearer {jwt}"} if jwt else {}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()
