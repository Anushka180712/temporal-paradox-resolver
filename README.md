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

##Architecture

flowchart TD
    A[User] -->|Sidebar form| B[Capture Decision]
    B --> C[SQLite DB (my_decisions.db)]
    C --> D[Store (Python)]
    D -->|LLM Call| E[Google Gemini (gemini‑3.5‑flash)]
    E -->|Narrative| F[Streamlit UI]
    F -->|User question| D
    F -->|Feature buttons (Pros‑Cons, Conclusion, Goal‑Plan)| D
    G[Optional Web‑Search API] -->|Keywords| H[search_alternatives() function]
    H -->|Results| F

##Input Guide – Where & What to Type

Sidebar – “Capture a New Decision”
Choice description – The exact words you used when making the decision.
Example: "I accepted the software‑engineer offer at Company X."

Values you're ranking – One value per line (the criteria that matter most).
Example:
financial security
work‑life balance
location

Alternatives considered – For each option: name on its own line, then pros (one per line), then cons (one per line). Separate each alternative with a blank line.
Example:
Job A (high salary, long commute)
high salary
long commute

Job B (remote, lower salary)
remote
lower salary
Time of day – Dropdown: morning, afternoon, evening (default: evening).
Energy level – Slider from 1 to 10 (default: 6).
Stressors – Comma‑separated list of external pressures (optional).
Example: deadline pressure, family visiting
Notes – Free‑form anything you want to remember.
Tags – Keywords to help you find the decision later (comma‑separated).
Example: career,2024,major
Main – “Ask a What‑If Question”
This box appears below your selected decision in the content area.
What to type: A natural‑language question about the decision you just expanded.
Copy‑paste any of these examples:
If I had taken the government job instead of the private‑sector role, where would I be living today?
What are the pros and cons of choosing a government job over a private‑sector job, given my values of financial security and work‑life balance?
Give me a 1‑2 sentence conclusion about staying vs switching.
Create a 6‑month goal plan for me if I decide to switch to a government job, focusing on the top‑ranked value "career growth".
Press Generate Timeline and the app will send your query to Google Gemini.
Sidebar – “Search Alternatives” (optional)
What to type: Keywords describing the kind of alternatives you’re curious about.
Example: government jobs remote work / software engineering jobs work‑life balance / project manager roles non‑profit
Click Search – currently shows a placeholder message; connect a Google Custom Search API to get real results.
Example output format (once wired):
🔎 Search results for **government jobs remote work**
**1. Remote Government Analyst** – https://example.com/job1
• Analyze policies from home, flexible schedule, …


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

