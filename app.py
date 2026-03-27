import os
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

from model.inference import generate_vision_reply
from utils.memory import MemoryStore
from utils.ocr import extract_text

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
MEMORY_FILE = DATA_DIR / "chat_memory.json"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
load_dotenv(BASE_DIR / ".env")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")

memory = MemoryStore(MEMORY_FILE)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_session_id() -> str:
    sid = session.get("sid")
    if not sid:
        sid = str(uuid.uuid4())
        session["sid"] = sid
    return sid


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/uploads/<path:filename>", methods=["GET"])
def uploaded_file(filename: str):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/api/history", methods=["GET"])
def history():
    sid = get_session_id()
    records = memory.get_full_history(sid)
    return jsonify({"messages": records, "session_id": sid})


@app.route("/api/chat", methods=["POST"])
def chat():
    sid = get_session_id()
    message = (request.form.get("message") or "").strip()
    image = request.files.get("image")

    image_path = None
    image_url = None
    ocr_text = ""

    if image and image.filename:
        if not allowed_file(image.filename):
            return jsonify({"error": "Unsupported file type. Use png, jpg, jpeg, webp, or gif."}), 400

        filename = secure_filename(image.filename)
        stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        unique_name = f"{stamp}_{uuid.uuid4().hex}_{filename}"
        image_path = UPLOAD_DIR / unique_name
        image.save(image_path)
        image_url = url_for("uploaded_file", filename=image_path.name)
        ocr_text = extract_text(image_path)

    if not message and not image_path:
        return jsonify({"error": "Please provide text or an image."}), 400

    history = memory.get_history(sid, limit=12)
    answer = generate_vision_reply(
        user_message=message,
        image_path=image_path,
        ocr_text=ocr_text,
        history=history,
    )

    user_payload = message if message else "[Image uploaded]"
    if ocr_text:
        user_payload += f"\n\n[OCR]\n{ocr_text[:500]}"

    memory.append_message(sid, "user", user_payload, image_url=image_url)
    memory.append_message(sid, "assistant", answer)

    return jsonify(
        {
            "reply": answer,
            "ocr_text": ocr_text,
            "image_url": image_url,
            "session_id": sid,
        }
    )


@app.route("/api/reset", methods=["POST"])
def reset_chat():
    sid = get_session_id()
    memory.clear(sid)
    return jsonify({"ok": True})


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=debug)
