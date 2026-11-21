"""Streamlit web app for the Temporal Paradox Resolver.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import html
import os

import streamlit as st

from temporal_paradox_resolver import commitment as engine
from temporal_paradox_resolver import advisor, llm, motivation, settings
from temporal_paradox_resolver.models import STATUS_COMMITTED, DecisionRecord, Doubt
from temporal_paradox_resolver.store import DecisionStore

settings.load_env()
st.set_page_config(page_title="Temporal Paradox Resolver", page_icon="⏳", layout="centered")

st.markdown(
    """
    <style>
      .block-container {max-width: 760px; padding-top: 2rem;}
      .verdict {padding: 1rem 1.2rem; border-radius: 12px; margin: .5rem 0 1rem 0;}
      .verdict h3 {margin: 0 0 .25rem 0;}
      .verdict p {margin: 0; opacity: .85;}
      .past-self {padding: 1rem 1.2rem; border-radius: 12px; background: rgba(120,120,160,.10);
                  white-space: pre-line; line-height: 1.6;}
      div.stButton > button {border-radius: 10px;}
      .motivate {padding: 1.1rem 1.3rem; border-radius: 14px; margin-bottom: .6rem;
                 background: linear-gradient(135deg, rgba(255,183,77,.22), rgba(186,104,200,.18));}
      .motivate h4 {margin: 0 0 .4rem 0;}
      .motivate p {margin: 0; font-size: 1.05rem; line-height: 1.55;}
      .motivate small {opacity: .75;}
    </style>
    """,
    unsafe_allow_html=True,
)

VERDICTS = {
    engine.HOLD: ("🟢", "Stay the course.", "Your past self had good reasons. Nothing so far changes them.",
                  "rgba(46,125,50,.14)"),
    engine.WATCH: ("🟠", "Stay the course, and keep an eye on it.",
                   "Some real concerns are building. Keep noting them honestly instead of acting on them.",
                   "rgba(237,108,2,.14)"),
    engine.RECONSIDER: ("🔴", "Time for an honest second look.",
                        "Something real has changed. You can now keep your decision or change it.",
                        "rgba(198,40,40,.14)"),
}
SIZE = {"Tiny": 1, "Small": 2, "Medium": 3, "Big": 4, "Huge": 5}
MOOD = {"😣 Rough": 1, "😕 Meh": 2, "🙂 Okay": 3, "😊 Good": 4, "🤩 Great": 5}
ENERGY = {"Exhausted": 2, "Tired": 4, "Okay": 6, "Good": 8, "Great": 10}
STRESS = {"Calm": 2, "A little": 4, "Stressed": 6, "Very stressed": 8, "Overwhelmed": 10}


@st.cache_resource
def get_store() -> DecisionStore:
    return DecisionStore(os.getenv("TPR_DB", "decisions.db"))


def lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def go(view: str, decision_id: str | None = None) -> None:
    st.session_state.view = view
    st.session_state.open_id = decision_id
    st.rerun()


store = get_store()
st.session_state.setdefault("view", "home")
st.session_state.setdefault("open_id", None)
st.session_state.setdefault("form_round", 0)
if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"))

# ---------------------------------------------------------------------------
# Sidebar: settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    st.subheader("AI helper (optional)")
    if settings.masked_key():
        if llm.available():
            st.success(f"Connected  {settings.masked_key()}")
        else:
            st.warning(f"Key saved {settings.masked_key()}, but the AI package is missing. "
                       "Run `pip install google-genai` and restart the app.")
        if st.button("Remove key"):
            settings.clear_key()
            llm.reset()
            st.session_state.flash = "Key removed."
            st.rerun()
    else:
        st.info("Off. Everything still works; answers come from your own notes.")
    with st.form("key_form", clear_on_submit=True):
        new_key = st.text_input("Paste your Gemini key", type="password",
                                placeholder="Get one free at aistudio.google.com")
        if st.form_submit_button("Save key", use_container_width=True) and new_key.strip():
            settings.save_key(new_key)
            llm.reset()
            st.session_state.flash = "Key saved on this computer."
            st.rerun()
    st.caption("🔐 Your key is saved only on this computer, in a `.env` file that is never "
               "uploaded to GitHub. [Get a free key](https://aistudio.google.com/apikey)")

# ---------------------------------------------------------------------------
# Header and navigation
# ---------------------------------------------------------------------------
st.title("⏳ Temporal Paradox Resolver")
st.caption("Decide once, calmly. Then hold the line, unless something real changes.")

nav = st.columns(3)
if nav[0].button("🏠 My decisions", use_container_width=True):
    go("home")
if nav[1].button("➕ New decision", use_container_width=True, type="primary"):
    go("new")
if nav[2].button("🔮 What if?", use_container_width=True):
    go("explore")
st.write("")

records = store.list_all()
pairs = [(r, store.get_commitment(r.id)) for r in records]
pairs = [(r, c) for r, c in pairs if c]


# ---------------------------------------------------------------------------
# Shared pieces
# ---------------------------------------------------------------------------
def motivation_card(record, c, key: str) -> None:
    today = motivation.utcnow().date()
    m = motivation.daily_message(record, c, today)
    extra = []
    if m.streak:
        extra.append(f"🔥 {m.streak}-day streak")
    if m.next_milestone:
        extra.append(f"next milestone: day {m.next_milestone}")
    st.markdown(f"<div class='motivate'><h4>{html.escape(m.title)}</h4><p>{html.escape(m.message)}</p>"
                f"<small>{html.escape(' · '.join(extra))}</small></div>", unsafe_allow_html=True)
    with st.expander("💪 Why I'm doing this"):
        for reason in m.why:
            st.write("• " + reason)
    if motivation.checked_in_today(c, today):
        st.caption("✅ You checked in today. See you tomorrow!")
        return
    with st.form(f"checkin_{key}", clear_on_submit=True):
        st.markdown("**Daily check-in** · takes 10 seconds")
        mood = st.select_slider("How does it feel today?", options=list(MOOD), value="🙂 Okay")
        win = st.text_input("One small win today (optional)", placeholder="e.g. Finished my first project task")
        if st.form_submit_button("✅ Check in", type="primary"):
            motivation.check_in(c, MOOD[mood], win, today)
            store.save_commitment(c)
            st.session_state.flash = "Checked in! 🔥"
            st.rerun()


def show_advice(advice: advisor.Advice) -> None:
    st.markdown(f"**{advice.opening}**")
    if not advice.points:
        st.write("Nothing worrying stands out.")
    for p in advice.points:
        st.markdown(f"{p.icon} **{p.title}**  \n{p.detail}")
    if advice.other_side:
        st.markdown("**↔️ The honest case for the other side**")
        for line in advice.other_side:
            st.write("• " + line)
    (st.success if advice.ready else st.info)(advice.summary)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
def view_home() -> None:
    if not pairs:
        st.markdown("### Welcome 👋")
        st.write("Made a big choice recently, or about to? Write it down while your head is clear. "
                 "When doubts show up later, this app helps you tell a bad day from a real reason to change.")
        if st.button("➕ Record my first decision", type="primary"):
            go("new")
        return
    active = [(r, c) for r, c in pairs if c.status == STATUS_COMMITTED]
    if active:
        st.markdown("### ☀️ Today")
        for record, c in active[:3]:
            motivation_card(record, c, f"home_{record.id}")
        st.write("")
    st.markdown("### My decisions")
    for record, c in pairs:
        with st.container(border=True):
            left, right = st.columns([4, 1])
            title = record.chosen or record.choice
            if c.status != STATUS_COMMITTED:
                left.markdown(f"**{title}**  \n↩️ Changed. Kept for your records.")
            else:
                v = engine.evaluate(c, record)
                icon, headline, _, _ = VERDICTS[v.decision]
                left.markdown(f"**{title}**  \n{icon} {headline} · held {v.days_committed} day(s)")
                left.progress(min(1.0, v.ratio), text="Case for changing")
            if right.button("Open", key=f"open_{record.id}", use_container_width=True):
                go("detail", record.id)


def view_detail() -> None:
    found = [(r, c) for r, c in pairs if r.id == st.session_state.open_id]
    if not found:
        go("home")
    record, c = found[0]

    if st.button("← Back"):
        go("home")
    st.markdown(f"## {record.chosen or record.choice}")
    if record.chosen and record.choice != record.chosen:
        st.caption(record.choice)

    if c.status != STATUS_COMMITTED:
        st.info("You changed this decision. Here is the record of how you got there.")
        show_history(c)
        return

    v = engine.evaluate(c, record)
    icon, headline, explain, color = VERDICTS[v.decision]
    st.markdown(f"<div class='verdict' style='background:{color}'><h3>{icon} {headline}</h3>"
                f"<p>{explain}</p></div>", unsafe_allow_html=True)
    st.progress(min(1.0, v.ratio), text=f"Case for changing: {v.evidence:.1f} of {v.threshold:.1f} needed")

    motivation_card(record, c, "detail")

    st.markdown("#### 💌 Your past self says")
    st.markdown(f"<div class='past-self'>{html.escape(engine.reminder(c, record))}</div>", unsafe_allow_html=True)
    st.write("")

    with st.expander("😟 I'm having a doubt", expanded=v.decision != engine.RECONSIDER):
        with st.form("doubt", clear_on_submit=True):
            text = st.text_area("What's bothering you?", placeholder="Say it in your own words")
            known = st.radio("Did you know this when you decided?",
                             ["No, this is new", "Yes, I already knew it"], horizontal=True)
            value = st.selectbox("What does it affect most?", record.values_ranked + ["Something else"])
            size = st.select_slider("How big is it?", options=list(SIZE), value="Medium")
            col1, col2 = st.columns(2)
            energy = col1.select_slider("How's your energy?", options=list(ENERGY), value="Okay")
            stress = col2.select_slider("How stressed are you?", options=list(STRESS), value="A little")
            if st.form_submit_button("Write it down", type="primary") and text.strip():
                engine.log_doubt(c, Doubt(
                    text=text.strip(), is_new_information=known.startswith("No"),
                    affects_value="" if value == "Something else" else value,
                    severity=SIZE[size], energy_level=ENERGY[energy], stress_level=STRESS[stress]))
                store.save_commitment(c)
                st.session_state.flash = "Written down. It's been weighed, not acted on."
                st.rerun()
        st.caption("Not sure if it's a real reason? Try **What if?** → *Hear my past self out*.")

    pending = [t for t in c.tripwires if not t.triggered]
    if pending:
        with st.expander("🚩 Something I planned for has happened"):
            with st.form("trip"):
                which = st.radio("Which one?", range(len(c.tripwires)),
                                 format_func=lambda i: c.tripwires[i].condition)
                evidence = st.text_input("What happened?")
                if st.form_submit_button("Yes, this happened"):
                    engine.trigger_tripwire(c, str(which + 1), evidence)
                    store.save_commitment(c)
                    st.rerun()

    st.markdown("#### Decide again")
    keep, change = st.columns(2)
    with keep.form("reaffirm", clear_on_submit=True):
        note = st.text_input("Why I'm keeping it (optional)")
        if st.form_submit_button("💪 Keep my decision", use_container_width=True):
            engine.reaffirm(c, note)
            store.save_commitment(c)
            st.session_state.flash = "Kept. It's now even harder to shake."
            st.rerun()
    with change.form("reverse"):
        locked = not v.can_reverse
        reason = st.text_input("Why I'm changing it", disabled=locked)
        if st.form_submit_button("🔒 Locked for now" if locked else "↩️ Change my decision",
                                 use_container_width=True, disabled=locked):
            try:
                engine.reverse(c, record, reason)
                store.save_commitment(c)
                st.session_state.flash = "Changed and recorded. Record your new decision next."
                go("new")
            except ValueError as err:
                st.error(str(err))
    if not v.can_reverse:
        st.caption("Changing is unlocked only when something you planned for happens, "
                   "or when strong new reasons keep showing up for over a week.")

    with st.expander("Why this answer?"):
        for reason in v.reasons:
            st.write("• " + reason)
        for s in v.scored_doubts:
            st.write(f"**{s.score:.2f}** · {s.doubt.text}")
            st.caption("; ".join(s.factors))
    show_history(c)


def show_history(c) -> None:
    with st.expander("📜 History"):
        for e in reversed(c.history):
            st.write(f"`{e.timestamp[:10]}` **{e.kind}** {e.detail}")


def view_new() -> None:
    r = st.session_state.form_round
    st.markdown("### ➕ New decision")
    st.caption("Take your time. The calmer and more honest you are now, the more this helps later.")

    choice = st.text_input("**1. What are you deciding?**", key=f"choice{r}",
                           placeholder="e.g. Which job offer to accept")

    st.markdown("**2. What are your options?**")
    count = st.number_input("How many options?", 2, 6, 2, key=f"count{r}")
    options = []
    for i in range(int(count)):
        with st.container(border=True):
            name = st.text_input(f"Option {i + 1}", key=f"name{r}_{i}", placeholder="Name it")
            col1, col2 = st.columns(2)
            pros = col1.text_area("👍 Good things", key=f"pros{r}_{i}", height=90, placeholder="One per line")
            cons = col2.text_area("👎 Downsides", key=f"cons{r}_{i}", height=90, placeholder="One per line")
            if name.strip():
                options.append({"name": name.strip(), "pros": lines(pros), "cons": lines(cons)})

    names = [o["name"] for o in options]
    chosen = st.radio("**3. Which one are you choosing?**", names, horizontal=True,
                      key=f"chosen{r}") if names else None
    values = st.text_area("**4. What matters most to you here?** Most important first, one per line",
                          key=f"values{r}", placeholder="growth\nfamily\nmoney")
    reasoning = st.text_area("**5. Why this option?**", key=f"why{r}",
                             placeholder="In a sentence or two, in your own words")
    conviction = st.slider("**6. How sure are you?**", 1, 10, 7, key=f"sure{r}")
    anchor = st.text_area("**7. A note to your future self** for the day you doubt this",
                          key=f"anchor{r}", placeholder="You knew it would be hard. You chose it anyway because...")
    tripwires = st.text_area("**8. I'll only reconsider if...** one condition per line",
                             key=f"trip{r}", placeholder="The company runs out of money\n"
                                                         "I'm unhappy for three months in a row")
    st.markdown("**9. How are you feeling right now?**")
    col1, col2 = st.columns(2)
    energy = col1.select_slider("Energy", options=list(ENERGY), value="Okay", key=f"energy{r}")
    stress = col2.select_slider("Stress", options=list(STRESS), value="A little", key=f"stress{r}")
    with st.expander("More settings"):
        cooling = st.number_input("Settling-in period (days). Ordinary doubts can't unlock the decision "
                                  "during this time.", 0, 365, 30, key=f"cool{r}")
        tags = st.text_input("Tags (comma-separated)", key=f"tags{r}")

    draft = DecisionRecord(choice=choice.strip(), chosen=chosen or "", values_ranked=lines(values),
                           alternatives=options, reasoning=reasoning.strip())
    st.write("")
    with st.container(border=True):
        st.markdown("#### 🧭 Honest second opinion")
        st.caption("Not to change your mind. Just so you decide with open eyes.")
        a_col, b_col = st.columns(2)
        if a_col.button("Check my decision", use_container_width=True, disabled=len(options) < 2):
            st.session_state[f"advice{r}"] = True
        if llm.available() and b_col.button("Ask AI for an outside view", use_container_width=True,
                                            disabled=len(options) < 2):
            with st.spinner("Thinking it through..."):
                st.session_state[f"outside{r}"] = advisor.outside_view(draft)
        if st.session_state.get(f"advice{r}"):
            show_advice(advisor.review(draft, conviction, lines(tripwires), ENERGY[energy], STRESS[stress]))
        if st.session_state.get(f"outside{r}"):
            st.markdown("**🤖 Outside view**")
            st.markdown(st.session_state[f"outside{r}"])

    if st.button("🔒 Commit to this decision", type="primary", use_container_width=True):
        missing = [label for label, ok in [("what you're deciding", choice.strip()),
                                           ("at least two named options", len(options) >= 2),
                                           ("what matters most", lines(values))] if not ok]
        if missing:
            st.error("Please add " + ", ".join(missing) + ".")
            return
        record = store.add(DecisionRecord(
            choice=choice.strip(), chosen=chosen or "", values_ranked=lines(values), alternatives=options,
            reasoning=reasoning.strip(), tags=[t.strip() for t in tags.split(",") if t.strip()],
            context={"energy_level": ENERGY[energy], "stress_level": STRESS[stress]}))
        store.save_commitment(engine.commit(record, conviction, anchor, lines(tripwires), int(cooling)))
        st.session_state.form_round += 1
        st.session_state.flash = f"Committed to {record.chosen}. 💪"
        go("detail", record.id)


def view_explore() -> None:
    st.markdown("### 🔮 What if?")
    if not pairs:
        st.info("Record a decision first, then come back to explore it.")
        return
    idx = st.selectbox("Decision", range(len(pairs)),
                       format_func=lambda i: pairs[i][0].chosen or pairs[i][0].choice)
    record = pairs[idx][0]
    if not llm.available():
        st.caption("Tip: add a Gemini key in ⚙️ Settings (sidebar) for richer answers.")

    with st.container(border=True):
        st.markdown("**🛤️ The road not taken**")
        others = [a["name"] for a in record.unchosen()] or record.alternative_names()
        if others:
            alt = st.selectbox("Imagine you had chosen", others)
            if st.button("Show me that life"):
                with st.spinner("Imagining..."):
                    st.markdown(llm.what_if(record, alt))
    with st.container(border=True):
        st.markdown("**🗣️ Hear my past self out**")
        doubt = st.text_input("What's your doubt?")
        if st.button("Make the case") and doubt.strip():
            with st.spinner("Thinking..."):
                st.markdown(llm.defend_past_self(record, doubt))
    with st.container(border=True):
        st.markdown("**🗺️ Make it pay off**")
        if st.button("Give me a plan"):
            with st.spinner("Planning..."):
                st.markdown(llm.goal_plan(record))


{"home": view_home, "detail": view_detail, "new": view_new, "explore": view_explore}.get(
    st.session_state.view, view_home)()
