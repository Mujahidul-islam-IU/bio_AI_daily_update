# BioAI Daily Update 🧬🤖

A high-performance, AI-driven research dashboard that monitors the latest innovations in **Bioinformatics** (Single-cell, Cancer) and **Artificial Intelligence** (LLMs, GNNs) in real-time.

## 🚀 Key Features

- **Multi-Source Research Fetching**: Automatically parses the latest papers from **arXiv**, **PubMed**, **bioRxiv**, and **Crossref / Top Journals**.
- **Context-Aware AI Chat**: Click "💬 Ask AI" on any paper to start a deep-dive conversation about its contents using **Groq (Llama 3.3)**. Chat sessions are persisted.
- **Dynamic Research Topics**: Users can specify custom AI and Bio topics (e.g., "Alzheimer's", "Ollama", "GNNs") for targeted research.
- **Overarching Gap Analysis**: Analyzes all fetched papers collectively to identify the "Missing Link" and overarching technology gaps in the field.
- **Web Insights Synthesis**: A dedicated "Synthesize Trends" engine to summarize the absolute latest innovations from the live web using Tavily.
- **Relevancy Scoring**: Live 0-100% keyword density match calculation to ensure search precision.
- **Research Hub**: Full history timeline to review past sessions, paper bookmarking, and one-click Export to Markdown functionalites.
- **SQLite Persistence**: All research history, bookmarks, and AI insights are securely stored in a local database.
- **Premium UI**: Modern, glassmorphic dark/light mode dashboard with vanilla CSS micro-animations.

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **AI Brain**: Groq Cloud SDK (Llama-3.3-70b-versatile)
- **Web Search API**: Tavily Search API
- **Database**: SQLAlchemy + SQLite
- **Frontend**: Vanilla HTML5, CSS3 (Glassmorphism), and JavaScript (ES6)
- **Research APIs**: arXiv API, Entrez (PubMed) E-utilities, bioRxiv API, Crossref API

## ⚙️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Mujahidul-islam-IU/bio_AI_daily_update.git
cd bio_AI_daily_update
```

### 2. Configure Environment Variables
Copy the `.env.example` file to create a `.env` file in the `backend/` directory and add your API keys:
```bash
cp backend/.env.example backend/.env
```
Inside `.env`, insert your keys:
```env
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

### 3. Run the Backend
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 4. Run the Frontend
```bash
cd ../frontend
# Any static local server will work
python -m http.server 8080
```
Visit **http://localhost:8080** in your browser.

## 📄 License
This project is licensed under the MIT License.
