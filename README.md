# AnkiSketchy

Local Python app for turning labeled Sketchy-style images into Anki decks.

## What it does

- Lets you upload images in the browser and label symbols on them.
- Can ask an OpenAI vision model to suggest crop centers for clearly numbered symbols.
- Builds an Anki deck from the labeled content.
- Keeps the uploaded images in the browser until you click **Build Anki deck**.

## Run it

```bash
python3 sketchy_anki_app.py
```

Then open the localhost URL printed in the terminal. By default the app runs on `127.0.0.1:8765`.

## AI crop detection

The manual crop-clicking flow works without any API key. To enable **AI auto-detect crops**, set an OpenAI API key before starting the app:

```bash
export OPENAI_API_KEY="your_api_key_here"
python3 sketchy_anki_app.py
```

The app sends the labeled image and numbered symbol list to the OpenAI Responses API, then applies returned crop suggestions to the matching clean image. Review the crop previews before exporting.

Optional model override:

```bash
export SKETCHY_ANKI_OPENAI_MODEL="gpt-5.5"
```

## Requirements

- Python 3.11 or newer recommended.
- No external Python packages are required for the app itself.

## Notes

- The generated deck is written temporarily on the Python side.
- The app is designed to be run locally.
- AI crop detection sends the labeled image to OpenAI; the non-AI manual workflow keeps uploaded images in the browser until deck build.
