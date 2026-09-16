# Rembg Bot

> A Discord bot that wipes image backgrounds in seconds — powered by AI.
> Upload a photo, pick the subject type, and get back a clean, transparent PNG.

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-2.x-5865F2?logo=discord&logoColor=white)
![rembg](https://img.shields.io/badge/powered%20by-rembg-00948B)
![License](https://img.shields.io/badge/license-MIT-brightgreen)

---

## About

**Rembg Bot** is a lightweight, single-file Discord bot that brings professional-grade background removal to any server. Instead of fiddling with photo editors, members simply run the `/removebg` slash command, attach an image, and the bot replies with a transparency-ready PNG. Under the hood it leans on [rembg](https://github.com/danielgatis/rembg), an industry-standard library built on the U²-Net and ISNet salient-object-detection models, so cutouts are surprisingly clean — even around tricky areas like hair and product edges.

Despite being a single Python file, the bot is built with production habits in mind. Heavy inference work is offloaded to a worker thread so the Discord event loop never blocks, garbage collection runs around every job to keep RAM predictable on small dynos and VPS boxes, and structured logging records each request for easy debugging. It deploys anywhere Python runs, and ships with a `Procfile` for one-command hosting on Heroku.

## Features

- **One-command background removal** — `/removebg` accepts any image attachment and returns a transparent PNG named `nobg_<filename>.png`, with no watermarks and no sign-ups.
- **Three selectable AI models** — a native Discord dropdown lets users match the model to the content: people and complex scenes, simple objects, or anime and illustrations.
- **Optional edge smoothing** — a `smooth_edges` toggle enables alpha matting, which softens jagged cutout edges for a more natural finish (at a small speed cost).
- **Non-blocking async design** — image processing runs in a separate thread via `asyncio.to_thread`, so the bot stays responsive to other users while a job is running.
- **Memory-conscious pipeline** — the rembg session is created per request, explicitly destroyed afterward, and `gc.collect()` is called before and after each job to keep memory footprints flat.
- **Input validation & friendly errors** — non-image uploads are rejected early with an ephemeral warning, and failures surface as private messages instead of spamming the channel.
- **Slash-command native** — built on discord.py 2.x application commands with automatic global syncing on startup; no prefix commands to memorize.

## How It Works

The entire bot lives in `main.py` and follows a clean, linear pipeline:

1. **Startup** — `BackgroundBot` loads the token from the environment, registers the `BackgroundRemoverCog`, and syncs the slash-command tree with Discord in `setup_hook()`.
2. **Request** — a user runs `/removebg` with an attachment. The bot validates the MIME type, then defers the interaction ("Thinking…") since inference takes a few seconds.
3. **Inference** — the image bytes are passed to `process_image()` in a worker thread. A fresh rembg session is opened with the chosen model, `remove()` produces the cutout, and alpha matting is applied only if requested.
4. **Cleanup & reply** — the session is deleted, garbage collection runs, and the result is wrapped in `io.BytesIO` and sent back to the channel as a PNG, mentioning the requester.
5. **Failure handling** — any exception is logged with a full traceback and reported to the user as an ephemeral error message, which also hints at RAM limits if the host ran out of memory.

## AI Models

The `subject_type` dropdown picks the segmentation model. Choosing well makes a visible difference in quality and speed:

| Dropdown choice    | Model          | Best for                                        | Model size | Speed    |
| ------------------ | -------------- | ----------------------------------------------- | ---------- | -------- |
| Person / Complex   | `u2net`        | People, pets, detailed real-world photos        | ~176 MB    | Standard |
| Object / Simple    | `u2netp`       | Everyday objects, products, quick edits         | ~4.5 MB    | Fastest  |
| Anime / Illustration | `isnet-anime` | Anime characters, manga art, drawn illustrations | ~170 MB   | Standard |

**About `smooth_edges` (alpha matting):** when enabled, the bot runs an additional matting pass with a foreground threshold of 240, a background threshold of 10, and an erode size of 10. This blending of the foreground boundary is noticeably better for fine detail — hair, fur, glassware, foliage — but adds a few seconds of processing. For hard-edged subjects like logos or product shots on plain backgrounds, the default off position is usually fine.

> Models are downloaded automatically on first use and cached in `~/.u2net/`. Expect a one-time delay (and bandwidth spike) the first time each model is selected.

## Requirements

- **Python 3.10+** with `pip` and `venv`
- **A Discord bot token** — create a free application in the [Discord Developer Portal](https://discord.com/developers/applications) and copy its bot token
- **~1 GB of free RAM** — u2net inference is memory-hungry; small images may squeeze by on 512 MB, but headroom avoids crashes
- **Internet access** — required on first run to download model weights, and always, for the Discord gateway

## Local Setup

1. **Clone the repository and enter the folder:**

   ```bash
   git clone https://github.com/Saineeee/Rembg.git
   cd Rembg
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   ```

3. **Install the dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file** in the project root (the token is read via `python-dotenv`):

   ```env
   DISCORD_BOT_TOKEN=your_bot_token_here
   ```

5. **Invite the bot to your server.** In the Developer Portal's OAuth2 URL Generator, select the `bot` and `applications.commands` scopes, then use a URL like:

   ```
   https://discord.com/api/oauth2/authorize?client_id=YOUR_APPLICATION_ID&permissions=0&scope=bot+applications.commands
   ```

   The bot only needs **Send Messages** and **Attach Files** permissions in the channels where it will be used.

6. **Run it:**

   ```bash
   python main.py
   ```

   On success, the console prints `Bot is online and ready!`, and the first `/removebg` call downloads the selected model (see the note above). Slash commands can take a few minutes to appear globally after the first launch — this is normal Discord behavior.

## Deploying to Heroku

The repo ships with a `Procfile` that defines a `worker` process, so Heroku deployment is only a handful of commands once the [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) is installed and you are logged in (`heroku login`):

```bash
# 1. Create the app (this also adds the 'heroku' git remote)
heroku create your-app-name

# 2. Store the bot token as a config var — never commit it
heroku config:set DISCORD_BOT_TOKEN=your_bot_token_here

# 3. Push the code
git push heroku main

# 4. Boot the worker defined in the Procfile
heroku ps:scale worker=1
```

Watch the logs to confirm startup and model downloads with `heroku logs --tail`.

**Two hosting notes worth knowing:**

- **RAM limits.** Basic and Standard-1x dynos offer 512 MB, which is tight for u2net on large images. When memory is exhausted, the dyno is restarted mid-job — users will see the bot's own hint that "the image was too heavy for the server's RAM." A 1 GB+ dyno (Standard-2x) gives comfortable headroom.
- **Ephemeral model cache.** Heroku's filesystem is wiped on every restart and dyno cycling, so the model files in `~/.u2net/` are re-downloaded after each restart. This adds a one-time latency after deploys, but costs nothing otherwise.

## Using the Bot

Type `/removebg` in any channel the bot can see, and fill in the parameters:

| Parameter      | Required | Description                                                                 |
| -------------- | -------- | --------------------------------------------------------------------------- |
| `image`        | Yes      | The image attachment to process (PNG, JPG, WebP, and other common formats)  |
| `subject_type` | Yes      | Dropdown that selects the AI model — see the [model table](#ai-models)       |
| `smooth_edges` | No       | Enables alpha matting for softer edges (default: off)                        |

A typical exchange: attach a portrait, choose **Person / Complex**, flip `smooth_edges` on for hair detail, and hit Enter. The bot shows "Thinking…" while it works, then replies with `nobg_<filename>.png` and a confirmation message that names the model used. Invalid uploads are answered privately (ephemerally), so channels stay clean.

## Project Structure

```
Rembg/
├── main.py            # The entire bot — gateway client, slash command, image pipeline
├── requirements.txt   # Python dependencies (discord.py, rembg, Pillow, python-dotenv)
├── Procfile           # Heroku process definition (worker dyno)
├── LICENSE.txt        # MIT License
└── README.md          # You are here
```

## Acknowledgements

- [rembg](https://github.com/danielgatis/rembg) by Daniel Gatis — the background-removal engine doing the heavy lifting
- [discord.py](https://github.com/Rapptz/discord.py) — the Discord API library this bot is built on
- [U²-Net](https://github.com/xuebinqin/U-2-Net) and [DIS/ISNet](https://github.com/xuebinqin/DIS) — the research behind the segmentation models

## License

Released under the [MIT License](LICENSE.txt) — free to use, modify, and self-host. Copyright © 2026 Saine.
