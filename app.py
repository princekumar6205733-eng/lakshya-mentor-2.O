import os
import time
from google import genai
from google.genai import types
import gradio as gr

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

SYSTEM_INSTRUCTION = """
Tumhara naam Lakshya Mentor 2.0 hai. Tum Abhishek ke bade bhaiya ke dwara banaye gaye ek personal 24/7 AI study companion aur mentor ho. 
Tumhara main role hai Abhishek ko uski Class 9 Bihar Board ki padhai me help karna, concepts ko ekdum aasan bhasha (Hinglish/Hindi) me real-life examples ke sath samjhana, aur use motivate rakhna.
Hamesha use 'Chote' ya 'Abhishek bhai' keh kar bulao. Tone friendly, supportive, aur inspiring honi chahiye.
"""

def extract_text(item):
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("text", "")
    if isinstance(item, list):
        return "".join(extract_text(sub) for sub in item)
    return str(item)

def chat_lakshya(message, history):
    formatted_contents = []
    for turn in history:
        if isinstance(turn, dict):
            role = "user" if turn.get("role") == "user" else "model"
            content = extract_text(turn.get("content", ""))
            if content:
                formatted_contents.append(types.Content(role=role, parts=[types.Part.from_text(text=content)]))
        elif isinstance(turn, (list, tuple)) and len(turn) >= 2:
            u_text = extract_text(turn[0])
            m_text = extract_text(turn[1])
            if u_text:
                formatted_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=u_text)]))
            if m_text:
                formatted_contents.append(types.Content(role="model", parts=[types.Part.from_text(text=m_text)]))

    user_msg = extract_text(message)
    formatted_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_msg)]))

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=formatted_contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION
                )
            )
            return response.text
        except Exception as e:
            print("ASLI ERROR:", repr(e))
            if attempt < 2:
                time.sleep(3)
                continue
            return f"Chote, abhi Google server issue hai. (Error: {str(e)[:40]})"

demo = gr.ChatInterface(
    fn=chat_lakshya,
    title="Lakshya Mentor 2.0 🎯",
    description="Tumhare bhaiya ka banaya hua 24/7 personal study companion - Bihar Board Class 9"
)

demo.launch(server_name="0.0.0.0", server_port=7860)
