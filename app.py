import os
import re
import time
import requests
import gradio as gr

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

SYSTEM_INSTRUCTION = """
Tumhara naam Lakshya Mentor 2.0 hai. Tum Abhishek ke personal 24/7 AI study companion aur mentor ho. 
Tumhara main role hai Abhishek ko uski Class 9 Bihar Board ki padhai me help karna, concepts ko ekdum aasan bhasha (Hinglish/Hindi) me samjhana, aur motivate rakhna.
Hamesha use 'Chote' ya 'Abhishek bhai' keh kar bulao. Tone friendly, desi aur supportive honi chahiye.

IMPORTANT FORMATTING RULES:
1. Maths ya Science ke kisi bhi formula ya equation me '$' ya '$$' (LaTeX syntax) bilkul use MAT karna.
2. Har equation ko bilkul normal text ki tarah likho (Jaise: x^2 + 5x + 6 = 0, ya a/b, sqrt(x)).
3. Simple aur saaf readable text hona chahiye.
"""

ENDPOINTS = [
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

    if CIRCUIT_BREAKER["is_open"]:
        elapsed = current_time - CIRCUIT_BREAKER["last_failure_time"]
        if elapsed < CIRCUIT_BREAKER["cooldown_seconds"]:
            remaining = int(CIRCUIT_BREAKER["cooldown_seconds"] - elapsed)
            return f"Chote, Google server abhi thoda garam hai! Bas {remaining} second ruko, fir batata hoon."
        else:
            CIRCUIT_BREAKER["is_open"] = False

    if not API_KEY:
        return "Error: GEMINI_API_KEY Render Environment Variables me nahi mili!"

    user_text = message.get("text", "") if isinstance(message, dict) else str(message)
    if not user_text.strip():
        return "Kuch pucho toh sahi, Chote!"

    prompt = f"System: {SYSTEM_INSTRUCTION}\n\n"
    if history:
        for turn in history:
            if isinstance(turn, (list, tuple)) and len(turn) >= 2:
                u = turn[0].get("text", "") if isinstance(turn[0], dict) else str(turn[0])
                m = turn[1].get("text", "") if isinstance(turn[1], dict) else str(turn[1])
                prompt += f"User: {u}\nAssistant: {m}\n"
            elif isinstance(turn, dict):
                role = "User" if turn.get("role") == "user" else "Assistant"
                c = turn.get("content", "")
                prompt += f"{role}: {c}\n"
    prompt += f"User: {user_text}\nAssistant:"

    last_error = ""

    for model_name in ENDPOINTS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        try:
            res = requests.post(url, json=payload, timeout=25)
            if res.status_code == 200:
                data = res.json()
                reply = data["candidates"][0]["content"]["parts"][0]["text"]
                CIRCUIT_BREAKER["is_open"] = False
                return clean_math_text(reply)
            else:
                last_error = f"HTTP {res.status_code} on {model_name}"
                print(f"FAILED {model_name}: {res.status_code} - {res.text[:100]}", flush=True)
        except Exception as e:
            last_error = f"Exception on {model_name}: {repr(e)[:80]}"
            print(f"ERR {model_name}: {last_error}", flush=True)
            continue

    CIRCUIT_BREAKER["is_open"] = True
    CIRCUIT_BREAKER["last_failure_time"] = time.time()
    return f"Chote, abhi Google server par load zyada hai. (Reason: {last_error})"

demo = gr.ChatInterface(
    fn=chat_lakshya,
    title="Lakshya Mentor 2.0 🎯",
    description="Tumhare bhaiya ka banaya hua 24/7 personal study companion - Bihar Board Class 9"
)

demo.launch(server_name="0.0.0.0", server_port=7860)
                
