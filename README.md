# ImageSeeker (Python + Web UI)

ImageSeeker is a simple AI vision chatbot with:
- Python backend (Flask)
- Web UI (HTML/CSS/JavaScript)
- Drag-and-drop image upload + text chat
- Multi-turn conversation
- OCR support (optional)
- Saved chat history in `data/chat_memory.json`

## Setup

```bash
python -m venv .venv
# Windows
./.venv/Scripts/activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

Create `.env` from `.env.example`:

```env
AI_API_KEY=your_api_key_here
AI_MODEL=gpt-4.1
AI_BASE_URL=
AI_USE_CHAT_COMPLETIONS=false
FLASK_SECRET_KEY=replace_with_random_string
FLASK_DEBUG=true
PORT=5000
```

Notes:
- If using OpenAI directly, leave `AI_BASE_URL` empty.
- If using a third-party OpenAI-compatible provider, set `AI_BASE_URL` and usually set `AI_USE_CHAT_COMPLETIONS=true` for better image compatibility.
- Legacy `OPENAI_*` env names are still accepted as fallback.

## Run

```bash
python app.py
```

Open `http://localhost:5000`.

## OCR

`pytesseract` is optional. Install Tesseract engine if you want OCR:
- Windows: install Tesseract OCR and add it to PATH.
- macOS: `brew install tesseract`
- Ubuntu/Debian: `sudo apt install tesseract-ocr`
