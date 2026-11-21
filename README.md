# ⏳ Temporal Paradox Resolver

**Decide once, calmly. Then hold the line, unless something real changes.**

Every big decision creates a quiet paradox. There are two versions of you:

- **Your past self**, who decided with a clear head, weighed the options, and knew exactly why.
- **Your present self**, who is tired at 1 a.m., scrolling through someone else's life, and suddenly sure it was all a mistake.

Both are you. Only one of them should be steering. The Temporal Paradox Resolver settles that argument. It archives the full context of a decision at the moment you make it, then puts a **commitment lock** on it. Doubts get *logged and weighed* instead of acted on. The lock opens only when the case for changing course is genuinely strong: new information, about something you care about, felt with a clear mind, and still true a week later. Or when a condition your past self wrote down in advance actually happens.

No mood swings. No flip-flopping. No changing your mind because of one bad night. And no stubbornness either, because when the situation really does change, the engine says so plainly.

---

## Table of contents

- [Why this exists](#why-this-exists)
- [How the commitment lock works](#how-the-commitment-lock-works)
- [Quick start](#quick-start)
- [A full example](#a-full-example)
- [Motivation that keeps you going](#motivation-that-keeps-you-going)
- [An honest second opinion before you commit](#an-honest-second-opinion-before-you-commit)
- [The web app](#the-web-app)
- [Command reference](#command-reference)
- [Under the hood: how doubts are weighed](#under-the-hood-how-doubts-are-weighed)
- [Optional AI features](#optional-ai-features)
- [Project layout](#project-layout)
- [Running the tests](#running-the-tests)
- [Ideas for what comes next](#ideas-for-what-comes-next)

---

## Why this exists

People rarely regret decisions because they were made badly. They regret them because, months later, they can no longer remember *why* they made them. The reasons fade, the trade-offs blur, and what is left is the cost of the path you took next to the imagined perfection of the one you did not.

That leads to three predictable traps:

1. **Re-arguing settled trade-offs.** You knew the startup paid less. You chose it anyway, for the learning. "But the bank pays more!" is not news.
2. **Deciding from a bad state.** Exhaustion and stress make every choice look worse. A doubt felt at 2/10 energy is mostly about the 2/10 energy.
3. **Flip-flopping.** You change course, then change back, and lose the benefits of both paths, because most good decisions only pay off if you stay with them long enough.

The resolver is built around a few ideas from decision research: write down your reasoning at the time, set **kill criteria** (here called *tripwires*) in advance, add a **cooling-off period**, and use **hysteresis** so that the bar to switch back is higher than the bar to switch in the first place.

---

## How the commitment lock works

When you make a decision, you tell the resolver:

| You record | Why it matters |
|---|---|
| **The decision and every option**, with pros and cons | So future-you can see the whole picture you saw. |
| **Your ranked values** | Doubts about your #1 value weigh much more than doubts about your #5. |
| **Your reasoning** | In your own words, quoted back to you when you waver. |
| **Conviction (1-10)** | The surer you were, the more evidence it takes to unsettle you. |
| **A note to your future self** | Read first, every time you log a doubt. |
| **Tripwires** | "I will reconsider only if..." conditions, written while calm. |
| **A cooling period** | Days during which ordinary doubts cannot unlock the decision. |

From then on, the engine gives one of three verdicts:

| Verdict | Meaning |
|---|---|
| 🟢 **HOLD** | Stay the course. Your past self had good reasons. |
| 🟠 **WATCH** | Still hold, but evidence is building. Keep logging honestly. |
| 🔴 **RECONSIDER** | A real reason to review exists. Now, and only now, you may reaffirm or reverse. |

The rules that make it firm:

- 🔐 **You cannot reverse a decision unless the verdict is RECONSIDER.** The command refuses and shows you why.
- 🧠 **Old news barely counts.** A doubt about something you already knew when you decided counts at 25%.
- 😴 **Your state of mind is factored in.** Doubts logged while exhausted (energy ≤ 3) or overwhelmed (stress ≥ 8) count half.
- 📅 **One bad day is never enough.** You need at least two doubts that bring new information, spread over at least seven days.
- ❄️ **The cooling period protects early decisions.** Inside it, only a tripwire or twice the usual evidence can break the lock.
- 🎯 **Tripwires always win.** If a condition you wrote in advance happens, the engine says RECONSIDER at once. You trusted your calm self to define what counts.
- 🔁 **Reaffirming makes you stronger.** Choosing the decision again clears the doubts you have now answered and raises the bar by 25%. The same doubts cannot flip you back next month.
- ✍️ **Reversing needs a written reason.** At least 40 characters, stored forever, so your next future self knows why you changed.

Every verdict comes with line-by-line reasons and a breakdown of how each doubt was weighed. The engine is plain, deterministic Python: no AI is involved in the decision to hold or release, so the same history always gives the same answer.

---

## Quick start

Requires Python 3.10 or newer. The core uses only the standard library.

```bash
git clone https://github.com/Anushka180712/temporal-paradox-resolver.git
cd temporal-paradox-resolver
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[ui,dev]"         # app, AI helper and tests
```

That installs a `tpr` command. Capture your first decision interactively:

```bash
tpr capture
```

Or run the web app:

```bash
streamlit run app.py
```

You can also skip installing and use `python -m temporal_paradox_resolver <command>`.

---

## A full example

**1. Decide and lock it in.**

```bash
tpr capture \
  --choice "Join the early-stage startup instead of the bank" \
  --chosen "Startup" \
  --values "growth, autonomy, money" \
  --alt "Startup | fast learning; real ownership | lower pay; risk" \
  --alt "Bank | higher salary; stability | slow growth; narrow role" \
  --reasoning "I learn fastest where I own real problems, and I can afford the risk now." \
  --conviction 8 \
  --anchor "You knew the pay was lower. You chose growth on purpose." \
  --tripwire "The company runs out of runway" \
  --tripwire "I have learned nothing new for three months straight" \
  --cooling-days 60
```

```
Saved decision 3f9c1a2b.
Committed at 8/10 with 2 tripwire(s) and a 60-day cooling period.
```

**2. Two weeks in, a friend posts their bank bonus. You feel it.**

```bash
tpr doubt 3f9c "My friend's bonus at the bank is huge" --value money --energy 3 --stress 7
```

```
Before anything else, read what your past self wrote:

You chose: Startup
You have held this for 14 day(s).
What mattered most, in order: growth, autonomy, money
Why you chose it: I learn fastest where I own real problems, and I can afford the risk now.
How sure you were: 8/10
Your note to yourself: "You knew the pay was lower. You chose growth on purpose."
You agreed to reconsider only if: The company runs out of runway; I have learned nothing new for three months straight

Doubt logged. It has been weighed, not acted on.

Verdict: HOLD   [....................] 0.1 / 15.6
  - Evidence against the decision: 0.1 of the 15.6 needed (conviction 8/10).
  - The evidence has not reached the bar.
  - Only 0 doubt(s) bring new information; at least 2 are needed. Re-arguing known trade-offs does not count.
  ...
  - Hold the decision. Your past self had good reasons.
```

The doubt scored almost nothing: you already knew the pay was lower, money is your #3 value, and you were exhausted.

**3. Try to quit anyway.**

```bash
tpr reverse 3f9c --reason "The bank just looks so much better right now honestly."
```

```
Not reversed. The engine is holding this decision.
```

**4. Something real happens.**

```bash
tpr trip 3f9c 1 --evidence "Funding round collapsed; six weeks of runway left"
```

```
Tripwire triggered: The company runs out of runway
Verdict: RECONSIDER
  - A tripwire you set in advance has been triggered: 'The company runs out of runway'.
```

Now you review. Either **reaffirm** (`tpr reaffirm 3f9c --note "Founders found a bridge loan; staying"`), which makes the lock stronger, or **reverse** with a real reason, and capture your next decision.

Use `tpr check 3f9c` at any point to see the full verdict with every doubt's weight, and `tpr show 3f9c` for the record and its complete history.

---

## Motivation that keeps you going

Writing a decision down is the easy part. Sticking with it on day 40 is the hard part. So the resolver doesn't just store your notes. It brings them back to you:

- **☀️ A fresh message every day**, built from your own reasons, what your chosen option gives you, the downsides you chose *not* to live with, your top value and your note to yourself. It changes daily, so it doesn't turn into wallpaper. With a Gemini key, it's rewritten in a warmer, more personal voice, still using only your own words.
- **🎉 Milestones** at day 1, 3, 7, 14, 21, 30, 60, 90, 100, 180 and 365.
- **✅ A 10-second daily check-in**: how it feels today, plus one small win. Your wins come back in later messages as proof the decision is paying off.
- **🔥 A check-in streak** that makes showing up a habit.
- **💪 "Why I'm doing this"**: every reason, in one list, one tap away.

On the command line: `tpr motivate` for today's message, and `tpr checkin ID --mood 4 --win "..."`. To get it automatically every morning, schedule `tpr motivate` with cron (Mac/Linux) or Task Scheduler (Windows).

---

## An honest second opinion before you commit

While you're deciding, the advisor says: **"It's okay to choose this. Before you lock it in, here's what you should know."** It never picks for you. It checks your draft for the classic traps:

| Check | What it looks for |
|---|---|
| ⚖️ A fair comparison | The other option has no good points written, or more good points than yours |
| 🙈 Hidden costs | No downsides listed for the option you're choosing |
| 🎯 Your values | Your reasons don't touch the value you ranked #1 |
| 👥 Other people's voices | Reasons that are really about what parents, friends or "everyone" expect |
| 🕳️ Sunk cost | "I've already invested...", "can't waste..." |
| 😨 Fear | Moving away from a fear rather than toward something |
| ⏰ False urgency | "Now or never", "last chance" |
| 😴 Your state | Deciding while exhausted or overwhelmed |
| 🔭 Confidence | 10/10 certainty (blind spots) or 4/10 or less (get one more fact first) |
| 🚩 Exits | No "I'll reconsider if..." conditions |

It also shows **the honest case for the other side**: exactly what you give up by not choosing it. That way, nothing it offered can surprise you later. With a Gemini key, **Ask AI for an outside view** adds an unbiased written review. On the command line: `tpr advise ID` (or `--ai`). `tpr capture` also shows the advice before it commits.

---

## The web app

`streamlit run app.py` opens a simple, friendly app:

- **☀️ Today**: today's motivation for each decision, your streak, and the daily check-in, right at the top.
- **🏠 My decisions**: one card per decision with a plain-language verdict ("Stay the course") and how strong the case for changing is.
- **➕ New decision**: nine short, numbered questions. Options get their own boxes for good things and downsides, and you pick your choice with one tap. Before you commit, **🧭 Check my decision** gives you the honest second opinion.
- **Decision page**: what your past self wants you to read, an "I'm having a doubt" box that asks in everyday words (is this new? how big is it? how is your energy?), a "something I planned for happened" button, and a **Keep my decision** / **Change my decision** pair. Change stays visibly locked until the engine allows it.
- **🔮 What if?**: the road not taken, "hear my past self out", and a plan to make your decision pay off.

**Adding your Gemini key is a paste:** open the sidebar, paste the key under ⚙️ Settings, press **Save key**. It is stored only on your computer in a `.env` file that git ignores, so it never ends up in the code or on GitHub. **Remove key** deletes it again.

Data is stored in `decisions.db` (override with `TPR_DB`).

---

## Command reference

| Command | What it does |
|---|---|
| `tpr capture` | Record a decision and lock it. Interactive with no flags, scriptable with `--choice`, `--chosen`, `--values`, `--alt`, `--reasoning`, `--conviction`, `--anchor`, `--tripwire`, `--cooling-days`, `--no-commit`. |
| `tpr commit ID` | Lock a decision you saved with `--no-commit`. |
| `tpr list` | All decisions with their current verdict. |
| `tpr show ID` | Full record, reminder, history and verdict. |
| `tpr doubt ID "text"` | Log a doubt. Flags: `--new` (information you did not have), `--value`, `--severity 1-5`, `--energy 1-10`, `--stress 1-10`. |
| `tpr check ID` | Verdict with a breakdown of every doubt's weight. |
| `tpr trip ID N` | Mark tripwire number `N` as triggered, with `--evidence`. |
| `tpr reaffirm ID` | Choose the decision again. Clears answered doubts, raises the bar. |
| `tpr reverse ID --reason "..."` | Change course. Refused unless the verdict is RECONSIDER. |
| `tpr whatif ID "Option"` | Narrative of the timeline where you chose another option. |
| `tpr defend ID "doubt"` | Your past self's strongest honest case against a doubt. |
| `tpr plan ID` | Milestones that turn your top value into progress on the chosen path. |
| `tpr motivate [ID]` | Today's motivation, from your own reasons. |
| `tpr checkin ID` | Daily check-in: `--mood 1-5`, `--win "..."`. |
| `tpr advise ID` | The honest second opinion (`--ai` for Gemini's outside view). |
| `tpr export` | Everything as JSON, for backup. |

`ID` can be the first few characters of a decision's id. Use `--db path.db` (or `TPR_DB`) to pick a database.

---

## Under the hood: how doubts are weighed

Each doubt starts at its **severity** (1-5) and is multiplied by:

| Factor | Multiplier |
|---|---|
| Brings new information | × 1.0 |
| Already known when you decided | × 0.25 |
| Touches your value ranked *r* of *n* | × (n − r + 1) / n, so your top value is × 1.0 |
| Not tied to a ranked value | × 0.5 |
| Logged while exhausted (energy ≤ 3) or overwhelmed (stress ≥ 8) | × 0.5 |
| Logged while strained (energy ≤ 5 or stress ≥ 6) | × 0.75 |
| Age | halves every 60 days, so doubts that are not repeated fade |

The **bar** is `6 + 1.2 × conviction`, multiplied by `1.25` for every reaffirmation. Conviction 7 means 14.4. After one reaffirmation, 18.

The verdict is **RECONSIDER** when a tripwire is triggered, or when all of these hold at once:

1. Total evidence ≥ the bar.
2. At least two doubts bring new information.
3. Those doubts span at least seven days.
4. The cooling period is over, or the evidence is at least twice the bar.

Otherwise it is **WATCH** if evidence is at least 60% of the bar, and **HOLD** below that. Every number lives in one `Policy` dataclass in `temporal_paradox_resolver/commitment.py`, so you can tune it openly instead of quietly lowering your own standards in the moment.

---

## Optional AI features

Paste a key in the app's ⚙️ Settings, or set `GEMINI_API_KEY` in your environment or in a local `.env` file (see `.env.example`), to get richer text for `whatif`, `defend` and `plan`. The model defaults to `gemini-3.5-flash` and can be changed with `TPR_GEMINI_MODEL`.

Without a key, all three still work, with offline answers built from your own notes. **The AI never decides whether you hold or reverse.** That stays deterministic on purpose.

Never commit a real API key. Keep it in your environment or in a local `.env` file, which `.gitignore` already excludes.

---

## Project layout

```
temporal-paradox-resolver/
├── app.py                          # Streamlit web app
├── temporal_paradox_resolver/
│   ├── commitment.py               # the commitment engine: scoring, verdicts, lock, reaffirm, reverse
│   ├── models.py                   # DecisionRecord, Commitment, Doubt, Tripwire, Event
│   ├── store.py                    # SQLite storage (also imports databases from the first version)
│   ├── motivation.py               # daily messages, milestones, check-ins and streaks
│   ├── advisor.py                  # the honest, unbiased second opinion
│   ├── llm.py                      # optional Gemini features with offline fallbacks
│   ├── settings.py                 # saves your key to a local, git-ignored .env file
│   ├── cli.py                      # the `tpr` command
│   └── __main__.py                 # `python -m temporal_paradox_resolver`
├── tests/                          # pytest suite for the engine, storage and CLI
├── pyproject.toml
├── requirements.txt
└── .env.example
```

Databases created by the first version of this project are imported automatically the first time you open them.

---

## Running the tests

```bash
pytest
```

The suite checks the behaviour that makes the lock trustworthy: one panicked night never breaks a decision, a single strong doubt is not enough, evidence must persist, the cooling period holds, tripwires always win, reaffirming raises the bar so the same evidence cannot flip you back, and reversal is refused while the verdict is HOLD or WATCH.

---

## Ideas for what comes next

- **Phone notifications** for the daily message, without needing the app open.
- **An accountability partner**: let a trusted friend co-sign tripwires, so triggering one takes two people.
- **Pattern insights**: across many decisions, which doubts turned out to matter and which always faded.
- **Outcome reviews**: at 3, 6 and 12 months, rate how the decision turned out, to calibrate your future conviction.
- **Encrypted export and sync** between devices.
