# AnkiSketchy

Local Python app for turning labeled Sketchy-style images into Anki decks.

## What it does

- Lets you upload images in the browser and label symbols on them.
- Builds an Anki deck from the labeled content.
- Keeps the uploaded images in the browser until you click **Build Anki deck**.

## Run it

```bash
python3 sketchy_anki_app.py
```

Then open the localhost URL printed in the terminal. By default the app runs on `127.0.0.1:8765`.

## Requirements

- Python 3.11 or newer recommended.
- No external Python packages are required for the app itself.

## Notes

- The generated deck is written temporarily on the Python side.
- The app is designed to be run locally.