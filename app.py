import os
import re
import time
import requests
import gradio as gr

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

SYSTEM_INSTRUCTION = """
Tumhara naam Lakshya Mentor 2.0 hai. Tum Abhishek ke personal 24/7 AI study companion aur elder brother (bhaiya) mentor ho.
Mission: Abhishek ko Class 9 Bihar Board exam me top karwana.

CORE PERSONA & WORKING RULES:
1. Tone: Friendly, desi, motivating, aur elder brother jaisi. Abhishek ko hamesha 'Chote' ya 'Abhishek bhai' keh kar bulao.
2. 10-DAY BIHAR BOARD EXAM DRILL: Abhishek ko 10-Day Exam Drill ke frame me guide karo (Maths, Science, Social Science, Hindi). Har din targeted revision aur important Bihar Board pattern ke questions par focus hona chahiye.
3. PROACTIVE QUESTIONING: Kabhi bhi sirf answer dekar chat khatam mat karo! Har answer ke aakhir me Abhishek se usi topic par ek chota question ya cross-question pucho taaki wo active rahe aur revision hota rahe.
4. CLEAN OUTPUT: Koi background thinking, draft, checklist ya evaluation text chat me nahi aana chahiye. Seedha final mentor dialogue do.
5. NO LATEX: Formulas me '$' ya '$$' bilkul use mat karna. Plain text me likho (Jaise: x^2 - 9 = 0, a/b, sqrt(x)).
"""

CIRCUIT_BREAKER = {
    "is_open": False,
    "last_failure_time": 0,
    "cooldown_seconds": 60
}

def clean_mentor_output(text):
    if not text:
        return ""
    text = re.sub(r'\${1,2}', '', text)
    
    quoted_matches = re.findall(r'"([^"]{20,})"', text, re.DOTALL)
    if quoted_matches:
        text = quoted_matches[-1]
    else:
        cleaned_lines = []
        for line in text.split('\n'):
            l = line.strip()
            if l.startswith(('•', '*', 'o ', 'Persona:', 'Role:', 'Constraint:', 'Greeting:', 'Refining', 'Draft')):
                continue
            cleaned_lines.append(line)
        text = '\n'.join(cleaned_lines)
        
    return text.strip()

def get_available_models():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    fallback_flash = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            valid_models = []
            blocked = ["tts", "audio", "embed", "imagen", "robot", "pro", "ultra", "exp", "vision"]
            for m in data.get("models", []):
                methods = m.get("supportedGenerationMethods", [])
                name = m.get("name", "").replace("models/", "")
                if "generateContent" in methods:
                    if any(b in name.lower() for b in blocked):
                        continue
                    if "flash" in name.lower():
                        valid_models.append(name)
            if valid_models:
                return valid_models
    except Exception:
        pass
    return fallback_flash

ACTIVE_MODELS = get_available_models()

def chat_lakshya(message, history):
    global ACTIVE_MODELS
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
    user_text = user_text.strip()
    if not user_text:
        return "Kuch pucho toh sahi, Chote!"

    if not ACTIVE_MODELS:
        ACTIVE_MODELS = get_available_models()

    # Gradio to Gemini strictly-alternating history converter
    contents = []
    if history:
        for turn in history:
            if isinstance(turn, dict):
                r = "user" if turn.get("role") == "user" else "model"
                text_content = turn.get("content", "")
                if isinstance(text_content, list):
                    text_content = "".join([part.get("text", "") for part in text_content if isinstance(part, dict)])
                text_content = str(text_content).strip()
                if text_content:
                    if not contents or contents[-1]["role"] != r:
                        contents.append({"role": r, "parts": [{"text": text_content}]})

            elif isinstance(turn, (list, tuple)) and len(turn) >= 2:
                u_text = turn[0].get("text", "") if isinstance(turn[0], dict) else str(turn[0] or "").strip()
                m_text = turn[1].get("text", "") if isinstance(turn[1], dict) else str(turn[1] or "").strip()
                if u_text:
                    if not contents or contents[-1]["role"] != "user":
                        contents.append({"role": "user", "parts": [{"text": u_text}]})
                if m_text:
                    if not contents or contents[-1]["role"] != "model":
                        contents.append({"role": "model", "parts": [{"text": m_text}]})

    if contents and contents[-1]["role"] == "user":
        contents[-1] = {"role": "user", "parts": [{"text": user_text}]}
    else:
        contents.append({"role": "user", "parts": [{"text": user_text}]})

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_INSTRUCTION}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7
        }
    }

    last_error = ""

    for model_name in ACTIVE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
        try:
            res = requests.post(url, json=payload, timeout=25)
            if res.status_code == 200:
                data = res.json()
                reply = data["candidates"][0]["content"]["parts"][0]["text"]
                CIRCUIT_BREAKER["is_open"] = False
                return clean_mentor_output(reply)
            else:
                last_error = f"HTTP {res.status_code} on {model_name}"
                print(f"FAILED {model_name}: {res.status_code} - {res.text[:120]}", flush=True)
        except Exception as e:
            last_error = f"Exception on {model_name}: {repr(e)[:80]}"
            print(f"ERR {model_name}: {last_error}", flush=True)
            continue

    CIRCUIT_BREAKER["is_open"] = True
    CIRCUIT_BREAKER["last_failure_time"] = time.time()
    return f"Chote, Google server ne mana kiya. (Reason: {last_error})"

demo = gr.ChatInterface(
    fn=chat_lakshya,
    title="Lakshya Mentor 2.0 🎯",
    description="Tumhare bhaiya ka banaya hua 24/7 personal study companion - Bihar Board Class 9"
)

demo.launch(server_name="0.0.0.0", server_port=7860)

