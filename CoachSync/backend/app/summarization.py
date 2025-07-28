import openai
import json

def summarize_meeting(transcript_text: str) -> dict:
    prompt = f"""
Summarize the following personal trainer coaching session transcript clearly and concisely.

Return in structured JSON format making sure to label action items by the speaker name:

{{
  "summary": "<Brief 2-4 sentence meeting summary>",
  "action_items": ["<Action Item 1>", "<Action Item 2>", "..."],
  "progress_notes": "<Brief notes about client's stated progress or concerns>"
}}

Transcript:
{transcript_text}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=512
    )

    result = response.choices[0].message['content']
    return json.loads(result)
