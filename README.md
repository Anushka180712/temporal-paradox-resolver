# Temporal Paradox Resolver — Decision‑Archival Agent

**Your personal "decision time capsule."** Archive the full context of major life choices today, and query them years later to see plausible alternate timelines — complete with gains, losses, and learned patterns.

---

## 🤔 The Problem

Humans are notoriously bad at remembering *why* we made past decisions. Within 2 years, most people forget:

- The specific values they ranked
- The alternatives they weighed
- The trade‑offs they considered
- The emotional state and timing of the choice

The result? We re‑argue the same trade‑offs, carry unresolved regret, and repeat mistakes — all while *confident* we already know the answer.

This agent solves that by creating a permanent, structured archive of every major decision, and using LLMs to reconstruct plausible "what‑if" timelines on demand.

---

## ✨ Key Features

| Feature | What It Does |
|---|---|
| **Decision Capture** | Prompt you at the moment of a big choice: exact wording, values ranked, alternatives considered (with pros/cons), time‑of‑day, context notes, tags. Records are stored as immutable JSON in SQLite (or PostgreSQL). |
| **Structured Archive** | Every decision gets a UUID, timestamp, values, alternatives, context, notes, and tags. Data lives locally by default; optionally cloud‑hosted. |
| **Alternate‑Timeline Simulation** | Ask natural‑language "what‑if" queries ("If I’d taken Job B instead of Job A, where would I be today?") and get a synthesized, data‑backed narrative from the LLM. |
| **Pros‑Cons Generator** | After a decision is captured, the LLM automatically creates 3 plausible pros and 3 cons for the alternative *not* chosen, grounded in your ranked values and context. |
| **Conclusion Prompt** | The LLM writes a brief 1‑2‑sentence personal recommendation based on your values and the simulated gains/losses, helping you reflect and reach a conclusion. |
| **Goal‑Plan Generator** | Translate your top‑ranked value (e.g., "career growth") into a concrete 6‑month action plan with 3 monthly milestones, turning abstract priorities into trackable steps. |
| **Motivational Tagline** | A short uplifting tagline is prepended to every simulation narrative (e.g., "💡 Remember: every choice teaches you more about what you truly value."). |
| **Pattern Learning** | Over time, the agent surfaces patterns: which value prioritizations led to satisfaction, which to burnout, etc. |
| **Privacy‑First** | All data lives locally (or your chosen cloud); no external tracking unless you opt‑in. |
| **Export & Backup** | JSON/CSV export, optional encrypted backup. |
| **Web UI (Streamlit)** | Beautiful, responsive web interface for capturing decisions, viewing your history, and running what‑if queries without touching the CLI. |
| **CLI** | Full command‑line interface for capturing decisions and running simulations programmatically. |

---

## 🏗️ Architecture Overview

```text
┌─────────────────────┐     ┌─────────────────────┐
│   Decision Capture   │──►│   Storage Layer      │
│ (CLI or Web Form)    │     │ (SQLite / Postgres)  │
└─────────────────────┘     └─────────────────────┘
           │                          │
           ▼                          ▼
      ┌─────────────────┐      ┌─────────────────┐
      │   Simulation    │◄────▶│   Query Interface│
      │   Engine (LLM)  │      │ (Natural‑lang)  │
      └─────────────────┘      └─────────────────┘
```

### Data Flow

1. **Decision Capture** → user fills form → `DecisionRecord` JSON → stored in SQLite.
2. **Simulation Engine** → LLM prompt (`simulate_alternative`) → narrative string.
3. **Additional Feature Hooks** → `generate_pros_cons`, `generate_conclusion`, `generate_goal_plan`, `add_motivational_tagline` all receive the same `DecisionRecord` and optional narrative, call the LLM with specialized prompts, and return structured text.
4. **Query Interface** → natural‑language parser (`query.py`) decides which feature to invoke, fetches the record, and returns the result.

### Technology Stack

| Layer | Recommendation |
|---|---|
| **Language** | Python 3.10+ |
| **CLI** | Typer‑based (`main.py`) |
| **Web UI** | Streamlit (`app.py`) — optional, `pip install streamlit` |
| **Database** | SQLite for MVP → PostgreSQL for multi‑user scale |
| **LLM API** | Google Gemini `gemini-3.5-flash` (primary) |
| **Packaging` | `requirements.txt`, optional `Dockerfile` |
| **Testing** | `pytest` + simple integration tests |

---

## 📂 Repo Structure — What Each File Is For

```
temporal-paradox-resolver/
├─ __init__.py           # Package marker — makes this a Python package
├─ main.py               # CLI entry point — runs the interactive capture flow
├─ capture.py            # Interactive CLI prompt for decision capture (step‑by‑step)
├─ store.py              # SQLite wrapper — add / get / list records
├─ models.py             # DecisionRecord dataclass + serialization (to/from dict)
├─ simulate.py           # LLM simulation + pros‑cons / conclusion / goal‑plan / tagline
├─ query.py              # Natural‑language question parser & orchestrator
├─ app.py                # Streamlit web UI (capture + queries + new features)
├─ requirements.txt      # Python dependencies (google-genai, streamlit, etc.)
├─ .env.example          # Template for GEMINI_API_KEY
├─ README.md             # This file — comprehensive guide
└─ ARCHITECTURE.md       # Detailed architecture note (overview + component desciptions)
```

### Quick File Reference

| File | Purpose |
|---|---|
| `__init__.py` | Makes `temporal_paradox_resolver` a importable Python package. |
| `main.py` | Entry point for CLI: `python main.py` starts the capture workflow. |
| `capture.py` | Interactive CLI prompt that walks you through capturing a decision. |
| `store.py` | SQLite backend — persists decisions immutably, provides `add()`, `get()`, `list_all()`. |
| `models.py` | `DecisionRecord` dataclass — defines the schema of a captured decision. |
| `simulate.py` | Core LLM engine: `simulate_alternative()`, `generate_pros_cons()`, `generate_conclusion()`, `generate_goal_plan()`, `add_motivational_tagline()`. |
| `query.py` | Parses natural‑language "what‑if" questions, extracts record IDs and alternate names, delegates to the simulation engine. |
| `app.py` | Streamlit web UI — sidebar form for capture, decision list, what‑if query box, and feature buttons. |
| `requirements.txt` | pip‑installable dependencies. |
| `.env.example` | Copy to `.env` and add your `GEMINI_API_KEY=...`. |
| `ARCHITECTURE.md` | Detailed architectural diagrams and component descriptions (for developers). |
| `README.md` | This guide — what the project does, how to use it, and what makes it intriguing. |

---

## 🚀 Getting Started — Quick & Easy

### 1. Clone the repo

```bash
git clone https://github.com/your-handle/temporal-paradox-resolver.git
cd temporal-paradox-resolver
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

**`requirements.txt` contents:**

```
# Core dependencies
google-genai>=0.8.0
streamlit>=1.35.0   # optional, for web UI

# Optional, if you want easier .env handling
python-dotenv>=1.0.0
```

### 4. Set up your Gemini API key

Copy the example env file and add your key:

```bash
cp .env.example .env
```

Edit `.env` (or export in your shell):

```bash
export GEMINI_API_KEY='AQ.Ab8RN6IAx3sl1y5JK7Eqf5Vp3EGf3ki9VhgAwUlNKY7JR87PHg'
```

You can also place the line `GEMINI_API_KEY=YOUR_KEY_HERE` directly in `.env`; the code reads `os.getenv("GEMINI_API_KEY")`.

### 5. Run the agent

#### CLI — capture a decision

```bash
python main.py
```

You'll be prompted step‑by‑step for choice description, values, alternatives, context, notes, and tags. The record is saved to `my_decisions.db` (SQLite) in the project root.

#### CLI — simulate an alternate timeline

After a decision is captured, you can ask the LLM for a narrative:

```bash
python3 -m temporal_paradox_resolver.simulate <record-id> "Alternative Name"
```

e.g.:

```bash
python3 -m temporal_paradox_resolver.simulate 4ad4b13d-78c1-4144-971c-adfe3e74b792 "Stay in current role"
```

The script will output the ~150‑word "what‑if" narrative.

#### Streamlit Web UI (optional, recommended for first‑time users)

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser. The UI features:

- **Sidebar form** to capture a new decision.
- **Decision list** view — click any decision to query it.
- **What‑if query box** — type a natural‑language question (e.g., "If I had chosen the other option, where would I be today?").
- **Three feature buttons** per decision:
  - **Generate Pros‑Cons** – LLM creates 3 pros and 3 cons for the alternative not chosen.
  - **Get Conclusion** – LLM gives a 1‑2‑sentence personal recommendation.
  - **Create Goal Plan** – LLM produces a 6‑month action plan with 3 monthly milestones based on your top‑ranked value.
- **Motivational tagline** is automatically shown at the top of every narrative.

---

## 🎛️ Using the Features — Step‑by‑Step

### 1. Capture a Decision

**CLI:**

```bash
python main.py
```

Follow the prompts: choice, values (one per line), alternatives (name, pros, cons), context (time of day, energy level, stressors), notes, tags.

**Web UI:**

Go to the sidebar form, fill in the fields, and click **Save Decision**. A UUID is generated and stored in SQLite.

### 2. Generate an Alternate‑Timeline Narrative

**CLI:**

```bash
python3 -m temporal_paradox_resolver.simulate <record-id> "Alternative Name"
```

**Web UI:**

- Select a decision from the list.
- Type your question in the "What‑if query" box (or use the default "the other option").
- Click **Generate Timeline**.
- The narrative appears below, with a motivational tagline prepended.

### 3. Generate Pros‑Cons for the Alternative Not Chosen

**CLI:**

```python
from temporal_paradox_resolver.simulate import generate_pros_cons
from temporal_paradox_resolver.store import DecisionStore

store = DecisionStore(db_path="my_decisions.db")
record = store.get("<your-uuid>")
pros_cons = generate_pros_cons(record, "the other option")
if pros_cons:
    print(pros_cons)
store.close()
```

**Output format:**

```
Pros:
- <pro 1>
- <pro 2>
- <pro 3>

Cons:
- <con 1>
- <con 2>
- <con 3>
```

**Web UI:**

- After viewing a narrative, click the **Generate Pros‑Cons** button.
- The result appears in an expandable section.

### 4. Get a Personal Conclusion

**CLI:**

```python
from temporal_paradox_resolver.simulate import generate_conclusion

narrative = """If you had chosen Job B, you would today be working remotely…
* Primary Gain: …
* Primary Trade‑off: …
* Value Alignment: …
"""
rec = store.get("<uuid>")
rec_conclusion = generate_conclusion(rec, narrative)
if rec_conclusion:
    print("Conclusion:", rec_conclusion)
```

**Output:** a brief 1‑2‑sentence recommendation, e.g.:

> "Given that financial security is your top value, the stable salary of Job A may provide longer‑term peace of mind, but if career growth is equally important, mixing a side‑project with the new role could balance both."

**Web UI:**

- Click **Get Conclusion** after a narrative is generated.

### 5. Create a 6‑Month Goal Plan

**CLI:**

```python
from temporal_paradox_resolver.simulate import generate_goal_plan

rec = store.get("<uuid>")
plan = generate_goal_plan(rec, top_value="career growth", horizon_months=6, num_milestones=3)
if plan:
    print(plan)
```

**Output format:**

```
Month 1: Enroll in an online course on data structures (5 hours/week).
Month 2: Complete a small personal project using the new skills (10 hours total).
Month 3: Update your résumé and apply for one internal transfer opportunity.
```

**Web UI:**

- Click **Create Goal Plan** after a narrative is generated.

### 6. View the Motivational Tagline

Taglines are automatically prepended to every narrative. If you want to see it separately:

```python
from temporal_paradox_resolver.simulate import add_motivational_tagline, simulate_alternative

narrative = simulate_alternative(rec, "Job B (remote, lower salary)")
tagged = add_motivational_tagline(narrative)
print(tagged)
```

**Output:**

```
💡 Remember: every choice teaches you more about what you truly value.

If you had chosen Job B, you would today be working remotely from home…
```

**Web UI:**

- The tagline appears automatically at the top of every narrative.

---

## 💡 Sample Queries & Use Cases

| Query Type | Example | What You'll Get |
|---|---|---|
| **Alternate timeline** | "If I had taken the remote job instead of the office job, where would I be living today?" | A 150‑word narrative describing likely location, job, gains, losses, and value alignment. |
| **Pros‑cons** | "What are the pros and cons of the path I didn't choose?" | Formatted block with 3 pros and 3 cons, grounded in your values. |
| **Conclusion** | "Given my values and the alternate outcome, what should I take away?" | A 1‑2‑sentence uplifting recommendation. |
| **Goal plan** | "What should I do in the next 6 months based on my top value?" | A 3‑month milestone plan (by default 6 months, 3 milestones). |
| **Pattern query** | "Which decisions where I ranked 'financial security' highest turned out well?" | (Future feature — the agent can aggregate your decision history.) |

### Example: Full CLI Session

```bash
$ python main.py

=== Capture a New Decision ===

Describe the decision you're making (your exact words): I'm deciding between Job A (high salary, long commute) and Job B (lower salary, remote).

Values you're ranking (type one per line, press Enter twice when done):
> financial security
> work-life balance
> location

Alternatives considered (for each: name, then pros, then cons, each section terminated by an empty line):
  Alternative name (or leave blank to finish): Job A
    Pros (one per line, empty line when done):
      high salary
    Cons (one per line, empty line when done):
      long commute

  Alternative name (or leave blank to finish): Job B
    Pros (one per line, empty line when done):
      remote
    Cons (one per line, empty line when done):
      lower salary

Context (press Enter after each, or type 'skip' to move on):
  Time of day (morning/afternoon/evening): evening
  Energy level (1-10): 6
  Stressors (comma-separated, or skip): burnout at current role

  Any additional notes (free‑form): Feeling burnt out and undervalued.

  Tags (comma-separated, e.g., career,2024,major): career,2024,major

✅ Decision captured and saved (ID: 4ad4b13d-78c1-4144-971c-adfe3e74b792…)

$ python3 -m temporal_paradox_resolver.simulate 4ad4b13d-78c1-4144-971c-adfe3e74b792 "Job B (remote, lower salary)"

=== Narrative ===

You likely would have kept your current city, avoided the daily 2‑hour commute, and had more evenings free. However, you would have had about $12k less annual income, which may have slowed your apartment‑down‑payment progress. Since 'financial security' was your top‑ranked value, you might have felt a moderate trade‑off: more time vs. less margin.

$ python3 -m temporal_paradox_resolver.simulate 4ad4b13d-78c1-4144-971c-adfe3e74b792 "Job B (remote, lower salary)"

Pros:
- More free time in the evenings
- No daily commute stress
- Greater flexibility to relocate

Cons:
- ~$12k less annual income
- Slower progress on apartment down‑payment
- Potential career ceiling in the new role

$ python3 -c "
from temporal_paradox_resolver.simulate import generate_conclusion
narrative = '''You likely would have kept your current city...'''
from temporal_paradox_resolver.store import DecisionStore
store = DecisionStore(db_path='my_decisions.db')
rec = store.get('4ad4b13d-78c1-4144-971c-adfe3e74b792')
print('Conclusion:', generate_conclusion(rec, narrative))
"
Conclusion: Given that financial security is your top value, the stable salary of Job A may provide longer‑term peace of mind, but if career growth is equally important, mixing a side‑project with the new role could balance both.
```

---

## 🌟 What Makes This Intriguing?

| Aspect | Why It's Cool |
|---|---|
| **Personalized LLM simulations** | The narratives are grounded in *your* actual data (your values, your alternatives), not generic AI advice. |
| **Decision‑time capsule** | Preserve the *why* behind your choices forever — rediscover them years later with fresh eyes. |
| **Multiple “what‑if” angles** | One decision → pros‑cons, conclusion, goal plan, and full narrative — all from the same data. |
| **Privacy‑first design** | Everything stays on your machine by default. No data leaves your control unless you explicitly enable API calls. |
| **CLI + Web UI** | Choose your interaction style: quick CLI commands or a beautiful, responsive Streamlit interface. |
| **Extensible architecture** | Swap SQLite for PostgreSQL, Gemini for Claude or local Llama — the modular design lets you grow into whatever you need. |
| **Pattern learning** | Over time, the agent can surface insights like "When I rank creativity #1, I'm satisfied 80% of the time after 6 months." (Roadmap.) |
| **Export & backup** | Pull your full decision history as JSON/CSV and archive it however you like. |
| **Goal‑oriented** | Turn abstract values into concrete, trackable action plans — not just reflection, but forward motion. |

---

## 🛣️ Roadmap (Next Steps)

1. **MVP** — decision capture + SQLite storage + CLI query (already functional).
2. **LLM Integration** — Google Gemini `gemini-3.5-flash` for simulation, pros‑cons, conclusion, goal‑plan.
3. **Web UI** — Streamlit interface with click‑through capture and queries (released).
4. **Pattern Analytics** — aggregate insights across your decision history (e.g., "When I rank financial security #1, I'm satisfied 80% of the time after 6 months").
5. **Export & Backup** — encrypted JSON/CSV export, optional iCloud/Google Drive sync.
6. **Multi‑user support** — namespaces per user in a shared database.
7. **Calendar/Contacts integration** — automatically pull in contextual data to enrich simulations.
8. **“Decision‑coach” mode** — after a new decision is captured, the agent suggests a follow‑up check‑in date (e.g., "6 months from now, I'll ask how you feel about this choice").
9. **Export to Notion/Roam** — embed decision archives into your personal knowledge graph.

---

## 🤝 Contributing

Found a bug or have an idea? Open an issue or submit a PR. This project is meant to be *personal* first — contributions should respect user privacy and data ownership.

*Built with ❤️ for anyone who's ever wondered "what if?" and wanted an answer grounded in their own data, not just generic advice.*

---

## 📬 Environment Setup Summary

| Step | Command / Action |
|---|---|
| Clone | `git clone … && cd temporal-paradox-resolver` |
| Venv | `python -m venv .venv && source .venv/bin/activate` |
| Install deps | `pip install -r requirements.txt` |
| Set API key | `export GEMINI_API_KEY='YOUR_KEY'`  or add to `.env` |
| Run CLI capture | `python main.py` |
| Run Streamlit UI | `streamlit run app.py` |
| Use Python features | import from `temporal_paradox_resolver.simulate` as shown above |

---

## 🎉 Quick “Hello World” Python Example

```python
import os, sys
sys.path.insert(0, "/Users/udishasingh/Desktop/RAG/AI Agent")
os.environ["GEMINI_API_KEY"] = "AQ.Ab8RN6IAx3sl1y5JK7Eqf5Vp3EGf3ki9VhgAwUlNKY7JR87PHg"

from temporal_paradox_resolver.store import DecisionStore
from temporal_paradox_resolver.simulate import (
    simulate_alternative,
    generate_pros_cons,
    generate_conclusion,
    generate_goal_plan,
    add_motivational_tagline,
)
from temporal_paradox_resolver.models import DecisionRecord
import datetime as dt, uuid, json

store = DecisionStore(db_path="/tmp/test.db")

# 1️⃣ Capture a mock record (normally done via CLI)
record = DecisionRecord(
    id=str(uuid.uuid4()),
    timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
    choice="I am deciding between Job A (high salary, long commute) and Job B (lower salary, remote).",
    values_ranked=["financial security", "work-life balance", "location"],
    alternatives=[
        {"name": "Job A", "pros": ["high salary"], "cons": ["long commute"]},
        {"name": "Job B", "pros": ["remote"], "cons": ["lower salary"]},
    ],
    context={"time_of_day": "evening", "energy_level": 6, "stressors": []},
    notes="Feeling burnt out.",
    tags=["career", "2024"],
)
store.add(record)

# 2️⃣ Simulate alternate timeline
narrative = simulate_alternative(record, "Job B (remote, lower salary)")
print("=== Narrative ===")
print(narrative)

# 3️⃣ Add motivational tagline
tagged = add_motivational_tagline(narrative)
print("\n=== Tagged ===")
print(tagged)

# 4️⃣ Generate pros‑cons for the alternative not chosen
pros_cons = generate_pros_cons(record, "Job B (remote, lower salary)")
print("\n=== Pros‑Cons ===")
print(pros_cons)

# 5️⃣ Generate a personal conclusion
conclusion = generate_conclusion(record, narrative)
print("\n=== Conclusion ===")
print(conclusion)

# 6️⃣ Generate a 6‑month goal plan for the top value
goal_plan = generate_goal_plan(record, top_value="financial security", horizon_months=6, num_milestones=3)
print("\n=== Goal Plan ===")
print(goal_plan)

store.close()
```

Run the snippet and you’ll see the narrative, tagline, pros‑cons, conclusion, and goal plan all generated by Google Gemini using your API key.

---

## 📖 Further Reading

- **Google AI Studio**: <https://aistudio.google.com/> — create & manage your Gemini API key.
- **Streamlit docs**: <https://docs.streamlit.io/> — for customizing the web UI.
- **SQLite docs**: <https://www.sqlite.org/> — the lightweight database used by default.
- **GitHub repository**: <https://github.com/your-handle/temporal-paradox-resolver> — source code, issues, contributions.

---

*Happy decision‑archiving! May your past choices illuminate your future path.*