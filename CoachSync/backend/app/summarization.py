import openai
import json

client = openai.OpenAI()  # Uses OPENAI_API_KEY from env

def summarize_meeting(transcript_text: str) -> dict:
    prompt = f"""
Summarize the following personal trainer coaching session transcript clearly and concisely.

Return in structured JSON format making sure to label action items by the speaker name:

{{
  "summary": "<Brief bulleted meeting summary focused on main topics related to fitness and nutrition coaching>",
  "action_items": ["Speaker 1: <Action Item 1>","Speaker 1: <Action Item 2>", "Speaker 2: <Action Item 1>", "Speaker 2: <Action Item 2>" "..."]
}}

Transcript:
{transcript_text}
"""
    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=512
    )
    result = response.choices[0].message.content
    # Remove code block markers if present
    print(f"Raw result: {result}")
    result = result.strip()
    if result.startswith("````json"):
        result = result[7:].strip()
    elif result.startswith("```json"):
        result = result[6:].strip()
    elif result.startswith("```"):
        result = result[3:].strip()
    if result.endswith("```"):
        result = result[:-3].strip()
    parsed = json.loads(result)
    print(f"Parsed: {parsed}")
    # Map to Fireflies schema
    return {
        "overview": parsed.get("summary", ""),
        "action_items": parsed.get("action_items", []),
        "progress_notes": parsed.get("progress_notes", ""),
        "keywords": parsed.get("keywords", []),
        "outline": parsed.get("outline", ""),
        "key_points": parsed.get("key_points", []),
    }
