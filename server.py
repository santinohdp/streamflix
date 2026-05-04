"""
StreamFlix Backend v2 - Login + Contenido + Sirve la app web
Requisitos: pip install flask flask-cors
Ejecutar:   python server.py
Luego abrí: http://localhost:5000/app    (la app)
            http://localhost:5000/panel  (el panel admin)
"""

from flask import Flask, request, jsonify, send_file, redirect
from flask_cors import CORS
import json, os, hashlib, secrets
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

USERS_FILE   = "users.json"
CONTENT_FILE = "content.json"
ADMIN_KEY    = "admin1234"       # ← CAMBIÁ ESTO

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════
#  SERVIR ARCHIVOS HTML
# ═══════════════════════════════════════════

@app.route("/")
def index():
    return redirect("/app")

@app.route("/app")
def serve_app():
    return send_file(os.path.join(BASE_DIR, "app.html"))

@app.route("/panel")
def serve_panel():
    return send_file(os.path.join(BASE_DIR, "panel.html"))

# ═══════════════════════════════════════════
#  BASE DE DATOS
# ═══════════════════════════════════════════

def load_users():
    if not os.path.exists(USERS_FILE):
        return {"users": {}, "tokens": {}}
    with open(USERS_FILE) as f:
        return json.load(f)

def save_users(db):
    with open(USERS_FILE, "w") as f:
        json.dump(db, f, indent=2)

def load_content():
    if not os.path.exists(CONTENT_FILE):
        return {"movies": {}, "series": {}}
    with open(CONTENT_FILE) as f:
        return json.load(f)

def save_content(db):
    with open(CONTENT_FILE, "w") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def check_admin(req):
    return req.headers.get("X-Admin-Key") == ADMIN_KEY

# ═══════════════════════════════════════════
#  AUTH — PARA LA APP
# ═══════════════════════════════════════════

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"success": False, "message": "Completá usuario y contraseña"}), 400
    db = load_users()
    user = db["users"].get(username)
    if not user:
        return jsonify({"success": False, "message": "Usuario no encontrado"}), 401
    if user["password"] != hash_pw(password):
        return jsonify({"success": False, "message": "Contraseña incorrecta"}), 401
    if not user["active"]:
        return jsonify({"success": False, "message": "Cuenta desactivada"}), 403
    if user.get("expires") and datetime.now() > datetime.fromisoformat(user["expires"]):
        return jsonify({"success": False, "message": "Cuenta vencida"}), 403
    token = secrets.token_hex(32)
    db["tokens"][token] = {"username": username, "created": datetime.now().isoformat()}
    save_users(db)
    return jsonify({"success": True, "token": token, "username": user.get("display_name", username)})

@app.route("/api/verify", methods=["POST"])
def verify():
    token = (request.json or {}).get("token")
    db = load_users()
    if token in db.get("tokens", {}):
        uname = db["tokens"][token]["username"]
        user  = db["users"].get(uname)
        if user and user["active"]:
            return jsonify({"valid": True, "username": user.get("display_name", uname)})
    return jsonify({"valid": False}), 401

@app.route("/api/version", methods=["GET"])
def version():
    return jsonify({"version": "1.0.0", "apk_url": "", "message": ""})

# ═══════════════════════════════════════════
#  CONTENIDO — PARA LA APP
# ═══════════════════════════════════════════

@app.route("/api/links/<media_type>/<int:tmdb_id>", methods=["GET"])
def get_links(media_type, tmdb_id):
    db = load_content()
    key = str(tmdb_id)
    section = "movies" if media_type == "movie" else "series"
    item = db[section].get(key)
    if not item:
        return jsonify({"links": []})
    return jsonify({"links": item.get("links", [])})

@app.route("/api/catalog", methods=["GET"])
def get_catalog():
    db = load_content()
    return jsonify({
        "movie_ids": list(db["movies"].keys()),
        "serie_ids": list(db["series"].keys())
    })

# ═══════════════════════════════════════════
#  ADMIN — USUARIOS
# ═══════════════════════════════════════════

@app.route("/admin/users", methods=["GET"])
def list_users():
    if not check_admin(request): return jsonify({"error": "No autorizado"}), 401
    db = load_users()
    return jsonify({"users": [
        {"username": u, "display_name": d.get("display_name", u),
         "active": d["active"], "expires": d.get("expires"), "created": d.get("created")}
        for u, d in db["users"].items()
    ]})

@app.route("/admin/users", methods=["POST"])
def create_user():
    if not check_admin(request): return jsonify({"error": "No autorizado"}), 401
    data = request.json or {}
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"error": "Usuario y contraseña requeridos"}), 400
    db = load_users()
    if username in db["users"]:
        return jsonify({"error": "El usuario ya existe"}), 409
    days = data.get("days")
    expires = (datetime.now() + timedelta(days=int(days))).isoformat() if days else None
    db["users"][username] = {
        "password": hash_pw(password),
        "display_name": data.get("display_name", username),
        "active": True, "expires": expires,
        "created": datetime.now().isoformat()
    }
    save_users(db)
    return jsonify({"success": True})

@app.route("/admin/users/<username>", methods=["DELETE"])
def delete_user(username):
    if not check_admin(request): return jsonify({"error": "No autorizado"}), 401
    db = load_users()
    if username not in db["users"]: return jsonify({"error": "No encontrado"}), 404
    del db["users"][username]
    save_users(db)
    return jsonify({"success": True})

@app.route("/admin/users/<username>/toggle", methods=["POST"])
def toggle_user(username):
    if not check_admin(request): return jsonify({"error": "No autorizado"}), 401
    db = load_users()
    if username not in db["users"]: return jsonify({"error": "No encontrado"}), 404
    db["users"][username]["active"] = not db["users"][username]["active"]
    save_users(db)
    return jsonify({"success": True, "active": db["users"][username]["active"]})

@app.route("/admin/users/<username>/extend", methods=["POST"])
def extend_user(username):
    if not check_admin(request): return jsonify({"error": "No autorizado"}), 401
    days = (request.json or {}).get("days", 30)
    db = load_users()
    if username not in db["users"]: return jsonify({"error": "No encontrado"}), 404
    db["users"][username]["expires"] = (datetime.now() + timedelta(days=int(days))).isoformat()
    save_users(db)
    return jsonify({"success": True})

# ═══════════════════════════════════════════
#  ADMIN — CONTENIDO
# ═══════════════════════════════════════════

@app.route("/admin/content", methods=["GET"])
def list_content():
    if not check_admin(request): return jsonify({"error": "No autorizado"}), 401
    db = load_content()
    movies = [{"tmdb_id": k, "type": "movie",   **v} for k, v in db["movies"].items()]
    series = [{"tmdb_id": k, "type": "series",  **v} for k, v in db["series"].items()]
    return jsonify({"content": movies + series})

@app.route("/admin/content", methods=["POST"])
def save_item():
    if not check_admin(request): return jsonify({"error": "No autorizado"}), 401
    data = request.json or {}
    tmdb_id    = str(data.get("tmdb_id", ""))
    media_type = data.get("type", "movie")
    title      = data.get("title", "")
    if not tmdb_id or not title:
        return jsonify({"error": "tmdb_id y title requeridos"}), 400
    db = load_content()
    section = "movies" if media_type == "movie" else "series"
    db[section][tmdb_id] = {
        "title": title, "year": data.get("year",""),
        "poster": data.get("poster",""),
        "links": data.get("links", []),
        "updated": datetime.now().isoformat()
    }
    save_content(db)
    return jsonify({"success": True, "message": f"'{title}' guardado con {len(data.get('links',[]))} link(s)"})

@app.route("/admin/content/<media_type>/<tmdb_id>", methods=["GET"])
def get_item(media_type, tmdb_id):
    if not check_admin(request): return jsonify({"error": "No autorizado"}), 401
    db = load_content()
    section = "movies" if media_type == "movie" else "series"
    item = db[section].get(tmdb_id)
    if not item: return jsonify({"error": "No encontrado"}), 404
    return jsonify({"tmdb_id": tmdb_id, "type": media_type, **item})

@app.route("/admin/content/<media_type>/<tmdb_id>", methods=["DELETE"])
def delete_item(media_type, tmdb_id):
    if not check_admin(request): return jsonify({"error": "No autorizado"}), 401
    db = load_content()
    section = "movies" if media_type == "movie" else "series"
    if tmdb_id not in db[section]: return jsonify({"error": "No encontrado"}), 404
    del db[section][tmdb_id]
    save_content(db)
    return jsonify({"success": True})

# ═══════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  StreamFlix corriendo!")
    print("  App:   http://localhost:5000/app")
    print("  Panel: http://localhost:5000/panel")
    print(f"  Clave admin: {ADMIN_KEY}")
    print("="*50 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
