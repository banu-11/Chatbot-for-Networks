import streamlit as st
import requests
import json
import os
import base64
from dotenv import load_dotenv
load_dotenv()

from datetime import datetime
from fpdf import FPDF

# === CONFIG ===
USER_DATA_FILE = "users.json"
API_KEY = os.getenv("HF_API_KEY", "use-your-own-API-key-here")
MODEL = "HuggingFaceH4/zephyr-7b-beta"

# === SESSION STATE INITIALIZATION ===
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "name_for_bot" not in st.session_state:
    st.session_state.name_for_bot = None
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = None
if "messages" not in st.session_state:
    st.session_state.messages = []

HISTORY_FILE = "chat_history.json"

def load_chat_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_chat_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)


# === STYLING ===
theme_colors = {
    "dark": {
        "bg": "#121212",
        "text": "#f1f1f1",
        "input_bg": "#1e1e1e",
        "accent": "#00b4d8",
        "bubble_user": "#005f73",
        "bubble_bot": "#1a1a1a",
    }
}
colors = theme_colors["dark"]

st.markdown(f"""
    <style>
        body, .stApp {{
            background-color: {colors['bg']} !important;
            color: {colors['text']} !important;
            font-family: 'Segoe UI', sans-serif;
        }}
        .title {{
            font-size: 38px;
            font-weight: 600;
            text-align: center;
            margin-bottom: 30px;
            color: {colors['accent']};
        }}
        .center-box {{
            max-width: 500px;
            margin: auto;
            padding: 30px;
            background: {colors['input_bg']};
            border-radius: 12px;
            box-shadow: 0 0 12px rgba(0,0,0,0.15);
        }}
        input, .stTextInput>div>div>input {{
            background-color: {colors['input_bg']};
            border: 1px solid #888 !important;
            color: {colors['text']} !important;
            border-radius: 8px;
        }}
        .chat-bubble {{
            background-color: {colors['bubble_bot']};
            border-radius: 12px;
            padding: 12px;
            margin: 10px 0;
        }}
        .chat-user {{
            background-color: {colors['bubble_user']};
            border-radius: 12px;
            padding: 12px;
            margin: 10px 0;
            text-align: right;
        }}
        button {{
            background-color: {colors['accent']} !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            padding: 10px 20px;
        }}
        .stRadio > div {{
            justify-content: center;
        }}
    </style>
""", unsafe_allow_html=True)

# === USER FUNCTIONS ===
def load_users():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def register_user(username, password):
    users = load_users()
    if username in users:
        return False
    users[username] = {"password": password}
    save_users(users)
    return True

def validate_user(username, password):
    users = load_users()
    return username in users and users[username]["password"] == password

def reset_password(username, new_password):
    users = load_users()
    if username in users:
        users[username]["password"] = new_password
        save_users(users)
        return True
    return False

# === CHATBOT FUNCTION ===
def generate_response(user_input, image_file=None):
    url = f"https://api-inference.huggingface.co/models/{MODEL}"
    headers = {'Authorization': f'Bearer {API_KEY}'}

    if image_file:
        image_bytes = image_file.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        data = {
            "inputs": {
                "text": user_input,
                "image": image_base64
            },
            "parameters": {
                "max_length": 500,
                "temperature": 0.7,
                "top_p": 0.9
            },
            "options": {"wait_for_model": True}
        }
    else:
        prompt = f"Provide a detailed explanation: {user_input}"
        data = {
            "inputs": prompt,
            "parameters": {
                "max_length": 500,
                "temperature": 0.7,
                "top_p": 0.9
            },
            "options": {"wait_for_model": True}
        }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        try:
            response_data = response.json()
            if isinstance(response_data, list) and response_data:
                result = response_data[0].get("generated_text", "")
                return result.replace(user_input, "").strip()
            return "Unexpected response format."
        except Exception as e:
            return f"Parsing error: {str(e)}"
    return f"API Error: {response.status_code}"

# === PDF GENERATION ===
def generate_chat_pdf(chat_history, chat_name="Chat Summary"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Chat Summary: {chat_name}", ln=True, align='C')
    pdf.ln(10)
    for msg in chat_history:
        role = "User" if msg["role"] == "user" else "Assistant"
        pdf.multi_cell(0, 10, txt=f"{role}: {msg['content']}")
        pdf.ln(1)
    return pdf.output(dest='S').encode('latin1')

# === LOGIN UI ===
def login_signup_ui():
    tab = st.radio("Select Option", ["🔐 Login", "🆕 Sign Up", "❓ Forgot Password"], horizontal=True)
    st.markdown('<div class="center-box">', unsafe_allow_html=True)
    if tab == "🔐 Login":
        uname = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if validate_user(uname, pwd):
                st.session_state.logged_in = True
                st.session_state.username = uname
                st.rerun()
            else:
                st.error("Invalid credentials")
    elif tab == "🆕 Sign Up":
        uname = st.text_input("Choose Username")
        pwd = st.text_input("Create Password", type="password")
        if st.button("Sign Up"):
            if register_user(uname, pwd):
                st.success("Account created! You can now log in.")
            else:
                st.error("Username already exists.")
    elif tab == "❓ Forgot Password":
        uname = st.text_input("Your Username")
        new_pwd = st.text_input("New Password", type="password")
        if st.button("Reset Password"):
            if reset_password(uname, new_pwd):
                st.success("Password updated.")
            else:
                st.error("Username not found.")
    st.markdown('</div>', unsafe_allow_html=True)
# Load chat history for the logged-in user
chat_history = load_chat_history()
username = st.session_state["username"]

if username in chat_history:
    st.session_state.all_chats = chat_history[username]
else:
    st.session_state.all_chats = {"default": []}
st.session_state.current_chat = "default"


# === MAIN INTERFACE ===
st.markdown('<div class="title">💼 SynBot – Network Configuration Assistant</div>', unsafe_allow_html=True)

if not st.session_state.logged_in:
    login_signup_ui()
elif not st.session_state.name_for_bot:
    st.markdown("### 👤 How should I address you?")
    name_input = st.text_input("Preferred Name:")
    if name_input:
        st.session_state.name_for_bot = name_input
        st.rerun()
else:
    # === SIDEBAR CHAT HISTORY ===
    st.sidebar.title("🧠 Chat Memory")
    chat_name = st.sidebar.text_input("📛 Enter chat name:", value="Network Chat")

    if st.sidebar.button("➕ New Chat"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_name = f"{chat_name} - {timestamp}"
        st.session_state.all_chats[full_name] = []
        st.session_state.current_chat = full_name
        st.session_state.messages = []

    st.sidebar.subheader("💾 Saved Chats")
    for name in st.session_state.all_chats:
        if st.sidebar.button(name):
            st.session_state.current_chat = name
            st.session_state.messages = st.session_state.all_chats[name]

    if st.session_state.current_chat:
        st.sidebar.write(f"📝 Current: {st.session_state.current_chat}")

    # === MAIN CHAT UI ===
    st.write(f"**Welcome, {st.session_state.name_for_bot}! Ask me anything about networks.**")
    if st.session_state.messages:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    uploaded_image = st.file_uploader("📷 Optionally upload an image to include with your question:", type=["png", "jpg", "jpeg"])

    if user_input := st.chat_input("Type your question..."):
        with st.chat_message("user"):
            st.markdown(user_input)
            if uploaded_image:
                st.image(uploaded_image, caption="Uploaded Image", use_column_width=True)
        st.session_state.messages.append({"role": "user", "content": user_input})
        

        # Include image in full prompt only for assistant logic
        bot_reply = generate_response(user_input, image_file=uploaded_image)

        with st.chat_message("assistant"):
            st.markdown(bot_reply)
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})

        if st.session_state.current_chat:
             st.session_state.all_chats[st.session_state.current_chat] = st.session_state.messages

    # Save chat history after bot response
    chat_history = load_chat_history()
    chat_history[st.session_state.username] = st.session_state.all_chats
    save_chat_history(chat_history)


    # === DOWNLOAD CHAT AS PDF ===
    st.markdown("---")
    if st.button("📥 Download Chat as PDF"):
        if st.session_state.current_chat and st.session_state.messages:
            pdf_bytes = generate_chat_pdf(st.session_state.messages, st.session_state.current_chat)
            b64 = base64.b64encode(pdf_bytes).decode()
            href = f'<a href="data:application/pdf;base64,{b64}" download="{st.session_state.current_chat}.pdf">Click here to download your chat 📄</a>'
            st.markdown(href, unsafe_allow_html=True)
        else:
            st.warning("No chat messages to export.")

    # === LOGOUT ===
    if st.button("🔒 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.name_for_bot = None
        st.session_state.messages = []
        st.session_state.current_chat = None
        st.rerun()
