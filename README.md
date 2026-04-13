<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/logo.svg">
    <img alt="Life Optimizer" src="assets/logo.svg" width="600">
  </picture>
</p>

<p align="center">
  <strong>AI-powered activity tracker that runs entirely on your Mac.</strong><br>
  Understands everything you do. Keeps it 100% private.
</p>

<p align="center">
  <a href="#install"><strong>Install</strong></a> &middot;
  <a href="#features"><strong>Features</strong></a> &middot;
  <a href="#how-it-works"><strong>How It Works</strong></a> &middot;
  <a href="#development"><strong>Development</strong></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS%2013%2B-blue?style=flat-square&logo=apple" alt="macOS 13+">
  <img src="https://img.shields.io/badge/python-3.12%2B-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/swift-5.10-F05138?style=flat-square&logo=swift&logoColor=white" alt="Swift 5.10">
  <img src="https://img.shields.io/badge/privacy-100%25%20local-10b981?style=flat-square&logo=shield&logoColor=white" alt="100% Local">
  <img src="https://img.shields.io/badge/license-MIT-gray?style=flat-square" alt="MIT License">
</p>

---

## What is this?

Life Optimizer is a personal analytics system that tracks your Mac activity and uses AI to give you honest, actionable insights about how you spend your time.

It knows which apps you use, which browser tabs you're on, who you're messaging, what files you're editing, and for how long. Then it tells you things like:

```
WORK (6h 12m)
├─ VS Code: 3h 41m (ally-ai repo)
├─ Slack: 1h 22m (#eng-team 32m, DM w/ co-founder 28m)
└─ Chrome - work: 1h 09m (GitHub 20m, Claude 25m)

SOCIAL / DISTRACTION (3h 47m)  ⚠️ above target
├─ Twitter: 2h 03m (DMs 48m, timeline scrolling 1h 15m)
├─ iMessage: 52m (8 conversations)
└─ Instagram: 32m

💡 You lost ~90 minutes to Twitter between coding sessions.
   Your deepest focus block was 9:15-10:40am.
```

**Everything stays on your machine.** Screenshots, messages, browsing history — none of it ever leaves your Mac. The AI analysis uses your existing Claude subscription or runs fully offline with Ollama.

---

## Install

### Download the App

> **[Download Life Optimizer v0.1.0](https://github.com/shauryaagg/life-optimizer/releases/latest)** (macOS 13+, Apple Silicon)

1. Download and unzip `LifeOptimizer-v0.1.0-macOS-arm64.zip`
2. Move `Life Optimizer.app` to Applications
3. Open it — the setup wizard handles everything else

The app will:
- Find Python on your system (or ask you to install it)
- Create an isolated virtual environment
- Install all dependencies automatically
- Walk you through granting permissions
- Start tracking

**That's it.** No terminal commands. No `pip install`. No config files.

### Requirements

- macOS 13 Ventura or later
- Apple Silicon (M1/M2/M3/M4)
- Python 3.12+ (pre-installed on most Macs, or [download here](https://www.python.org/downloads/))
- ~500MB disk space (Python env + dependencies)

### Permissions

The app will ask for these through native macOS dialogs:

| Permission | Why | Required? |
|---|---|---|
| **Accessibility** | Track which app is in the foreground | Yes |
| **Screen Recording** | Take smart screenshots | Yes |
| **Automation** | Read Chrome tabs, Calendar events via AppleScript | Per-app, auto-prompted |

---

## Features

### Spotlight-Style Query Panel

Press **`Cmd + Shift + Space`** anywhere to ask questions about your day:

```
┌──────────────────────────────────────────┐
│ 🔍 how much twitter today               │
├──────────────────────────────────────────┤
│                                          │
│  📊 Twitter Usage Today                  │
│                                          │
│  Total: 1h 47m                           │
│  ├─ Timeline scrolling: 58m             │
│  ├─ DMs: 32m                            │
│  └─ Composing: 17m                      │
│                                          │
│  That's 23% of your active time.         │
│                                          │
└──────────────────────────────────────────┘
```

Ask anything — "What was I doing at 3pm?", "Compare this week to last week", "Who did I message most today?", "How many context switches yesterday?"

### Deep App Tracking

Not just "you used Chrome for 2 hours" — Life Optimizer knows *exactly* what you were doing:

| App | What's Tracked |
|---|---|
| **Chrome / Safari** | Active tab URL + title, time per site, DM detection |
| **Slack** | Workspace, channel, DM partner from window title |
| **VS Code / Cursor** | Active file, project name, time per file |
| **iMessage** | Conversation participants, message timestamps |
| **Calendar** | Today's events, meeting details |
| **Terminal / iTerm** | Working directory, running command |
| **Mail** | Current mailbox, message subject + sender |
| **Any other app** | Window title + focused time |

All data collected via AppleScript/JXA — no kernel extensions, no browser plugins required.

### Smart Screenshots

Screenshots are taken **intelligently**, not on a dumb timer:

- **On every app switch** — captures context transitions (highest information density)
- **Every 30 seconds** as fallback (configurable: 10s - 120s)
- **Compressed** to ~100-150KB JPEG (50% scale, Q60)
- **~140MB/day** storage at default settings
- **Auto-cleanup** after 30 days

### AI-Powered Insights

The LLM pipeline runs locally and generates:

- **Hourly summaries** — what you did each hour
- **Daily reports** — full breakdown with actionable advice
- **Activity categorization** — Deep Work, Communication, Social Media, Entertainment, etc.
- **Behavioral patterns** — context switch frequency, focus block duration, distraction triggers

### Web Dashboard

Full-featured local dashboard at `localhost:8765`:

- **Timeline** — chronological event stream, color-coded by category
- **Reports** — daily summaries, weekly trends, monthly heatmap
- **Focus Timeline** — Gantt-style view of your work sessions
- **Screenshots** — filterable gallery with context
- **Chat** — web-based query interface (fallback for the Spotlight panel)
- **Settings** — configure everything from the browser

### Long-Term Memory

Your activity data is indexed for intelligent recall:

- **Text-to-SQL** — structured queries ("compare deep work Mon vs Fri")
- **Vector search** — semantic queries ("what was I working on when I had that API idea?")
- **Entity tracking** — tracks people, projects, and topics across all your interactions
- **Memory compression** — older data is summarized, keeping insights while saving space

### Chrome Extension

Optional extension for even deeper page context:

- Detects content type (article, video, social feed, code review)
- Extracts social media specifics (DM partner, subreddit, LinkedIn section)
- Detects composing state (are you typing a message?)
- Communicates **only** with `127.0.0.1` — nothing leaves your machine

---

## How It Works

```
┌─────────────────────────────────────────────────────┐
│                  Native macOS App                    │
│  ┌─────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Menubar │  │   Spotlight  │  │   Dashboard   │  │
│  │  Icon   │  │    Panel     │  │  (WKWebView)  │  │
│  └────┬────┘  └──────┬───────┘  └───────┬───────┘  │
│       └──────────────┴──────────────────┘           │
│                      │ HTTP                          │
├──────────────────────┴──────────────────────────────┤
│                  Python Backend                      │
│                                                      │
│  ┌──────────┐  ┌────────────┐  ┌─────────────────┐  │
│  │  Daemon  │  │ Collectors │  │  Screenshots    │  │
│  │  (2s     │→ │ Chrome,    │  │  (app switch +  │  │
│  │  poll)   │  │ Slack, ... │  │   30s timer)    │  │
│  └────┬─────┘  └─────┬──────┘  └────────┬────────┘  │
│       └──────────────┴──────────────────┘           │
│                      │                               │
│  ┌───────────────────┴───────────────────────────┐  │
│  │              SQLite (WAL mode)                 │  │
│  │  events │ sessions │ screenshots │ summaries   │  │
│  └───────────────────┬───────────────────────────┘  │
│                      │                               │
│  ┌───────────────────┴───────────────────────────┐  │
│  │           AI Analysis Pipeline                 │  │
│  │  Claude API │ Claude Code │ Ollama │ Rule-based│  │
│  │  ─────────────────────────────────────────────│  │
│  │  Categorizer │ Summarizer │ Insights │ Query   │  │
│  └───────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### Data Collection (Layer 1 — always on, <1% CPU)

The daemon polls every 2 seconds using lightweight AppleScript/JXA:

```javascript
// Chrome active tab — via JXA, ~80ms per call
var chrome = Application('Google Chrome');
var tab = chrome.windows[0].activeTab();
return { url: tab.url(), title: tab.title() };
```

NSWorkspace notifications provide instant app-switch detection. Combined with the 2-second poll, nothing is missed.

### AI Providers

| Provider | Latency | Cost | Privacy | Setup |
|---|---|---|---|---|
| **Claude Code** (default) | Fast | Uses your subscription | Summaries sent to API | Auto-detected |
| **Claude API** | Fast | Pay per token | Summaries sent to API | Paste API key |
| **Ollama** | Slower | Free | 100% local | Install Ollama |
| **None** | Instant | Free | 100% local | No setup |

Raw data (screenshots, messages, URLs) **never** leaves your Mac regardless of provider. Only structured activity summaries are sent to the AI.

---

## Development

### Quick Start (Python backend only)

```bash
git clone https://github.com/shauryaagg/life-optimizer.git
cd life-optimizer
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Start the daemon (tracks your activity)
life-optimizer start

# In another terminal — start the dashboard
life-optimizer dashboard
# Open http://localhost:8765
```

### Build the macOS App

```bash
cd macos-app
swift build -c release

# Create .app bundle
mkdir -p build/LifeOptimizer.app/Contents/MacOS
cp .build/release/LifeOptimizer build/LifeOptimizer.app/Contents/MacOS/
# (see scripts/ for full bundle creation)
```

### Run Tests

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
# 360 tests
```

### Project Structure

```
life-optimizer/
├── src/life_optimizer/
│   ├── daemon/          # Core event loop + NSWorkspace listener
│   ├── collectors/      # 10 app-specific data collectors
│   ├── screenshots/     # Smart capture + compression
│   ├── storage/         # SQLite + repositories
│   ├── llm/             # Claude / Ollama / rule-based pipeline
│   ├── query/           # Natural language query engine
│   ├── dashboard/       # FastAPI + HTMX web UI
│   ├── permissions/     # macOS permission checker
│   └── cli.py           # CLI entry point
├── macos-app/           # SwiftUI native app
├── chrome-extension/    # Optional Chrome extension
├── tests/               # 360 tests
└── config.yaml          # Configuration
```

### CLI Commands

```bash
life-optimizer start       # Start tracking daemon
life-optimizer dashboard   # Start web dashboard
life-optimizer setup       # Check permissions
life-optimizer status      # Show daemon status
life-optimizer install     # Install as login item
life-optimizer uninstall   # Remove login item
life-optimizer reindex     # Rebuild vector search index
```

---

## Privacy

Life Optimizer is designed with privacy as a hard constraint, not a feature toggle.

- **All data stored locally** in `~/Library/Application Support/LifeOptimizer/`
- **SQLite database** — no cloud, no sync, no telemetry
- **Screenshots stored on disk** — compressed JPEGs, auto-deleted after 30 days
- **AI analysis** — only structured summaries sent to Claude (if using cloud provider). Raw screenshots, message content, and full URLs never leave your machine.
- **Chrome extension** — communicates exclusively with `127.0.0.1`
- **No analytics, no tracking, no phone-home**

Want fully offline? Set `llm.provider: ollama` or `llm.provider: none` in config.

---

## Configuration

All settings live in `config.yaml`:

```yaml
daemon:
  poll_interval: 2.0          # Seconds between polls
  idle_threshold: 300          # Seconds before marking idle

screenshots:
  enabled: true
  interval: 30                 # Seconds between captures
  quality: 60                  # JPEG quality (0-100)
  retention_days: 30           # Auto-delete after N days

llm:
  provider: claude-code        # claude | claude-code | ollama | none
  claude:
    model: claude-sonnet-4-20250514
  ollama:
    model: llama3.1:8b
    base_url: http://localhost:11434

collectors:
  enabled:
    - chrome
    - safari
    - slack
    - terminal
    - vscode
    - calendar
    - finder
    - messages
    - mail
    - generic
```

---

## FAQ

**Will this slow down my Mac?**
No. The daemon uses <1% CPU and ~20MB RAM. It polls via lightweight AppleScript calls every 2 seconds. Screenshots use ~140MB/day of disk.

**Does it work with Arc / Brave / Firefox?**
The generic collector tracks window titles for any app. Deep URL tracking (via JXA) currently supports Chrome and Safari. Arc and Brave use Chromium's AppleScript API and may work with the Chrome collector.

**Can I see what data is being collected?**
Yes. Everything is in a SQLite database you can query directly:
```bash
sqlite3 data/life_optimizer.db "SELECT * FROM events ORDER BY timestamp DESC LIMIT 10"
```

**How do I delete my data?**
```bash
rm -rf ~/Library/Application\ Support/LifeOptimizer/
```

**Is this like Rewind.ai / Limitless?**
Similar concept, different approach. Those tools optimize for **recall** ("what was that thing I saw?"). Life Optimizer optimizes for **behavioral insight** ("am I wasting time?"). It uses structured OS data instead of OCR, and AI summarization instead of raw recording.

---

## License

MIT

---

<p align="center">
  <sub>Built for people who want to understand themselves better.</sub>
</p>
