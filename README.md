# NovaAI — Fully Intelligent General-Purpose AI Chatbot

NovaAI is a production-grade, general-purpose conversational AI web application modeled after ChatGPT. Powered by **Google Gemini** as its default Large Language Model (with **OpenAI** and **Groq** support), it features real-time token streaming, multi-turn conversation memory, and an elegant, responsive interface built with **HTML5, CSS3, Vanilla JavaScript, Python Flask, and SQLAlchemy ORM**.

---

## 🌟 Key Upgrades & Capabilities

### 1. Real Large Language Model (LLM) Engine
- **Default Provider**: **Google Gemini (`gemini-3.5-flash`)** directly integrated via official `google-genai` SDK.
- **Alternative Providers**: **OpenAI (`gpt-4o-mini`)** and **Groq Cloud (`llama-3.3-70b-versatile`)**.
- **No Rule-Based Limitations**: Every single prompt is passed to the real LLM. No hardcoded responses, keyword matching, or restricted FAQ databases.
- **Clear Error Messaging**: If an API key is missing or invalid, NovaAI displays a clear, actionable guide with links to get a key, rather than pretending to generate answers.

### 2. Multi-Turn Conversation Memory
- Full contextual awareness across turns in a conversation.
- Remembers previous user messages and assistant responses (e.g. asking *"What is Python?"* followed by *"Who created it?"* followed by *"Explain its advantages in Hindi"* maintains continuous context).
- Roles are strictly sanitized and ordered chronologically for LLM compliance.

### 3. General-Purpose Question Handling
NovaAI handles any question or task, including:
- **General Knowledge & Science**: Quantum physics, astronomy, history, geography, biology.
- **Programming & Web Development**: Python, JavaScript, HTML, CSS, SQL, Java, React, MERN stack, debugging, algorithms, and system architecture.
- **Mathematics & Logic**: Mathematical derivations, calculus, statistics, logic puzzles.
- **Language Adaptability**: Full native multilingual support, including English, Hindi, Hinglish, Spanish, French, and more. Matches the language of the prompt automatically.
- **Professional & Creative Writing**: Resume review, cover letters, formal emails, essays, stories, brainstorms, and business proposals.

### 4. ChatGPT-Like Real-Time Streaming
- Real-time token streaming via **Server-Sent Events (SSE)** at `/api/chat/send-stream`.
- **Stop Generation**: The send button dynamically switches to a stop square button during generation, allowing users to abort the stream at any moment.
- Live markdown formatting and Prism.js syntax highlighting while streaming.

### 5. UI/UX Architecture
- **Chronological History Grouping**: Today, Yesterday, Previous 7 Days, Older.
- **Inline Renaming**: Double-click or click the edit icon to rename conversations directly.
- **Search Conversations**: Live search filtering by title and content.
- **Markdown & Code Blocks**: Clean syntax highlighting with a one-click **Copy code** button.
- **Message Actions**: Copy response, regenerate answer, thumbs up/down feedback.
- **Export Chat**: Download active conversation as a `.md` Markdown file.
- **Theme Controller**: Seamless Dark and Light mode toggle with `localStorage` persistence.

---

## 📁 Directory Structure

```
chatbott/
├── app.py                     # Flask application entry point & WSGI factory
├── config.py                  # Environment configuration & system prompt
├── models.py                  # SQLAlchemy models (User, Conversation, Message, Feedback)
├── seed.py                    # Seeding utility for demo account & initial threads
├── test_suite.py              # Automated 8-point integration test suite
├── requirements.txt           # Python dependencies
├── .env.example               # Template environment configuration
├── .env                       # Active environment configuration
├── README.md                  # System documentation
├── routes/
│   ├── __init__.py            # Blueprint index
│   ├── auth.py                # Authentication, profile, and settings
│   ├── chat.py                # Send (streaming & standard), regenerate, feedback
│   └── conversations.py       # CRUD and live search for conversations
├── services/
│   ├── __init__.py            # Services package
│   └── ai_service.py          # Modular Real LLM Engine (Gemini, OpenAI, Groq)
├── templates/
│   ├── base.html              # Core HTML5 layout with CDN libraries
│   ├── index.html             # ChatGPT workspace, sidebar, welcome cards
│   ├── login.html             # Authentication login card
│   ├── signup.html            # Registration card
│   └── settings.html          # Profile settings & danger zone
└── static/
    ├── css/
    │   ├── style.css          # Main app layout, bubbles, code blocks, dark/light
    │   └── auth.css           # Auth forms & settings styles
    ├── js/
    │   ├── theme.js           # Theme switcher
    │   ├── chat.js            # Markdown parser, code copy, actions, auto-scroll
    │   └── app.js             # Real-time SSE streaming, state & sidebar manager
    └── images/
        └── logo.svg           # Vector app badge
```

---

## ⚙️ Setup & Configuration

### 1. Virtual Environment & Dependencies

```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Your AI API Key

Open `.env` in the root folder:

```ini
# Choose active provider: 'gemini' (default), 'openai', or 'groq'
AI_PROVIDER=gemini

# 1. Google Gemini API (Recommended)
# Get your free key at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-3.5-flash

# 2. OpenAI API
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini

# 3. Groq API
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
```

### 3. Run Automated Tests

Verify that all 8 core subsystems are functioning:

```powershell
python test_suite.py
```

### 4. Run the Application

```powershell
python app.py
```

Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🚀 Deploy to Vercel

NovaAI is pre-configured for zero-configuration serverless deployment on [Vercel](https://vercel.com/) via `vercel.json` and `api/index.py`.

### 1-Click Deploy
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fparulsaini059-bot%2Fchatbott&env=GEMINI_API_KEY,SECRET_KEY,GEMINI_MODEL&envDescription=API%20keys%20and%20secrets%20for%20NovaAI&project-name=chatbott&repository-name=chatbott)

### Manual Steps on Vercel Dashboard:
1. Go to [vercel.com/new](https://vercel.com/new).
2. Select your imported GitHub repository **`parulsaini059-bot/chatbott`**.
3. Under **Environment Variables**, add:
   - `GEMINI_API_KEY` = your Gemini API key
   - `SECRET_KEY` = any random secure string
   - `GEMINI_MODEL` = `gemini-3.5-flash`
4. Click **Deploy**. Vercel will install dependencies from `requirements.txt` and launch your live URL!

---

## 📜 System Prompt

NovaAI operates under the following general-purpose system instruction:

> *"You are NovaAI, an advanced, intelligent, friendly, and highly capable general-purpose AI assistant. You can discuss virtually any subject and help users with questions, explanations, calculations, coding, education, writing, reasoning, and everyday tasks. You must understand the user’s intent rather than simply matching keywords. Always generate responses using your actual language model capabilities. Be conversational, accurate, helpful, and context-aware. Adapt your response language to the user’s language. Do not restrict yourself to a predefined FAQ database. Never generate generic filler content. If you do not know something, be transparent. Your goal is to provide a ChatGPT-like conversational experience."*
