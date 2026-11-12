# Temporal Paradox Resolver – Decision‑Archival Agent

**GitHub:** [Anushka180712](https://github.com/Anushka180712)  
A personal “decision time capsule” that records the full context of your choices and, with Google Gemini, shows you “what‑if” timelines, pros‑cons, conclusions and goal‑plans.

---

## ✨  What it does

| Feature | What you get |
|---------|--------------|
| **Decision Capture** | Record the exact choice, the values you ranked, alternatives (with pros/cons), context (time of day, energy, stressors) and optional tags. |
| **Structured Archive** | Every decision is saved immutably in a local SQLite database (`my_decisions.db`). |
| **Alternate‑Timeline Simulation** | Ask “what‑if” questions (“If I had taken the government job instead of the private‑sector role…”) and get a concise, data‑backed narrative from Google Gemini. |
| **Pros‑Cons Generator** | Auto‑create 3 plausible pros and 3 cons for the alternative you *didn’t* choose. |
| **Conclusion Prompt** | A brief 1‑2‑sentence personal recommendation based on your values and the simulated gains/losses. |
| **Goal‑Plan Generator** | Turn your top‑ranked value (e.g., “career growth”) into a concrete 6‑month action plan with 3 monthly milestones. |
| **Motivational Tagline** | A short uplifting tagline prepended to every narrative (e.g., “💡 Remember: every choice teaches you more about what you truly value.”). |
| **Pattern Learning** | Over time the app surfaces which value prioritisations led to satisfaction or burnout. |
| **Privacy‑First** | All data stays on your machine. No external tracking unless you opt‑in to a web‑search API. |
| **Export & Backup** | JSON/CSV export so you can back up or migrate your decision history. |

---

## 🚀  Getting Started (one‑click)

```bash
# 1️⃣  Clone the repo (or download the zip)
git clone https://github.com/Anushka180712/temporal-paradox-resolver.git
cd temporal-paradox-resolver

# 2️⃣  Create a virtual environment
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# Windows PowerShell: .\.venv\Scripts\Activate.ps1

# 3️⃣  Install dependencies
pip install -r requirements.txt    # installs google‑genai, streamlit, etc.

# 4️⃣  Set your Gemini API key
#    • Option A – export in the terminal (for this session only)
export GEMINI_API_KEY='YOUR_GEMINI_API_KEY_HERE'

#    • Option B – add to a .env file (recommended, never committed)
#       Create a file called `.env` in the project root and write:
#       GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
#    • Add `.env` to `.gitignore` so it never gets committed.

# 5️⃣  Launch the Streamlit UI
streamlit run app.py
