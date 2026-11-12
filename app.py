"""Streamlit web UI for the Temporal Paradox Resolver.

Features:
  • Capture a new decision (form).
  • View stored decisions.
  • Ask "what‑if" natural‑language questions about alternatives.
  • Uses Google Gemini (via the provided API key) for simulations.
  • Sidebar button to search for alternative options (placeholder API).

Run with:
    streamlit run app.py
"""

# ---------------------------------------------------------------------------
# Placeholder for web‑search based alternative generation
# ---------------------------------------------------------------------------
def search_alternatives(keywords: str) -> str:
    """Placeholder for a web‑search based alternative‑generation function.

    In a full implementation you would call a search API (e.g. Google Custom Search,
    Bing Search, or a public scraper) with *keywords* and return a concise summary
    of the most relevant alternatives, including a one‑sentence description and a
    bullet list of pros/cons if available.

    For now the function returns a friendly message telling the user what would
    happen next.
    """
    return (
        "🔎 Web‑search integration not yet configured. \n\n"
        "To enable this feature you can:\n"
        "1. Obtain a Google Custom Search JSON API key and CX ID.\n"
        "2. Replace the function body with a call to the API, e.g.\n"
        "   `response = requests.get('https://www.googleapis.com/customsearch/v1', "
        "params={'key': API_KEY, 'cx': CX_ID, 'q': keywords})`. \n"
        "3. Parse the `items` array and format the results as markdown.\n\n"
        f"Searched keywords: *{keywords}*. \n"
        "When the API is wired, the result will appear here automatically."
    )

# Ensure the parent directory is on the path so `temporal_paradox_resolver` package is findable
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid
import datetime as dt

import json
import streamlit as st

from temporal_paradox_resolver.store import DecisionStore
from temporal_paradox_resolver.simulate import simulate_alternative, SIMULATION_PROMPT
from temporal_paradox_resolver.models import DecisionRecord

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Temporal Paradox Resolver", page_icon="⏳", layout="centered")

st.title("⏳ Temporal Paradox Resolver")
st.caption("Your personal decision‑time capsule. Archive choices today, explore alternate timelines tomorrow.")

# ---------------------------------------------------------------------------
# Initialize store (singleton per session)
# ---------------------------------------------------------------------------
if "store" not in st.session_state:
    GEMINI_API_KEY = __import__("os").getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        st.error(
            "🔑 GEMINI_API_KEY not set. Add it to your environment, e.g.:\n"
            "`export GEMINI_API_KEY='AQ.Ab8RN6IAx3sl1y5JK7Eqf5Vp3EGf3ki9VhgAwUlNKY7JR87PHg'`"
        )
        st.stop()
    st.session_state.store = DecisionStore(db_path="streamlit_decisions.db")

store = st.session_state.store

# ---------------------------------------------------------------------------
# Helper: capture form
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("📝 Capture a New Decision")
    with st.form("capture_form", clear_on_submit=False):
        choice = st.text_area("Describe the decision (your exact words)*", height=120)
        st.caption("* required")
        st.subheader("Values you're ranking (one per line)*")
        values_input = st.text_area("e.g. financial security\nwork-life balance\nlocation", height=100)
        st.caption("* required")
        alternatives_st = st.text_area(
            "Alternatives (one per block). For each: name, then pros (one per line), then cons (one per line).\n"
            "Terminate each block with an empty line.",
            height=200,
        )
        context_time = st.selectbox("Time of day", ["morning", "afternoon", "evening"], index=2)
        energy = st.slider("Energy level (1‑10)", 1, 10, 6)
        stressors = st.text_area("Stressors (comma‑separated)", "")
        notes = st.text_area("Any additional notes (free‑form)")
        tags = st.text_input("Tags (comma‑separated)", "career,2024,major")
        submitted = st.form_submit_button("Save Decision")

    if submitted:
        # --- Validate required fields ---
        if not choice.strip():
            st.error("Choice is required.")
            st.stop()
        if not values_input.strip():
            st.error("At least one value must be provided.")
            st.stop()
        # Parse alternatives blocks
        blocks = [b.strip() for b in alternatives_st.split("\n\n") if b.strip()]
        if not blocks:
            st.error("At least one alternative must be provided.")
            st.stop()

        # Parse values (keep only non‑empty lines)
        values = [v.strip() for v in values_input.splitlines() if v.strip()]

        # Parse each alternative block
        alternatives = []
        for block in blocks:
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            if not lines:
                continue
            name = lines[0]
            pros = lines[1:] if len(lines) > 1 else []
            # Cons may be on a separate "Cons" marker; for simplicity, treat remaining as cons
            # Actually we need structured parsing; skip for now and just capture name
            alternatives.append({"name": name, "pros": pros, "cons": []})

        # -------------------------------------------------------

        # Parse stressors
        context = {"time_of_day": context_time, "energy_level": energy, "stressors": [s.strip() for s in stressors.split(",") if s.strip()]}

        record = DecisionRecord(
            id=str(uuid.uuid4()),
            timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
            choice=choice,
            values_ranked=values,
            alternatives=alternatives,
            context=context,
            notes=notes or "",
            tags=[t.strip() for t in tags.split(",") if t.strip()],
        )

        store.add(record)
        st.success(f"✅ Decision saved (ID: {record.id[:8]}…)")
        # Clear form by re‑running
        st.rerun()

# ---------------------------------------------------------------------------
# View stored decisions
# ---------------------------------------------------------------------------
st.subheader("🗂️ Your Decisions")
records = store.list_all()
if not records:
    st.info("No decisions captured yet. Use the sidebar form to add one.")
else:
    # Show a summary table
    for i, rec in enumerate(records, 1):
        with st.expander(f"Decision {i}: {rec.choice[:60]}…"):
            st.write(f"**Timestamp:** {rec.timestamp}")
            st.write(f"**Values ranked:** {rec.values_ranked}")
            st.write(f"**Alternatives:** {len(rec.alternatives)} options")
            st.write(f"**Tags:** {rec.tags}")
            if st.button(f"Use this decision for a what‑if query", key=f"use_{rec.id}"):
                st.session_state["selected_record_id"] = rec.id
                st.query_params = {"whatif": ""}  # reset

    # Select a record for querying
    record_ids = [rec.id for rec in records]
    selected_id = st.selectbox(
        "Select a decision to query:",
        options=record_ids,
        format_func=lambda x: next((rec.choice[:40] + "…" for rec in records if rec.id == x), "Unknown"),
        index=record_ids.index(st.session_state.get("selected_record_id", record_ids[-1])) if st.session_state.get("selected_record_id") in record_ids else len(record_ids) - 1,
    )
    st.session_state["selected_record_id"] = selected_id

    selected_record = next(rec for rec in records if rec.id == selected_id)

    # ---------------------------------------------------------------------------
    # What‑if query form
    # ---------------------------------------------------------------------------
    st.subheader("🔮 Ask a What‑If Question")
    st.write("Type a natural‑language question about the decision you selected above.")
    with st.form("what_if_form"):
        question = st.text_area(
            "Your question",
            placeholder="e.g. If I had chosen the government job, where would I be living today?",
            height=120,
        )
        submit_query = st.form_submit_button("Generate Timeline")

    alt_name = None

    if submit_query and question:
        with st.spinner("Consulting the simulation engine..."):
            # Extract alternate name from question (very simple heuristic)
            # We'll just use the first alternative name from the record if the question mentions "the other option"
            alt_name = None
            # Check if question contains "Job A" / "Job B" etc.
            import re
            names_in_question = re.findall(r"\bJob\s+[A-Z]\b", question)
            if names_in_question:
                # Use the first mentioned name as alternate
                alt_name = names_in_question[0]
            else:
                # Fallback: use the first alternative's name
                if selected_record.alternatives:
                    alt_name = selected_record.alternatives[0]["name"]

            narrative = simulate_alternative(selected_record, alt_name or "the other option")

        if narrative:
            st.success("✅ Here's your alternate‑timeline narrative:")
            st.markdown(narrative)
        else:
            st.error("❌ Failed to generate narrative. Check the API key/quota.")

    # Optional: show the raw prompt sent to the LLM (expandable)
    with st.expander("View the prompt sent to Gemini"):
        # Build prompt similar to simulate module
        prompt = SIMULATION_PROMPT.format(
            choice=selected_record.choice,
            values_ranked=json.dumps(selected_record.values_ranked, ensure_ascii=False),
            alternatives=json.dumps(selected_record.alternatives, ensure_ascii=False),
            alternate_name=alt_name or "the other option",
        )
        st.code(prompt, language="text")


# ---------------------------------------------------------------------------
# Helper: simple web‑search placeholder (replace with real API later)
# ---------------------------------------------------------------------------
def search_alternatives(keywords: str) -> str:
    """Placeholder for a web‑search based alternative‑generation function.

    In a full implementation you would call a search API (e.g. Google Custom Search,
    Bing Search, or a public scraper) with *keywords* and return a concise summary
    of the most relevant alternatives, including a one‑sentence description and a
    bullet list of pros/cons if available.

    For now the function returns a friendly message telling the user what would
    happen next.
    """
    return (
        "🔎 Web‑search integration not yet configured. \n\n"
        "To enable this feature you can:\n"
        "1. Obtain a Google Custom Search JSON API key and CX ID.\n"
        "2. Replace the function body with a call to the API, e.g.\n"
        "   `response = requests.get('https://www.googleapis.com/customsearch/v1', "
        "params={'key': API_KEY, 'cx': CX_ID, 'q': keywords})`. \n"
        "3. Parse the `items` array and format the results as markdown.\n\n"
        f"Searched keywords: *{keywords}*. \n"
        "When the API is wired, the result will appear here automatically."
    )