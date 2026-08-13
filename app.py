"""
app.py
======
Flask web server for the PII Redaction Tool.
Serves the frontend and handles document upload + redaction via API.

Run locally:
    pip install flask
    python app.py

Deploy to Vercel:
    vercel deploy
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file, abort

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB max upload

# Lazy-load the heavy Presidio engine once on first request
_engine_lock = threading.Lock()
_analyzer = None
_anonymizer = None
_engine_ready = False
_engine_error = None


def _load_engine():
    global _analyzer, _anonymizer, _engine_ready, _engine_error
    try:
        logger.info("Loading Presidio engine…")
        from pii_redactor.engine import build_analyzer, build_anonymizer
        _analyzer = build_analyzer()
        _anonymizer = build_anonymizer()
        _engine_ready = True
        logger.info("Engine ready.")
    except Exception as exc:
        _engine_error = str(exc)
        logger.error("Engine load failed: %s", exc)


# Pre-load in background so first request isn't slow
threading.Thread(target=_load_engine, daemon=True).start()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    return jsonify({
        "ready": _engine_ready,
        "error": _engine_error,
    })


@app.route("/api/redact", methods=["POST"])
def api_redact():
    if not _engine_ready:
        if _engine_error:
            return jsonify({"error": f"Engine failed to load: {_engine_error}"}), 500
        return jsonify({"error": "Engine is still loading. Please wait a few seconds and try again."}), 503

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith(".docx"):
        return jsonify({"error": "Only .docx files are supported."}), 400

    locale = request.form.get("locale", "en_IN")
    seed_str = request.form.get("seed", "42")
    try:
        seed = int(seed_str)
    except ValueError:
        seed = 42

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_dir = Path(tmpdir)
            input_path = tmp_dir / "input.docx"
            output_path = tmp_dir / "redacted.docx"

            file.save(str(input_path))

            t0 = time.time()

            from pii_redactor.consistency import ConsistencyMapper
            from pii_redactor.document import DocxRedactor
            from pii_redactor.operators import FakerOperators

            faker_ops = FakerOperators(locale=locale, seed=seed)
            mapper = ConsistencyMapper()
            redactor = DocxRedactor(
                analyzer=_analyzer,
                anonymizer=_anonymizer,
                faker_operators=faker_ops,
                consistency_mapper=mapper,
            )

            stats = redactor.redact(input_path, output_path)
            elapsed = round(time.time() - t0, 1)

            # Read output into memory before tmpdir is deleted
            redacted_bytes = output_path.read_bytes()

        # Write to a stable temp file for download
        dl_tmp = tempfile.NamedTemporaryFile(
            suffix="_REDACTED.docx", delete=False, dir=tempfile.gettempdir()
        )
        dl_tmp.write(redacted_bytes)
        dl_tmp.close()

        original_name = Path(file.filename).stem
        download_name = f"{original_name}_REDACTED.docx"

        return jsonify({
            "success": True,
            "download_token": Path(dl_tmp.name).name,
            "download_name": download_name,
            "elapsed_seconds": elapsed,
            "stats": {
                "total": stats.total,
                "by_entity": stats.entity_counts,
            },
        })

    except Exception as exc:
        logger.exception("Redaction failed")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/download/<token>")
def api_download(token: str):
    # Security: token must be a filename only, no path traversal
    if "/" in token or "\\" in token or ".." in token:
        abort(400)
    tmp_path = Path(tempfile.gettempdir()) / token
    if not tmp_path.exists():
        abort(404)
    return send_file(
        str(tmp_path),
        as_attachment=True,
        download_name=request.args.get("name", "redacted.docx"),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
