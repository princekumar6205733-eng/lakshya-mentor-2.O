import os
import re
import time
import requests
import gradio as gr

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

SYSTEM_INSTRUCTION = (
    "Tumhara naam Lakshya Mentor 2.0 hai. Tum Abhishek ke personal 24/7 AI study companion aur mentor ho. "
    "Class 9 Bihar Board ki padhai aasan bhasha (Hinglish/Hindi) me samjhana aur motivate rakhna tumhara kaam hai. "
    "Abhishek ko hamesha 'Chote' ya 'Abhishek bhai' keh kar bulao. Tone friendly aur desi rakho. "
    "Kewal aur kewal seedha dialogue reply do. Koi thinking, draft ya checklist output me mat likho. "
    "Maths me '$' ka use bilkul mat karna, normal plain text me likho."
)

CIRCUIT_BREAKER = {
    "is_open": False,
    "last_failure_time": 0,
    "cooldown_seconds": 60
}

def clean_mentor_output(text):
    if not text:
        return ""
    # LaTeX stripping
    text = re.sub(r'\${1,2}', '', text)
    
    # Agar output me double quotes me response ho toh seedha wahi uthao
    quoted_matches = re.findall(r'"([^"]{15,})"', text, re.DOTALL)
    if quoted_matches:
        return quoted_matches[-1].strip()

    # Checklist, bullets aur internal monologue ko filter karna
    cleaned_lines = []
    for line in text.split('\n'):
        l = line.strip()
        if l.startswith(('•', '*', '-', 'o ', 'User:', 'Persona:', 'Role:', 'Target', 'Constraint', 'Greeting:', 'Refining', 'Draft')):
            continue
        cleaned_lines.append(line)
        
    res = '\n'.join(cleaned_lines).strip()
    return res if res else text.strip()

def get_available_models():
    """Heavy/Pro/TTS models ko block karke sirf reliable Flash chat models filter karta hai"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    # Hardcoded permanent fallback agar network call miss ho
    fallback_flash = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            valid_models = []
            
            # Heavy aur problematic model keywords
            blocked_keywords = [
                "tts", "audio", "embed", "imagen", "robot", 
                "pro", "ultra", "exp", "vision", "learnlm"
            ]

            for m in data.get("models", []):
                methods = m.get("supportedGenerationMethods", [])
                name = m.get("name", "").replace("models/", "")
                
                # Sirf text generation wale flash models ko permission
                if "generateContent" in methods:
                    if any(bad in name.lower() for bad in blocked_keywords):
                        continue
                    if "flash" in name.lower():
                        valid_models.append(name)
            
            if valid_models:
                print(f"ACTIVE_FLASH_MODELS_LOCKED: {valid_models}", flush=True)
                return valid_models
    except Exception as e:
        print(f"FAILED_FETCHING_MODELS: {repr(e)}", flush=True)
        
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

    # Bulletproof contents formatter for Gemini API (Avoids HTTP 400)
    contents = []
    if history:
        for turn in history:
            u_text, m_text = "", ""
            if isinstance(turn, (list, tuple)) and len(turn) >= 2:
                u_text = turn[0].get("text", "") if isinstance(turn[0], dict) else str(turn[0] or "")
                m_text = turn[1].get("text", "") if isinstance(turn[1], dict) else str(turn[1] or "")
            elif isinstance(turn, dict):
                role = turn.get("role", "")
                text_val = turn.get("content", "")
                if role == "user":
                    u_text = text_val
                else:
                    m_text = text_val

            if u_text.strip():
                contents.append({"role": "user", "parts": [{"text": u_text.strip()}]})
            if m_text.strip():
                contents.append({"role": "model", "parts": [{"text": m_text.strip()}]})

    # Latest user query
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
    

    
