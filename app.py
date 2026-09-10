import os
import gradio as gr
from google import genai
from google.genai import types

# API key Render ke Environment Variables se secure load hogi
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

SYSTEM_INSTRUCTION = """
Role & Identity:
Tumhara naam Lakshya Mentor 2.0 hai. Tumhe Abhishek ke bade bhaiya ne banaya hai taaki tum Abhishek ke personal guide, mentor aur ek samajhdaar bade bhai ban kar uski padhai aur daily life ki pareshani ko door kar sako.
Abhishek Bihar Board (BSEB) Class 9 Hindi Medium ka student hai.

Purane Version ka Context:
Pehle wale "Lakshya Mentor" me technical kharabi aur link disconnect hone ki pareshani aa rahi thi, isliye bhaiya ne Abhishek ke liye yeh naya aur behtar "Lakshya Mentor 2.0" banaya hai jo ab 24/7 hamesha bina kisi rukawat ke chalega. Agar Abhishek pooche ya purani baat kare, toh use pyaar se batana ki purane bot me dikkat aa rahi thi isliye bhaiya ne special 2.0 version ready kar diya hai.

Language & Tone:
- Shuddh & Saral Hindi / Hinglish.
- Tone: Bahut supportive, caring, encouraging aur friendly bade bhai jaisi.
- Formatting: Short bullet points, aasan shabdon me explanations, lambe boring paras bilkul nahi.

Emergency Exam Rule:
- 10 din me Class 9 Bihar Board exam hai.
- Top 5 VVI questions aur 2-line direct definitions samjhao.
- Har concept ke baad turant 1 oral question pooch kar test lo.
"""

def chat_lakshya(message, history):
    formatted_contents = []
    for item in history:
        if isinstance(item, dict):
            u_text = item.get("content", "") if item.get("role") == "user" else ""
            m_text = item.get("content", "") if item.get("role") == "assistant" else ""
            if u_text:
                formatted_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=u_text)]))
            if m_text:
                formatted_contents.append(types.Content(role="model", parts=[types.Part.from_text(text=m_text)]))
        elif isinstance(item, (list, tuple)):
            formatted_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=str(item[0]))]))
            formatted_contents.append(types.Content(role="model", parts=[types.Part.from_text(text=str(item[1]))]))

    formatted_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))

    response = client.models.generate_content_stream(
        model="gemini-2.5-flash",
        contents=formatted_contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION
        )
    )

    full_reply = ""
    for chunk in response:
        full_reply += chunk.text
        yield full_reply

demo = gr.ChatInterface(
    fn=chat_lakshya,
    title="Lakshya Mentor 2.0 🎯",
    description="Tumhare bhaiya ka banaya hua 24/7 personal study companion - Bihar Board Class 9"
)

demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
