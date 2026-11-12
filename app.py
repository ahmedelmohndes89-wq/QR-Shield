from flask import Flask, render_template, request, jsonify
import sqlite3
import re
import ipaddress
from urllib.parse import urlparse
from datetime import datetime, timezone

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
DATABASE = "qr_shield.db"

SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly",
    "is.gd", "buff.ly", "cutt.ly", "shorturl.at"
}
SUSPICIOUS_WORDS = {
    "login", "verify", "verification", "account", "secure",
    "update", "password", "wallet", "banking", "confirm",
    "free-gift", "prize", "claim", "suspended"
}


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                summary TEXT NOT NULL,
                scanned_at TEXT NOT NULL
            )
        """)


def analyze_content(content):
    """Heuristic checks only. This does not prove that a URL is safe or malicious."""
    content = (content or "").strip()
    findings = []
    score = 0
    parsed = None

    if not content:
        return {
            "risk_score": 0,
            "risk_level": "Unknown",
            "summary": "No QR content was provided.",
            "findings": ["The QR code did not contain readable content."],
            "is_url": False,
        }

    # A QR code may contain plain text rather than a URL.
    candidate = content
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", candidate):
        if re.match(r"^(www\.)?[^/\s]+\.[a-zA-Z]{2,}([/:?#].*)?$", candidate):
            candidate = "https://" + candidate

    try:
        parsed = urlparse(candidate)
    except ValueError:
        parsed = None

    is_url = bool(parsed and parsed.hostname and parsed.scheme in {"http", "https"})

    if not is_url:
        return {
            "risk_score": 10,
            "risk_level": "Low",
            "summary": "This QR code contains text, not a standard web URL.",
            "findings": [
                "No website was opened or contacted.",
                "Treat unexpected requests for passwords, payment, or personal data with caution."
            ],
            "is_url": False,
        }

    host = (parsed.hostname or "").lower().rstrip(".")
    try:
        parsed.port  # Accessing this can raise ValueError for malformed ports.
    except ValueError:
        score += 20
        findings.append("The URL contains an invalid port number.")

    if parsed.scheme != "https":
        score += 15
        findings.append("The URL does not use HTTPS encryption.")

    if "@" in parsed.netloc:
        score += 25
        findings.append("The URL contains '@', which can disguise the actual destination.")

    try:
        ipaddress.ip_address(host)
        score += 25
        findings.append("The website uses a raw IP address instead of a normal domain name.")
    except ValueError:
        pass

    if host.startswith("xn--") or ".xn--" in host:
        score += 20
        findings.append("The domain uses internationalized/punycode characters.")

    labels = host.split(".")
    if len(labels) >= 5:
        score += 10
        findings.append("The domain has an unusually large number of subdomains.")

    if host in SHORTENERS:
        score += 20
        findings.append("This is a URL-shortening domain, so the final destination is hidden.")

    lowered = candidate.lower()
    matched_words = sorted(word for word in SUSPICIOUS_WORDS if word in lowered)
    if matched_words:
        score += min(25, 5 * len(matched_words))
        findings.append("The URL contains potentially deceptive terms: " + ", ".join(matched_words) + ".")

    if len(candidate) > 120:
        score += 10
        findings.append("The URL is unusually long.")

    if not findings:
        findings.append("No obvious warning signs were detected by the basic checks.")

    score = min(score, 100)
    if score >= 60:
        level = "High"
        summary = "Several warning signs were found. Do not open this link unless you can verify it independently."
    elif score >= 30:
        level = "Medium"
        summary = "Some warning signs were found. Check the destination carefully before proceeding."
    else:
        level = "Low"
        summary = "Few warning signs were found by these basic checks. This is not a guarantee that the link is safe."

    return {
        "risk_score": score,
        "risk_level": level,
        "summary": summary,
        "findings": findings,
        "is_url": True,
        "url": candidate,
        "host": host,
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.post("/api/analyze")
def analyze():
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    if not isinstance(content, str) or len(content) > 5000:
        return jsonify({"error": "Invalid QR content. Maximum length is 5,000 characters."}), 400

    result = analyze_content(content)
    scanned_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with get_db() as db:
        db.execute(
            """INSERT INTO scans (content, risk_score, risk_level, summary, scanned_at)
               VALUES (?, ?, ?, ?, ?)""",
            (content[:5000], result["risk_score"], result["risk_level"],
             result["summary"], scanned_at)
        )

    result["scanned_at"] = scanned_at
    return jsonify(result)


@app.get("/api/history")
def history():
    with get_db() as db:
        rows = db.execute(
            "SELECT id, content, risk_score, risk_level, scanned_at FROM scans ORDER BY id DESC LIMIT 20"
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/stats")
def stats():
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) AS n FROM scans").fetchone()["n"]
        high = db.execute("SELECT COUNT(*) AS n FROM scans WHERE risk_level = 'High'").fetchone()["n"]
        medium = db.execute("SELECT COUNT(*) AS n FROM scans WHERE risk_level = 'Medium'").fetchone()["n"]
    return jsonify({"total": total, "high": high, "medium": medium})


@app.post("/api/history/clear")
def clear_history():
    with get_db() as db:
        db.execute("DELETE FROM scans")
    return jsonify({"message": "Scan history cleared."})


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "The uploaded request is too large."}), 413


init_db()

if __name__ == "__main__":
    app.run(debug=True)
