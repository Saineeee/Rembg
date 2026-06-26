# Rembg — Discord Background Removal Bot

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-2.3.2%2B-5865F2?logo=discord&logoColor=white)
![rembg](https://img.shields.io/badge/rembg-2.0.50%2B-00C7B7?logo=onnx&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active-success)

A lightweight Discord bot that removes the background from any image you upload, directly inside a server. Powered by the [`rembg`](https://github.com/danielgatis/rembg) ML library and tuned to run on small free-tier dynos (Heroku, Render, Fly.io) through aggressive memory management.

> ⚠️ **Not the `rembg` Python library.** This repository is a Discord bot *wrapper* around that library. If you are looking for the CLI/Python API, see [danielgatis/rembg](https://github.com/danielgatis/rembg).

---

## Table of Contents

- [What It Does](#what-it-does)
- [Quickstart](#quickstart)
- [Models & Configuration](#models--configuration)
- [How It Works](#how-it-works)
- [Deployment](#deployment)
- [FAQ / Troubleshooting](#faq--troubleshooting)
- [Project Structure](#project-structure)
- [License](#license)

---

## What It Does

`Rembg` is a single-file Discord bot that exposes one slash command: `/removebg`. A user uploads an image, picks what kind of subject is in it, and the bot replies with the same image — background erased, transparency applied — as a PNG attachment. No website to visit, no API key to share, no file size limit beyond Discord's own attachment cap (currently 25 MB for most servers).

The bot is designed around three constraints that show up repeatedly in small Discord bot projects:

1. **Free-tier RAM is scarce.** The ML models used by `rembg` weigh between roughly 40 MB and 176 MB resident. On a 512 MB Heroku dyno (or similar), naive invocation will OOM-kill the process within a few requests. `Rembg` runs `gc.collect()` before *and* after each job, explicitly destroys the ONNX session, and ships a fallback error message that explains RAM-related restarts to the end user.
2. **Discord enforces a 3-second interaction deadline.** Background removal takes longer than that, so the bot defers the response with a "thinking…" state, then delivers the result as a follow-up. The CPU-bound ML work is offloaded to a worker thread via `asyncio.to_thread` so the Discord gateway heartbeat never stalls.
3. **Different subjects need different models.** A portrait, a product photo, and an anime illustration all have different edge characteristics. The bot lets the user choose between three pre-wired models so the result is optimal without exposing them to the model zoo directly.

---

## Quickstart

### Prerequisites

- **Python 3.9+** (3.11 recommended)
- A Discord account with permission to create bots in the target server
- ~1 GB free disk for the ONNX runtime and cached model weights

### 1. Create the Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) → **New Application**.
2. Open the **Bot** tab → **Add Bot** → copy the **token**.
3. Under **Privileged Gateway Intents**, no special intents are required — the bot uses only `discord.Intents.default()`.
4. Open **OAuth2 → URL Generator**, select scopes `bot` and `applications.commands`, then permissions `Send Messages` and `Attach Files`. Open the generated URL to invite the bot to your server.

### 2. Clone and install

```bash
git clone https://github.com/Saineeee/Rembg.git
cd Rembg
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` pins four packages:

| Package            | Purpose                                              |
|--------------------|------------------------------------------------------|
| `discord.py>=2.3.2`| Discord gateway client and slash-command framework   |
| `rembg[cpu]>=2.0.50`| The actual ML background-removal engine (CPU build) |
| `Pillow>=10.0.0`   | Image I/O used internally by `rembg`                 |
| `python-dotenv>=1.0.0` | Loads `.env` for local development               |

### 3. Set your bot token

Create a `.env` file in the project root:

```dotenv
DISCORD_BOT_TOKEN=your_token_here
```

The bot will refuse to start if this variable is missing — see the `if not TOKEN: exit(1)` guard in `main.py`.

### 4. Run it

```bash
python main.py
```

On a successful start you will see two log lines:

```
2026-06-27 10:00:00 - BG_Remover_Bot - INFO - Successfully synced 1 command(s).
2026-06-27 10:00:00 - BG_Remover_Bot - INFO - ✅ Bot is online and ready! Logged in as YourBot#1234 (ID: ...)
```

The first run will take longer than subsequent runs because `rembg` downloads the model weights to `~/.u2net/` on first use.

### 5. Use it in Discord

In any channel the bot can see, type `/removebg` and fill in the modal:

| Field          | Required | Description                                                     |
|----------------|----------|-----------------------------------------------------------------|
| `image`        | yes      | The image attachment to process                                 |
| `subject_type` | yes      | Which model to use — see [Models & Configuration](#models--configuration) |
| `smooth_edges` | no       | Enable alpha matting for cleaner edges (slightly slower)        |

The bot replies with the result as `nobg_<original_filename>.png`.

---

## Models & Configuration

The bot does **not** expose every model `rembg` supports. Three are pre-wired into the `subject_type` dropdown because they cover the vast majority of real-world inputs and each has a clearly different strength.

| Choice in Discord        | `rembg` model  | Typical RAM | Best for                                      | Notes                                                     |
|--------------------------|----------------|-------------|-----------------------------------------------|-----------------------------------------------------------|
| 🧑 **Person / Complex**  | `u2net`        | ~176 MB     | Portraits, photos with hair, busy backgrounds | Highest quality, slowest of the three                     |
| 📦 **Object / Simple**   | `u2netp`       | ~40 MB      | Product shots, isolated objects, simple scenes| Lightweight variant of `u2net`, ~4× faster                |
| 🎨 **Anime / Illustration** | `isnet-anime`| ~80 MB      | Drawings, anime, flat-color art               | Trained specifically on illustration data, not photos     |

### Edge smoothing (Alpha Matting)

When `smooth_edges=True`, the bot calls `rembg.remove()` with alpha matting enabled and these fixed parameters:

```python
alpha_matting=True
alpha_matting_foreground_threshold=240
alpha_matting_background_threshold=10
alpha_matting_erode_size=10
```

These thresholds work well for photos with semi-hard edges (hair against a bright sky, fur against a flat wall). For product shots on a clean backdrop you usually do **not** need this — the standard hard-edge pass is faster and visually equivalent. Alpha matting roughly doubles processing time.

### Environment variables

| Variable              | Required | Default | Description                                  |
|-----------------------|----------|---------|----------------------------------------------|
| `DISCORD_BOT_TOKEN`   | yes      | —       | The bot token from the Discord Developer Portal |

There are no other configuration knobs. Model selection, smoothing, and image validation are all driven by the slash-command parameters.

### Changing the available models

To add or swap a model, edit the `@app_commands.choices(...)` decorator on the `remove_background` method in `main.py`. Each `Choice` maps a friendly label shown in Discord to a `rembg` model name. The list of valid model names is documented in the upstream [`rembg` README](https://github.com/danielgatis/rembg#available-models). After changing the choices, restart the bot — the `setup_hook` will re-sync the command tree to Discord on the next launch.

---

## How It Works

The entire bot fits in `main.py` (~140 lines). The structure is:

```
BackgroundBot (commands.Bot)
  └── setup_hook()              # registers the cog, syncs slash commands to Discord
  └── on_ready()                # logs the bot identity
  └── BackgroundRemoverCog
        └── process_image()     # synchronous ML work, runs in a worker thread
        └── /removebg command   # async entry point, defers + streams result back
```

**Request lifecycle for `/removebg`:**

1. Discord sends an interaction. The bot validates that `image.content_type` starts with `image/`. If not, it replies ephemerally with a warning and aborts.
2. The bot calls `interaction.response.defer(thinking=True)` to acknowledge within Discord's 3-second window.
3. The attached image is read into memory as raw bytes via `await image.read()`.
4. `asyncio.to_thread(self.process_image, ...)` runs the CPU-bound ML pass on a thread pool, leaving the event loop free to handle heartbeats and other interactions.
5. Inside `process_image`:
   - `gc.collect()` to reclaim RAM from any prior request
   - `rembg.new_session(model_name)` to instantiate the ONNX session for the chosen model
   - `rembg.remove(...)` with the appropriate parameters
   - `del session` to release the model memory immediately
   - `gc.collect()` again to flush the freed blocks
6. The output bytes are wrapped in a `discord.File` named `nobg_<original>.png` and sent via `interaction.followup.send(...)`.
7. Any exception is logged with traceback and the user receives an ephemeral error explaining that the image may have been too heavy for the server's RAM — a common cause of dyno restarts.

This explicit memory discipline is what lets the bot run on a 512 MB dyno without crashing under repeated use. The first request after a restart is always slower because the model weights must be loaded from disk; subsequent requests benefit from OS-level file caching.

---

## Deployment

The repository includes a `Procfile` with a single `worker` process type, making it Heroku-compatible out of the box:

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

> **Important:** Use `worker`, not `web`. There is no HTTP server to bind a port to, and Heroku will crash a `web` dyno that fails to bind within 60 seconds.

### Render / Fly.io / Railway

The same `worker: python main.py` pattern works on any PaaS that supports a `Procfile`. On platforms without `Procfile` support, set the start command directly to `python main.py` and add the `DISCORD_BOT_TOKEN` environment variable in the dashboard.

### Resource sizing

| Tier              | RAM     | Recommended model default | Notes                                   |
|-------------------|---------|---------------------------|-----------------------------------------|
| Free / Eco        | 512 MB  | `u2netp`                  | Works, but large images with `u2net` may trigger restarts |
| Basic             | 1 GB    | any                       | Comfortable for all three models        |
| Standard          | 2 GB+   | any                       | Handles concurrent requests gracefully  |

The bot is single-process and does not queue requests. If two users invoke `/removebg` at the same time, both `process_image` calls run on the default `asyncio.to_thread` pool concurrently, which can briefly double peak RAM usage.

---

## FAQ / Troubleshooting

### The bot starts but the slash command doesn't show up in Discord

Slash commands are synced globally in `setup_hook`, which can take up to **1 hour** to propagate to all guilds on Discord's side. To force an instant sync for a single test server, replace `await self.tree.sync()` with `await self.tree.sync(guild=discord.Object(id=YOUR_GUILD_ID))` during development.

### "Successfully synced 0 command(s)" on startup

This means the command tree was already in sync from a previous run. It is not an error — the command is still registered. The bot will report `1` only on the first launch after a change to the command definition.

### First invocation takes 30+ seconds then succeeds

This is the model download. `rembg` caches weights under `~/.u2net/` (or `%USERPROFILE%\.u2net\` on Windows). On a fresh dyno with no persisted filesystem, the download repeats on every deploy. To avoid this on Heroku, attach a small persistent volume or build the cached weights into a Docker image.

### The bot restarts mid-request and the user gets the "image was too heavy" error

This is an OOM-kill. Mitigations, in order of impact:

1. Switch the user to the `u2netp` model (40 MB vs 176 MB resident).
2. Resize very large source images before processing (e.g. >4000px on the long edge).
3. Upgrade the dyno to one with 1 GB+ RAM.
4. Set `MAX_WORKERS=1` if you implement a custom thread pool, to prevent concurrent jobs.

### Discord returns "The application did not respond"

This appears when the interaction expired before the bot could call `defer()`. It should not happen in normal operation because `defer()` is the first `await` after validation. If it does, check that your network connection to Discord's gateway is stable and that the bot has not been rate-limited.

### Output image has rough / jagged edges around hair

Ask the user to invoke the command again with `smooth_edges=True`. This enables alpha matting, which refines semi-transparent borders at the cost of roughly 2× processing time.

### I want to add a new model

Edit the `@app_commands.choices(subject_type=[...])` list in `main.py`. Each entry maps a Discord-visible label to a `rembg` model name. The full list of valid model names is in the upstream [`rembg` documentation](https://github.com/danielgatis/rembg#available-models). Restart the bot after saving — `setup_hook` will re-sync the command tree.

### I want to process images programmatically without Discord

You are looking for the upstream [`rembg`](https://github.com/danielgatis/rembg) library, not this bot. This repository depends on `rembg` but only exposes it through Discord's slash-command interface.

---

## Project Structure

```
Rembg/
├── main.py             # Bot entry point — all logic in a single file (~140 lines)
├── requirements.txt    # Four pinned dependencies
├── Procfile            # Heroku-style worker declaration
└── README.md           # This file
```

There is intentionally no package layout, no tests directory, and no config module. The bot does one thing and the entire implementation fits in one screen of source. If you need to extend it — add commands, persistence, logging hooks — the recommended starting point is to split `BackgroundRemoverCog` into a `cogs/` package and keep `main.py` as a thin launcher.

---

## License

This project does not currently declare a license in the repository. All third-party dependencies retain their own licenses:

- [`rembg`](https://github.com/danielgatis/rembg) — MIT
- [`discord.py`](https://github.com/Rapptz/discord.py) — MIT
- [`Pillow`](https://python-pillow.org/) — HPND
- [`python-dotenv`](https://github.com/theskumar/python-dotenv) — BSD-3-Clause

If you intend to fork or redistribute this code, add a `LICENSE` file to the repository root before doing so.
