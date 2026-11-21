"""Streamlit web UI for the Temporal Paradox Resolver.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import os

import streamlit as st

from temporal_paradox_resolver import commitment as engine
from temporal_paradox_resolver import llm
from temporal_paradox_resolver.cli import parse_alternative
from temporal_paradox_resolver.models import DecisionRecord, Doubt
from temporal_paradox_resolver.store import DecisionStore

st.set_page_config(page_title="Temporal Paradox Resolver", page_icon="⏳", layout="centered")

COLORS = {engine.HOLD: "#2e7d32", engine.WATCH: "#ed6c02", engine.RECONSIDER: "#c62828"}


@st.cache_resource
def get_store() -> DecisionStore:
    return DecisionStore(os.getenv("TPR_DB", "decisions.db"))


def lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def show_verdict(verdict: engine.Verdict) -> None:
    color = COLORS[verdict.decision]
    st.markdown(
        f"<div style='border-left:6px solid {color};padding:0.6rem 1rem;border-radius:4px'>"
        f"<b style='color:{color};font-size:1.3rem'>{verdict.decision}</b>"
        f"&nbsp;&nbsp;evidence {verdict.evidence:.1f} of {verdict.threshold:.1f} needed</div>",
        unsafe_allow_html=True,
    )
    st.progress(min(1.0, verdict.ratio))
    for reason in verdict.reasons:
        st.write("• " + reason)
    if verdict.scored_doubts:
        with st.expander("How each doubt was weighed"):
            for s in verdict.scored_doubts:
                st.write(f"**{s.score:.2f}** · {s.doubt.text}")
                st.caption("; ".join(s.factors))


store = get_store()
st.title("⏳ Temporal Paradox Resolver")
st.caption("Decide once, calmly. Then hold, unless something real changes.")
if not llm.available():
    st.caption("Running offline: set GEMINI_API_KEY for richer what-if and past-self answers.")

tab_capture, tab_hold, tab_explore = st.tabs(["📝 Decide", "🔒 Hold the line", "🔮 Explore"])

# ---------------------------------------------------------------------------
with tab_capture:
    with st.form("capture", clear_on_submit=True):
        choice = st.text_area("What did you decide? (your own words)*")
        alts = st.text_area(
            "Every option you weighed, one per line: Name | pro; pro | con; con*",
            placeholder="Startup | learning; ownership | risk; lower pay\nBank | salary; stability | slow growth",
        )
        chosen = st.text_input("Which option did you choose?*")
        values = st.text_area("What matters most here, ranked (one per line)*")
        reasoning = st.text_area("Why this option?")
        st.divider()
        conviction = st.slider("How sure are you?", 1, 10, 7)
        anchor = st.text_area("A note to your future self, for the day you doubt this")
        tripwires = st.text_area("I will reconsider ONLY if... (one condition per line)")
        cooling = st.number_input("Cooling period (days)", 0, 365, 30)
        tags = st.text_input("Tags (comma-separated)")
        submitted = st.form_submit_button("Decide and commit")

    if submitted:
        options = [parse_alternative(a) for a in lines(alts)]
        if not (choice.strip() and options and chosen.strip() and lines(values)):
            st.error("Please fill in the decision, the options, your choice and your values.")
        else:
            record = store.add(DecisionRecord(
                choice=choice.strip(), chosen=chosen.strip(), values_ranked=lines(values),
                alternatives=options, reasoning=reasoning.strip(),
                tags=[t.strip() for t in tags.split(",") if t.strip()],
            ))
            store.save_commitment(engine.commit(record, conviction, anchor, lines(tripwires), int(cooling)))
            st.success(f"Committed. You chose {record.chosen}, at {conviction}/10.")

records = store.list_all()
committed = [(r, store.get_commitment(r.id)) for r in records]
committed = [(r, c) for r, c in committed if c]


def pick(label: str, key: str):
    if not committed:
        st.info("No committed decisions yet. Start in the Decide tab.")
        return None, None
    idx = st.selectbox(label, range(len(committed)), key=key,
                       format_func=lambda i: f"{committed[i][0].chosen or committed[i][0].choice[:50]}"
                                             f" ({committed[i][1].status})")
    return committed[idx]


# ---------------------------------------------------------------------------
with tab_hold:
    record, c = pick("Decision", "hold_pick")
    if record:
        st.info(engine.reminder(c, record))
        if c.status != "committed":
            st.warning("This decision was reversed. History is kept below.")
        else:
            show_verdict(engine.evaluate(c, record))

            st.subheader("Having a doubt? Log it here instead of acting on it.")
            with st.form("doubt", clear_on_submit=True):
                text = st.text_area("What is bothering you?")
                new = st.checkbox("This is information I did not have when I decided")
                value = st.selectbox("Which value does it touch?", ["(none)"] + record.values_ranked)
                severity = st.slider("How serious is it?", 1, 5, 3)
                col1, col2 = st.columns(2)
                energy = col1.slider("Your energy right now", 1, 10, 6)
                stress = col2.slider("Your stress right now", 1, 10, 4)
                if st.form_submit_button("Log doubt") and text.strip():
                    engine.log_doubt(c, Doubt(text=text.strip(), is_new_information=new,
                                              affects_value="" if value == "(none)" else value,
                                              severity=severity, energy_level=energy, stress_level=stress))
                    store.save_commitment(c)
                    st.rerun()

            active = [t for t in c.tripwires if not t.triggered]
            if active:
                st.subheader("Did one of your conditions actually happen?")
                with st.form("trip"):
                    which = st.selectbox("Tripwire", range(len(c.tripwires)),
                                         format_func=lambda i: c.tripwires[i].condition)
                    evidence = st.text_input("What happened?")
                    if st.form_submit_button("It happened"):
                        engine.trigger_tripwire(c, str(which + 1), evidence)
                        store.save_commitment(c)
                        st.rerun()

            st.subheader("Review")
            col1, col2 = st.columns(2)
            with col1, st.form("reaffirm"):
                note = st.text_input("Why you are choosing this again")
                if st.form_submit_button("Reaffirm"):
                    engine.reaffirm(c, note)
                    store.save_commitment(c)
                    st.rerun()
            with col2, st.form("reverse"):
                reason = st.text_area("Why you are changing course")
                if st.form_submit_button("Reverse decision"):
                    try:
                        engine.reverse(c, record, reason)
                        store.save_commitment(c)
                        st.rerun()
                    except engine.CommitmentLocked:
                        st.error("Locked. The engine is holding this decision; see the verdict above.")
                    except ValueError as err:
                        st.error(str(err))

        with st.expander("History"):
            for e in reversed(c.history):
                st.write(f"`{e.timestamp[:16]}` **{e.kind}** {e.detail}")

# ---------------------------------------------------------------------------
with tab_explore:
    record, c = pick("Decision", "explore_pick")
    if record:
        others = [a["name"] for a in record.unchosen()] or record.alternative_names()
        if others:
            alt = st.selectbox("The road not taken", others)
            if st.button("Show me that timeline"):
                with st.spinner("Simulating..."):
                    st.markdown(llm.what_if(record, alt))
        doubt_text = st.text_input("Argue with your past self: what is your doubt?")
        if st.button("Hear the other side") and doubt_text:
            with st.spinner("Asking your past self..."):
                st.markdown(llm.defend_past_self(record, doubt_text))
        if st.button("Plan to make this decision pay off"):
            with st.spinner("Planning..."):
                st.markdown(llm.goal_plan(record))
