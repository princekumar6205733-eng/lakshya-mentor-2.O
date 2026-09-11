import os
import re
import time
from google import genai
from google.genai import types
import gradio as gr

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

SYSTEM_INSTRUCTION = """
Tumhara naam Lakshya Mentor 2.0 hai. Tum Abhishek ke personal 24/7 AI study companion aur mentor ho. 
Tumhara main role hai Abhishek ko uski Class 9 Bihar Board ki padhai me help karna, concepts ko ekdum aasan bhasha (Hinglish/Hindi) me samjhana, aur motivate rakhna.
Hamesha use 'Chote' ya 'Abhishek bhai' keh kar bulao. Tone friendly, desi aur supportive honi chahiye.

IMPORTANT FORMATTING RULES:
1. Maths ya Science ke kisi bhi formula ya equation me '$' ya '$$' (LaTeX syntax) bilkul use MAT karna.
2. Har equation ko bilkul normal text ki tarah likho (Jaise: x^2 + 5x + 6 = 0, ya a/b, sqrt(x)).
3. Simple aur saaf readable text hona chahiye.
"""

# Stable models sequence
MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

CIRCUIT_BREAKER = {
    "is_open": False,
    "last_failure_time": 0,
    "cooldown_seconds": 60
}

def clean_math_text(text):
    if not text:
        return ""
    return re.sub(r'\${1,2}', '', text).strip()

def chat_lakshya(message, history):
    current_time = time.time()

    # Cooldown check
    if CIRCUIT_BREAKER["is_open"]:
        elapsed = current_time - CIRCUIT_BREAKER["last_failure_time"]
        if elapsed < CIRCUIT_BREAKER["cooldown_seconds"]:
            remaining = int(CIRCUIT_BREAKER["cooldown_seconds"] - elapsed)
            return f"Chote, Google server abhi thoda garam hai! Bas {remaining} second ruko, fir batata hoon."
        else:
            CIRCUIT_BREAKER["is_open"] = False

    user_text = message.get("text", "") if isinstance(message, dict) else str(message)
    if not user_text.strip():
        return "Kuch pucho toh sahi, Chote!"

    # Gradio history ko GenAI Contents format me cleanly convert karna
    contents = []
    if history:
        for turn in history:
            try:
                if isinstance(turn, (list, tuple)) and len(turn) >= 2:
                    u = turn[0].get("text", "") if isinstance(turn[0], dict) else str(turn[0])
                    m = turn[1].get("text", "") if isinstance(turn[1], dict) else str(turn[1])
                    if u:
                        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=u)]))
                    if m:
                        contents.append(types.Content(role="model", parts=[types.Part.from_text(text=m)]))
                elif isinstance(turn, dict):
                    role = "user" if turn.get("role") == "user" else "model"
                    c = turn.get("content", "")
                    if c:
                        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=str(c))]))
            except Exception:
                continue

    # Latest user query add karo
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))

    for model_name in MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION
                )
            )
            if response and response.text:
                CIRCUIT_BREAKER["is_open"] = False
                return clean_math_text(response.text)
        except Exception as e:
            print(f"Error on {model_name}: {repr(e)}")
            continue

    CIRCUIT_BREAKER["is_open"] = True
    CIRCUIT_BREAKER["last_failure_time"] = time.time()
    return "Chote, abhi Google server par load zyada hai. Circuit protection active hai, 1 minute ruk kar fir se pucho!"

demo = gr.ChatInterface(
    fn=chat_lakshya,
    title="Lakshya Mentor 2.0 🎯",
    description="Tumhare bhaiya ka banaya hua 24/7 personal study companion - Bihar Board Class 9"
)

demo.launch(server_name="0.0.0.0", server_port=7860)

                
