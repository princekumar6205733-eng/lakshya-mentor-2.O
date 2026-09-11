import os
import time
from google import genai
from google.genai import types
import gradio as gr

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

SYSTEM_INSTRUCTION = """
Tumhara naam Lakshya Mentor 2.0 hai. Tum Abhishek ke personal 24/7 AI study companion aur mentor ho. 
Tumhara main role hai Abhishek ko uski Class 9 Bihar Board ki padhai me help karna, concepts ko ekdum aasan bhasha (Hinglish/Hindi) me samjhana, aur motivate rakhna.
Hamesha use 'Chote' ya 'Abhishek bhai' keh kar bulao. Tone friendly aur supportive honi chahiye.
"""

# Quota issue se bachne ke liye available free models ka sequence
MODELS_TO_TRY = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

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

    # Ek ek karke model try karega agar 429 aaye
    for model_name in MODELS_TO_TRY:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=formatted_contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION
                )
            )
            return response.text
        except Exception as e:
            print(f"Failed with {model_name}: {repr(e)}")
            continue

    return "Chote, abhi Google server par load zyada hai. Bas 1 minute ruk kar fir se pucho!"

demo = gr.ChatInterface(
    fn=chat_lakshya,
    title="Lakshya Mentor 2.0 🎯",
    description="Tumhare bhaiya ka banaya hua 24/7 personal study companion - Bihar Board Class 9"
)

demo.launch(server_name="0.0.0.0", server_port=7860)

