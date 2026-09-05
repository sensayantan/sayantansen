# Architecture walkthrough

How this project actually works, file by file, in the order code runs —
written for future-me (or anyone else) who forgets how the pieces connect.

## The cast of files

```
backend/
  generate_news.py   entry point — orchestrates everything below
  config.py           static data: the 7 sections, their preferred sources/rules
  state.py            tracks "since when should we search"
  claude_news.py       does the research, when AI_PROVIDER=anthropic
  openai_news.py       does the research, when AI_PROVIDER=openai
  .env                 real secrets (gitignored, never committed)
  .env.example         template showing which variables exist

data/
  news.json            the ONLY handoff point between backend and frontend
  state.json           last successful run's timestamp

index.html, news.html, blogs.html   the three pages, sharing one nav
assets/css/style.css                 all styling
assets/js/main.js                    nav toggle, footer year (all pages)
assets/js/news.js                    fetches data/news.json, renders news.html
```

The backend is a script you run by hand (or, later, on a schedule). The
frontend is static files served by GitHub Pages. **They never talk to each
other directly** — the backend writes a file, the frontend reads that same
file. That's the entire integration.

## Step by step: what happens when you run `python generate_news.py`

### 1. Load secrets from `.env`

```python
from dotenv import load_dotenv
load_dotenv()
```

This is the *only* line that reads `.env`. It copies `ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, and `AI_PROVIDER` into the process's environment
variables. Nothing else in the codebase opens `.env` directly.

### 2. Pick a provider

```python
from config import AI_PROVIDER, TEXT_SECTIONS

if AI_PROVIDER == "openai":
    from openai_news import research_section
else:
    from claude_news import research_section
```

This one `if` is the entire "switch AI provider" mechanism. Whichever
module wins, its `research_section(section, since_iso)` function is what
gets called for every section — both modules implement the exact same
function signature, so `generate_news.py` doesn't need to know which one
it's using.

### 3. Figure out the search window

`state.py`:

```python
def load_since(force_lookback_days=None):
    if force_lookback_days is not None:
        return (now - timedelta(days=force_lookback_days)).isoformat()
    if STATE_PATH.exists():
        # read data/state.json's last_success_at
        ...
    return (now - timedelta(days=3)).isoformat()   # first-ever run
```

Just date arithmetic and a small JSON file — no network calls yet. The
`--since-days` CLI flag bypasses this entirely, which is why it's useful
for manual testing (otherwise every manual re-run narrows the window to
"since the last run a few minutes ago").

### 4. Loop over sections

```python
for section in TEXT_SECTIONS:      # defined in config.py
    stories = research_section(section, since_iso)
```

`section` is a plain data object from `config.py` (label, preferred
sources, how many stories to aim for, extra guidance). It has no
behavior — all the logic lives in `research_section`.

## Where the actual research (and the API key) happens

This is the part with real behavior. `openai_news.py`:

```python
client = OpenAI()   # reads OPENAI_API_KEY from the environment automatically

def research_section(section, since_iso):
    response = client.responses.create(
        model=MODEL_ID,
        tools=[{"type": WEB_SEARCH_TOOL_TYPE}],   # <- turns on real web search
        instructions=SYSTEM_PROMPT,
        input=_build_user_prompt(section, since_iso),
    )
    final_text = response.output_text
    return _extract_json_array(final_text)
```

Two lines matter most:

- **`client = OpenAI()`** is the only place the API key is used. The
  constructor silently reads `OPENAI_API_KEY` from the environment and
  attaches it to every request as an authorization header. The raw key
  string is never touched anywhere else in this codebase.

- **`tools=[{"type": "web_search_preview"}]`** is the entire mechanism for
  "crawling the web." This project does not write any HTTP-fetching or
  HTML-parsing code itself. This one line tells the provider's servers
  "you may search the internet for this request." The actual searching —
  running queries, fetching real pages — happens on OpenAI's (or
  Anthropic's) infrastructure, not on this machine. `response.output_text`
  comes back already containing, per the prompt's instructions, a JSON
  array of stories with real headlines, summaries, and source URLs.

`claude_news.py` is the same pattern with a different vendor:
`anthropic.Anthropic()` instead of `OpenAI()`, and
`tools=[{"type": "web_search_20260209", ...}]` instead. Same two-line
shape either way.

Both modules then run the model's raw text answer through
`_extract_json_array()`, which pulls out the JSON array even if the model
added a stray sentence around it, and returns a plain Python list of
story dicts.

## Assembling the output file

Back in `generate_news.py`:

```python
sections_out.append({
    "id": section.id, "label": section.label,
    "kicker": section.kicker, "stories": stories,
})
```

...for every section, plus the hardcoded Money/Markets placeholder, then:

```python
NEWS_JSON_PATH.write_text(json.dumps(output, indent=2))
```

writes the whole thing to **`data/news.json`**. The backend's job ends
here. `state.save_success()` then records this run's timestamp to
`data/state.json` — but only if at least one section found something, so
a fully-empty run doesn't narrow tomorrow's search window.

## How the frontend picks it up

Nothing in `news.html` or `news.js` knows anything about Python, Claude,
or OpenAI — only about the shape of `data/news.json`.

`news.html` has empty containers with IDs (`<div id="db-sections">`) and
loads `news.js`.

`assets/js/news.js`:

```javascript
const response = await fetch("data/news.json");
const data = await response.json();
// ...loop over data.sections, build HTML strings, inject with innerHTML
```

## The full chain, end to end

```
terminal (python generate_news.py)
  -> .env loaded (API key becomes an environment variable)
  -> provider module selected (config.AI_PROVIDER)
  -> for each section: real API call, server-side web search, JSON parsed
  -> data/news.json written
  -> data/state.json updated

(separately, manually)
  -> git add/commit/push data/news.json
  -> GitHub Pages redeploys

browser (news.html)
  -> news.js fetches data/news.json
  -> renders the page
```

Two completely separate programs — a Python script that runs occasionally
on a laptop, and a browser page served as static files — that only ever
communicate through one committed JSON file.
