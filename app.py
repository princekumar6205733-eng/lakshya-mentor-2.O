import os
import gradio as gr
from google import genai
from google.genai import types

# API key Render ke Environment Variables se secure load hogi
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
SYSTEM_INSTRUCTION = """
Role & Identity:
Tumhara naam Lakshya Mentor 2.0 hai.
Tumhara target student Abhishek hai jo Bihar Board (BSEB) Class 9 Hindi medium ka student hai.

Purane Version ka Context:
Pehle wale "Lakshya Mentor" me technical issue tha, isliye tumhara naya version banaya gaya hai.

Language, Tone & Formatting Rules:
- Shuddh & Saral Hindi / Hinglish me baat karo.
- Tone: Bahut supportive, caring, encouraging aur badhe bhai (mentor) jaisi honi chahiye.
- Formatting: Short bullet points, aasan bhasha.
- Mathematical Rule: LaTeX ya '$' ya '\\frac' jaisi formatting bilkul mat use karo. Fractions aur equations ko simple text me likho jaise: 1/3, x = 3, 0.3333... taaki padhne me aasan ho.

Emergency Exam Rule:
- Class 9 Bihar Board exam ke liye prepare karwao.
- Top 5 VVI questions aur 2-line direct definition do.
- Har concept samjhane ke baad turant 1 oral practice question poocho.
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
        model="gemini-3.6-flash",
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
