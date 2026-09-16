# 🪄 Rembg Discord Bot

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-2.3.2%2B-5865F2?logo=discord&logoColor=white)
![rembg](https://img.shields.io/badge/rembg-2.0.50%2B-00C7B7?logo=onnx&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

A friendly little Discord bot that removes the background from any image you upload — right inside your server. ✨ Upload a photo, pick what's in it, and get back a clean transparent PNG in seconds. No websites, no watermarks, no API keys to share with random services.

Under the hood it's powered by [`rembg`](https://github.com/danielgatis/rembg), a popular open-source ML library for background removal, and carefully tuned to squeeze into small free-tier servers through aggressive memory management.

> ⚠️ **Heads up!** This is **not** the `rembg` Python library itself — it's a Discord bot *wrapper* around it. If you're looking for the CLI tool or Python API, head over to [danielgatis/rembg](https://github.com/danielgatis/rembg) instead.

---

## 📑 Table of Contents

- [✨ Features](#-features)
- [🚀 Quickstart](#-quickstart)
- [🎮 Using the Bot](#-using-the-bot)
- [🧠 Models](#-models)
- [⚙️ How It Works](#️-how-it-works)
- [☁️ Deployment](#-deployment)
- [❓ FAQ](#-faq)
- [🤝 Contributing](#-contributing)
- [📁 Project Structure](#-project-structure)
- [📜 License](#-license)

---

## ✨ Features

- **One slash command, zero learning curve** — `/removebg` does everything.
- **Three AI models to choose from** — portraits, product shots, and anime art each get a model that suits them.
- **Optional edge smoothing** — alpha matting cleans up jagged edges around hair and fur.
- **Runs on a free tier** — garbage collection before *and* after every job, plus explicit session teardown, keep RAM usage low enough for 512 MB dynos.
- **Non-blocking by design** — the ML work runs on a worker thread, so the bot stays responsive even mid-job.
- **Everything in one file** — the whole bot is ~140 lines of readable Python in `main.py`.

---

## 🚀 Quickstart

### Prerequisites

- **Python 3.9+** (3.11 recommended)
- A Discord account with permission to add bots to a server
- ~1 GB of free disk space for the ONNX runtime and cached model weights

### 1. Create your Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) → **New Application**.
2. Open the **Bot** tab → **Add Bot** → copy the **token** (keep it secret! 🔑).
3. No special Privileged Gateway Intents are needed — the bot only uses `discord.Intents.default()`.
4. Open **OAuth2 → URL Generator**, select the `bot` and `applications.commands` scopes, then grant **Send Messages** and **Attach Files** permissions. Open the generated URL to invite the bot to your server.

### 2. Clone and install

```bash
git clone https://github.com/Saineeee/Rembg.git
cd Rembg
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

That installs just four dependencies:

| Package                | What it's for                                          |
|------------------------|--------------------------------------------------------|
| `discord.py>=2.3.2`    | Discord gateway client + slash-command framework       |
| `rembg[cpu]>=2.0.50`   | The actual ML background-removal engine (CPU build)    |
| `Pillow>=10.0.0`       | Image I/O used internally by `rembg`                   |
| `python-dotenv>=1.0.0` | Loads your `.env` file during local development        |

### 3. Set your bot token

Create a `.env` file in the project root:

```dotenv
DISCORD_BOT_TOKEN=your_token_here
```

The bot refuses to start without it — there's an explicit guard in `main.py` that exits with a clear log message.

### 4. Run it

```bash
python main.py
```

You'll know it worked when you see:

```
2026-06-27 10:00:00 - BG_Remover_Bot - INFO - Successfully synced 1 command(s).
2026-06-27 10:00:00 - BG_Remover_Bot - INFO - ✅ Bot is online and ready! Logged in as YourBot (ID: ...)
```

> 💡 **First run is slower** — `rembg` downloads the model weights to `~/.u2net/` the first time they're needed (on Windows: `%USERPROFILE%\.u2net\`).

---

## 🎮 Using the Bot

In any channel the bot can see, type `/removebg` and fill in the options:

| Option         | Required | What it does                                                        |
|----------------|----------|---------------------------------------------------------------------|
| `image`        | ✅       | The image attachment to process                                     |
| `subject_type` | ✅       | Tells the bot which AI model fits your image (see [Models](#-models)) |
| `smooth_edges` | ❌       | Enables alpha matting for cleaner edges — slightly slower           |

The bot replies with the result as `nobg_<your-filename>.png` — a transparent PNG ready to use. If something goes wrong (usually an image too heavy for the server's RAM), you'll get a friendly ephemeral error instead of silence.

> 🧠 **Pro tip:** Start without `smooth_edges`. If the cutout has rough edges around hair or fur, run it again with smoothing enabled — it roughly doubles processing time but refines semi-transparent borders nicely.

---

## 🧠 Models

The bot doesn't expose `rembg`'s entire model zoo — just the three that cover almost every real-world image. Each maps to a choice in the `subject_type` dropdown:

| Choice in Discord             | `rembg` model  | Typical RAM | Best for                                       | Notes                                        |
|-------------------------------|----------------|-------------|------------------------------------------------|----------------------------------------------|
| ℹ️ **Person / Complex**       | `u2net`        | ~176 MB     | Portraits, hair, busy backgrounds              | Highest quality, slowest of the three        |
| ℹ️ **Object / Simple**        | `u2netp`       | ~40 MB      | Product shots, isolated objects, clean scenes  | Lightweight `u2net` variant, noticeably faster |
| ℹ️ **Anime / Illustration**   | `isnet-anime`  | ~80 MB      | Drawings, anime, flat-color art                | Trained on illustrations, not photos         |

### Edge smoothing (alpha matting)

When `smooth_edges` is enabled, the bot calls `rembg.remove()` with these fixed parameters:

```python
alpha_matting=True
alpha_matting_foreground_threshold=240
alpha_matting_background_threshold=10
alpha_matting_erode_size=10
```

This works great for photos with semi-hard edges — hair against a bright sky, fur against a flat wall. For product shots on a clean backdrop, skip it: the standard pass is faster and looks just as good.

### Want more models?

Adding one is a two-line change. Edit the `@app_commands.choices(...)` decorator in `main.py` and map a friendly label to any model name from the upstream [`rembg` model list](https://github.com/danielgatis/rembg#available-models). Restart the bot and the new option appears in the dropdown automatically.

---

## ⚙️ How It Works

The whole bot fits in one file, organized like this:

```
BackgroundBot (commands.Bot)
  ├── setup_hook()              # registers the cog, syncs slash commands to Discord
  ├── on_ready()                # logs the bot identity
  └── BackgroundRemoverCog
        ├── process_image()     # synchronous ML work, runs on a worker thread
        └── /removebg           # async entry point: defer → process → reply
```

**Life of a `/removebg` request:**

1. **Validation** — the bot checks that the attachment's content type starts with `image/`, rejecting anything else with an ephemeral warning.
2. **Defer** — Discord kills interactions that take more than 3 seconds, so the bot immediately responds with a "Bot is thinking…" state via `defer()`.
3. **Read** — the attached image is read into memory as raw bytes.
4. **Offload** — `asyncio.to_thread()` runs the CPU-bound ML pass on a worker thread, keeping the event loop (and the Discord heartbeat) alive.
5. **Process** — inside `process_image()`: `gc.collect()` → `rembg.new_session(model)` → `rembg.remove(...)` → `del session` → `gc.collect()` again.
6. **Deliver** — the output is wrapped as `nobg_<original>.png` and sent as a follow-up message.
7. **Recover** — any exception is logged with a full traceback, and the user gets an ephemeral error explaining the likely cause.

That step-5 memory discipline is the secret sauce 🧪 — it's what lets the bot survive repeated use on a 512 MB free dyno instead of getting OOM-killed after a few requests.

---

## ☁️ Deployment

The repo ships with a `Procfile` declaring a single `worker` process:

```procfile
worker: python main.py
```

### Heroku

```bash
heroku create my-rembg-bot
heroku config:set DISCORD_BOT_TOKEN=your_token_here
git push heroku main
heroku ps:scale worker=1
```

> ⚠️ **Use `worker`, not `web`.** There's no HTTP server here — Heroku will crash a `web` dyno that fails to bind a port within 60 seconds.

### Other platforms (Render, Fly.io, Railway…)

Any PaaS that understands a `Procfile` works out of the box. On platforms without Procfile support, just set the start command to `python main.py` and add `DISCORD_BOT_TOKEN` in the dashboard.

### How much RAM do you need?

| Tier       | RAM    | Experience                                                      |
|------------|--------|------------------------------------------------------------------|
| Free / Eco | 512 MB | Works, but very large images with `u2net` may trigger restarts  |
| Basic      | 1 GB   | Comfortable for all three models                                |
| Standard   | 2 GB+  | Handles concurrent requests without breaking a sweat            |

Note that the bot doesn't queue jobs — two simultaneous `/removebg` calls run in parallel on the default thread pool, which can briefly double peak RAM usage.

---

## ❓ FAQ

**The slash command doesn't show up in Discord.**
Commands sync *globally* in `setup_hook`, which can take up to an hour to propagate. For instant syncing while developing, use `await self.tree.sync(guild=discord.Object(id=YOUR_GUILD_ID))` instead.

**"Successfully synced 0 command(s)" — is that bad?**
Nope! It means the command tree was already in sync from a previous run. You'll see `1` only on the first launch after changing the command definition.

**The first invocation takes 30+ seconds, then works fine.**
That's the model download. On platforms with ephemeral filesystems (like Heroku), weights re-download on every deploy unless you attach a persistent volume or bake them into a Docker image.

**The bot restarts mid-request / users see the "too heavy" error.**
That's an OOM-kill. In order of impact: switch to the `u2netp` model (~40 MB vs ~176 MB), resize very large source images, or upgrade to 1 GB+ of RAM.

**The output has jagged edges around hair.**
Run the command again with `smooth_edges` enabled — alpha matting exists exactly for this.

**I want to process images in Python without Discord.**
You want the upstream [`rembg`](https://github.com/danielgatis/rembg) library — this repo just wraps it for Discord.

---

## 🤝 Contributing

This project is intentionally tiny, which makes it a great first contribution! 🎉

### Dev setup

```bash
git clone https://github.com/Saineeee/Rembg.git
cd Rembg
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# create .env with DISCORD_BOT_TOKEN (a dedicated test bot is safest)
python main.py
```

### Ideas worth exploring

- 🎨 Background replacement (solid color / custom image) instead of just transparency
- 📦 Batch processing for multiple attachments in one command
- 🗯️ A `!prefix` fallback command alongside the slash command
- 💾 Persistent model cache volume for faster cold starts on PaaS deploys

### Guidelines

1. Fork the repo and create a feature branch.
2. Keep the single-file philosophy unless the change genuinely demands a package layout — if it does, split `BackgroundRemoverCog` into a `cogs/` package and keep `main.py` a thin launcher.
3. Test with a real bot in a test server before opening a PR.
4. Open a Pull Request describing *what* changed and *why*.

---

## 📁 Project Structure

```
Rembg/
├── main.py             # The entire bot — entry point, cog, ML pipeline (~140 lines)
├── requirements.txt    # Four pinned dependencies
├── Procfile            # Heroku-style worker declaration
├── LICENSE.txt         # MIT license
└── README.md           # You are here 🙂
```

No package layout, no tests directory, no config module — on purpose. The bot does one thing, and the whole implementation fits on one screen.

---

## 📜 License

Released under the [MIT License](LICENSE.txt) — Copyright (c) 2026 Saine.

Third-party dependencies keep their own licenses:

- [`rembg`](https://github.com/danielgatis/rembg) — MIT
- [`discord.py`](https://github.com/Rapptz/discord.py) — MIT
- [`Pillow`](https://python-pillow.org/) — HPND
- [`python-dotenv`](https://github.com/theskumar/python-dotenv) — BSD-3-Clause
