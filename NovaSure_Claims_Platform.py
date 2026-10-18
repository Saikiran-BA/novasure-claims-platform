"""
Secure Product Catalog Web App for AWS 3-Tier Architecture
---------------------------------------------------------
Flask application with:
- Professional login page and post-login application shell
- No public self-registration
- Password hashing (Werkzeug PBKDF2)
- Session-based authentication
- Admin-only user creation and deactivation
- Protected product list and create API
- MySQL/Amazon Aurora support
- CSRF protection for form submissions and state-changing API requests

Install:
    pip install Flask mysql-connector-python

Required environment variables:
    DB_HOST       Aurora writer endpoint
    DB_USER       Database username
    DB_PASSWORD   Database password
    DB_NAME       Database name (default: catalogdb)
    SECRET_KEY    Long random secret (required for production)

Optional first-run administrator bootstrap:
    ADMIN_USERNAME
    ADMIN_PASSWORD

The app creates its tables automatically. If ADMIN_USERNAME and ADMIN_PASSWORD
are set, it creates that admin account if it does not already exist.

For production:
- Set COOKIE_SECURE=1 and serve the site over HTTPS.
- Prefer retrieving DB credentials and SECRET_KEY from AWS Secrets Manager.
- Put the app behind an HTTPS-enabled ALB.
- Do not expose the app port directly to the internet.
"""

import hmac
import os
import re
import secrets
from datetime import timedelta
from functools import wraps

from mysql.connector import IntegrityError
from database import db_connect, execute, init_db, query_all, query_one
from flask import (
    Flask, abort, flash, jsonify, redirect, render_template_string,
    request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash


APP_NAME = os.getenv("APP_NAME", "Northstar Workspace")
SECRET_KEY = os.getenv("SECRET_KEY", "")
APP_ENV = os.getenv("APP_ENV", "development").lower()
# HTTPS cookies default on in production; set COOKIE_SECURE=0 only for local HTTP testing.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "1" if APP_ENV == "production" else "0") == "1"

if APP_ENV == "production" and len(SECRET_KEY) < 32:
    raise RuntimeError(
        "Production requires SECRET_KEY to be set to a long random value "
        "(at least 32 characters). Retrieve it from AWS Secrets Manager."
    )

app = Flask(__name__)
app.secret_key = SECRET_KEY or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=COOKIE_SECURE,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=1 * 1024 * 1024,
    SESSION_REFRESH_EACH_REQUEST=True,
)


@app.after_request
def add_security_headers(response):
    """Add baseline browser protections; deploy behind HTTPS in production."""
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cache-Control", "no-store")
    if APP_ENV == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def enforce_csrf():
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        expected = session.get("_csrf_token", "")
        supplied = request.form.get("_csrf_token", "")
        if request.is_json:
            supplied = request.headers.get("X-CSRF-Token", "")
        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            abort(400, description="Invalid or missing CSRF token.")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            if request.path.startswith("/api/"):
                return jsonify(error="Authentication required"), 401
            return redirect(url_for("login", next=request.full_path))
        user = query_one(
            "SELECT id, username, display_name, role, is_active "
            "FROM app_users WHERE id = %s",
            (user_id,),
        )
        if not user or not user["is_active"]:
            session.clear()
            if request.path.startswith("/api/"):
                return jsonify(error="Account is inactive or unavailable"), 401
            return redirect(url_for("login"))
        request.current_user = user
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if request.current_user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


BASE_STYLE = """
:root{--bg:#0b1020;--panel:#111a2e;--panel2:#17233c;--line:#273653;
--text:#edf3ff;--muted:#9aabc7;--accent:#7c9cff;--accent2:#9a7cff;
--good:#70e1b0;--danger:#ff8e9b}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(ellipse at top,#18274a 0%,#0b1020 55%);
color:var(--text);font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;min-height:100vh}
a{color:#b9c9ff;text-decoration:none}
a:hover{text-decoration:underline}
button,.button{border:0;border-radius:10px;background:linear-gradient(135deg,#7898ff,#9a7cff);
color:#fff;font-weight:700;padding:11px 16px;cursor:pointer;display:inline-block}
button:hover,.button:hover{filter:brightness(1.08);text-decoration:none}
input,select{width:100%;background:#0c1427;border:1px solid #344463;color:var(--text);
padding:12px;border-radius:9px;outline:none}
input:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 3px #7c9cff22}
label{display:block;font-size:13px;color:#b8c6df;margin:14px 0 6px}
.small{font-size:12px;color:var(--muted)}
.muted{color:var(--muted)}
.card{background:#111a2eeF;border:1px solid var(--line);border-radius:18px;
box-shadow:0 18px 60px #0003}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;letter-spacing:.2px}
.brand-mark{height:36px;width:36px;border-radius:11px;display:grid;place-items:center;
background:linear-gradient(135deg,#7898ff,#a47cff);font-size:18px}
.flash{border:1px solid #ff8e9b55;background:#ff8e9b12;color:#ffd5da;padding:10px 12px;
border-radius:10px;margin:12px 0}
"""
LOGIN_TEMPLATE = r"""
<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign in · {{ app_name }}</title><style>""" + BASE_STYLE + r"""
.login-wrap{min-height:100vh;display:grid;grid-template-columns:1.1fr .9fr;max-width:1200px;margin:auto;padding:30px;gap:35px;align-items:center}
.hero{padding:30px 10px 30px 20px}.hero h1{font-size:clamp(36px,5vw,62px);line-height:1.06;letter-spacing:-2px;margin:28px 0 18px}
.gradient{background:linear-gradient(100deg,#fff,#aebfff 55%,#c7aaff);-webkit-background-clip:text;background-clip:text;color:transparent}
.hero p{max-width:500px;color:#a9b8d2;font-size:17px}.eyebrow{color:#aebfff;font-size:12px;letter-spacing:2px;font-weight:800}
.features{display:flex;gap:10px;flex-wrap:wrap;margin-top:30px}.pill{border:1px solid #344463;background:#ffffff08;color:#b9c7df;border-radius:99px;padding:7px 11px;font-size:12px}
.login-card{padding:34px;max-width:430px;width:100%;justify-self:center}
.login-card h2{margin:25px 0 4px;font-size:26px}.login-card p{margin:0;color:var(--muted)}
.login-card button{width:100%;margin-top:22px;padding:13px}
.input-wrap{position:relative}.input-wrap input{padding-right:50px}
.toggle{position:absolute;right:7px;top:7px;background:transparent;color:#aab9d5;padding:6px 8px;font-size:12px}
.secure-note{display:flex;gap:8px;align-items:center;margin-top:20px;color:#94a5c1;font-size:12px}
@media(max-width:780px){.login-wrap{grid-template-columns:1fr;padding:20px}.hero{padding:20px 5px 0}.hero h1{font-size:42px}.login-card{max-width:none}.features{margin-top:18px}}
</style></head><body><main class="login-wrap">
<section class="hero">
<div class="brand"><div class="brand-mark">N</div><span>{{ app_name }}</span></div>
<div class="eyebrow" style="margin-top:65px">YOUR WORKSPACE. YOUR DATA.</div>
<h1>Everything you need.<br><span class="gradient">One secure place.</span></h1>
<p>Sign in to access your workspace, manage your catalog, and keep your team's work connected.</p>
<div class="features"><span class="pill">✦ Secure access</span><span class="pill">◈ Team workspace</span><span class="pill">↗ Live catalog</span></div>
</section>
<section class="card login-card">
<div class="brand"><div class="brand-mark">↗</div><span>Workspace access</span></div>
<h2>Welcome back</h2><p>Enter your credentials to continue.</p>
{% with messages = get_flashed_messages() %}{% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}{% endwith %}
<form method="post" action="{{ url_for('login') }}">
<input type="hidden" name="_csrf_token" value="{{ csrf_token() }}">
<input type="hidden" name="next" value="{{ next_url }}">
<label for="username">Username</label>
<input id="username" name="username" autocomplete="username" required autofocus maxlength="80" placeholder="Enter your username">
<label for="password">Password</label>
<div class="input-wrap"><input id="password" name="password" type="password" autocomplete="current-password" required placeholder="Enter your password">
<button class="toggle" type="button" onclick="const p=document.getElementById('password');p.type=p.type==='password'?'text':'password';this.textContent=p.type==='password'?'Show':'Hide'">Show</button></div>
<button type="submit">Sign in securely&nbsp; →</button>
</form>
<div class="secure-note"><span>🔒</span><span>Authorized users only. Contact your administrator for access.</span></div>
</section></main></body></html>
"""

APP_TEMPLATE = r"""
<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} · {{ app_name }}</title><style>""" + BASE_STYLE + r"""
.layout{display:grid;grid-template-columns:240px 1fr;min-height:100vh}
aside{padding:24px 16px;border-right:1px solid var(--line);background:#0b1222aa}
.side-link{display:block;padding:10px 12px;border-radius:9px;color:#aebbd2;margin:5px 0}
.side-link.active,.side-link:hover{background:#7c9cff18;color:#fff;text-decoration:none}
main{padding:30px;max-width:1200px;width:100%;margin:0 auto}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:15px;margin-bottom:30px}
.panel{padding:22px;margin:18px 0}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.stat{padding:18px;border:1px solid var(--line);border-radius:14px;background:#ffffff05}
.stat strong{display:block;font-size:28px;margin-top:6px}
.row{display:flex;gap:12px;align-items:end;flex-wrap:wrap}
.row>div{flex:1;min-width:160px}
table{width:100%;border-collapse:collapse;margin-top:12px}
th,td{text-align:left;padding:13px 10px;border-bottom:1px solid var(--line)}
th{color:#9faecc;font-size:12px;text-transform:uppercase;letter-spacing:.6px}
.badge{display:inline-block;padding:4px 8px;border-radius:99px;background:#70e1b01a;color:var(--good);font-size:12px}
.danger{background:#ff8e9b18;color:#ffb2bb}
.inline{display:inline}
.inline button{padding:7px 10px;font-size:12px}
@media(max-width:760px){.layout{grid-template-columns:1fr}aside{border-right:0;border-bottom:1px solid var(--line)}main{padding:18px}.grid{grid-template-columns:1fr}.topbar{align-items:flex-start;flex-direction:column}}
</style></head><body><div class="layout">
<aside><div class="brand" style="margin:5px 8px 30px"><div class="brand-mark">N</div><span>{{ app_name }}</span></div>
<div class="small" style="padding:0 12px">WORKSPACE</div>
<a class="side-link {{ 'active' if active == 'dashboard' else '' }}" href="{{ url_for('dashboard') }}">◫ &nbsp; Overview</a>
<a class="side-link {{ 'active' if active == 'products' else '' }}" href="{{ url_for('dashboard') }}#products">▦ &nbsp; Product catalog</a>
{% if user.role == 'admin' %}<a class="side-link {{ 'active' if active == 'users' else '' }}" href="{{ url_for('users_page') }}">♙ &nbsp; User access</a>{% endif %}
<div style="margin-top:50px;border-top:1px solid var(--line);padding:18px 10px">
<div class="small">SIGNED IN AS</div><strong>{{ user.display_name }}</strong><div class="small">{{ user.role|capitalize }}</div>
<form method="post" action="{{ url_for('logout') }}"><input type="hidden" name="_csrf_token" value="{{ csrf_token() }}"><button style="width:100%;margin-top:16px;background:#26334c">Sign out ↗</button></form>
</div></aside>
<main><div class="topbar"><div><div class="small">YOUR WORKSPACE / {{ title|upper }}</div><h1 style="margin:5px 0">{{ title }}</h1><div class="muted">A secure place for your team's work.</div></div><span class="badge">● Session active</span></div>
{% with messages = get_flashed_messages() %}{% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}{% endwith %}
{{ content|safe }}
</main></div></body></html>
"""


def page(title, active, content, **context):
    return render_template_string(
        APP_TEMPLATE, title=title, active=active, content=content,
        app_name=APP_NAME, user=request.current_user, **context
    )


@app.route("/health")
def health():
    # ALB health check only; intentionally does not expose database details.
    return jsonify(status="ok")


@app.route("/")
def root():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = query_one(
            "SELECT id, username, display_name, password_hash, role, is_active "
            "FROM app_users WHERE username = %s",
            (username,),
        )
        if user and user["is_active"] and check_password_hash(
            user["password_hash"], password
        ):
            session.clear()
            session["user_id"] = user["id"]
            session.permanent = True
            csrf_token()
            next_url = request.form.get("next", "")
            # Avoid open redirects: only accept local absolute paths.
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url.split("#", 1)[0])
            return redirect(url_for("dashboard"))
        flash("Sign-in failed. Check your username and password, or contact your administrator.")
    next_url = request.args.get("next", "")
    if not (next_url.startswith("/") and not next_url.startswith("//")):
        next_url = ""
    return render_template_string(
        LOGIN_TEMPLATE, app_name=APP_NAME, next_url=next_url
    )


@app.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/dashboard")
@login_required
def dashboard():
    total_products = query_one("SELECT COUNT(*) AS n FROM products")["n"]
    total_users = 0
    if request.current_user["role"] == "admin":
        total_users = query_one("SELECT COUNT(*) AS n FROM app_users WHERE is_active = TRUE")["n"]
    products = query_all(
        "SELECT id, name, price, created_at FROM products ORDER BY id DESC LIMIT 100"
    )
    rows = "".join(
        "<tr><td>{}</td><td>₹{:.2f}</td><td>{}</td></tr>".format(
            str(p["name"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
            float(p["price"]),
            p["created_at"].strftime("%Y-%m-%d %H:%M") if p["created_at"] else ""
        ) for p in products
    ) or '<tr><td colspan="3" class="muted">No products yet. Add the first one below.</td></tr>'
    content = """
    <div class="grid">
      <div class="stat"><span class="muted">Catalog items</span><strong>{}</strong><span class="small">Stored in Aurora</span></div>
      <div class="stat"><span class="muted">Access level</span><strong style="font-size:22px">{}</strong><span class="small">Role-based permissions</span></div>
      <div class="stat"><span class="muted">Workspace status</span><strong style="font-size:22px;color:var(--good)">Online</strong><span class="small">Authenticated session</span></div>
    </div>
    <section class="card panel" id="products">
      <h2 style="margin-top:0">Add a product</h2>
      <form method="post" action="/products">
        <input type="hidden" name="_csrf_token" value="{}">
        <div class="row"><div><label>Product name</label><input name="name" maxlength="150" required placeholder="e.g. Wireless keyboard"></div>
        <div><label>Price (INR)</label><input name="price" type="number" min="0" step="0.01" required placeholder="799.00"></div>
        <div style="flex:0 0 auto"><button type="submit">Save product +</button></div></div>
      </form>
    </section>
    <section class="card panel"><h2 style="margin-top:0">Product catalog</h2>
      <div class="muted">Recent products saved by your workspace.</div>
      <table><thead><tr><th>Product</th><th>Price</th><th>Created</th></tr></thead><tbody>{}</tbody></table>
    </section>
    """.format(total_products, request.current_user["role"].capitalize(), csrf_token(), rows)
    return page("Overview", "dashboard", content)


@app.post("/products")
@login_required
def create_product():
    name = request.form.get("name", "").strip()
    try:
        price = float(request.form.get("price", ""))
    except (TypeError, ValueError):
        flash("Please enter a valid price.")
        return redirect(url_for("dashboard") + "#products")
    if not name or len(name) > 150 or price < 0:
        flash("Enter a valid product name and non-negative price.")
        return redirect(url_for("dashboard") + "#products")
    execute(
        "INSERT INTO products (name, price, created_by) VALUES (%s, %s, %s)",
        (name, price, request.current_user["id"]),
    )
    flash("Product saved successfully.")
    return redirect(url_for("dashboard") + "#products")


@app.get("/api/products")
@login_required
def api_products():
    rows = query_all(
        "SELECT id, name, price FROM products ORDER BY id DESC LIMIT 500"
    )
    return jsonify([
        {"id": row["id"], "name": row["name"], "price": float(row["price"])}
        for row in rows
    ])


@app.post("/api/products")
@login_required
def api_create_product():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    try:
        price = float(data.get("price", 0))
    except (TypeError, ValueError):
        return jsonify(error="Invalid price"), 400
    if not name or len(name) > 150 or price < 0:
        return jsonify(error="Enter a valid name and non-negative price"), 400
    product_id = execute(
        "INSERT INTO products (name, price, created_by) VALUES (%s, %s, %s)",
        (name, price, request.current_user["id"]),
    )
    return jsonify(id=product_id, name=name, price=price), 201


@app.get("/admin/users")
@admin_required
def users_page():
    users = query_all(
        "SELECT id, username, display_name, role, is_active, created_at "
        "FROM app_users ORDER BY created_at DESC"
    )
    rows = []
    for u in users:
        state = '<span class="badge">Active</span>' if u["is_active"] else '<span class="badge danger">Inactive</span>'
        action = ""
        if u["id"] != request.current_user["id"]:
            action = """
            <form class="inline" method="post" action="/admin/users/{}/toggle">
              <input type="hidden" name="_csrf_token" value="{}">
              <button type="submit" style="background:#26334c">{}</button>
            </form>
            """.format(u["id"], csrf_token(), "Deactivate" if u["is_active"] else "Activate")
        rows.append("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            u["username"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
            u["display_name"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
            u["role"].capitalize(), state, action
        ))
    content = """
    <section class="card panel"><h2 style="margin-top:0">Create a user</h2>
      <p class="muted">Only administrators can provision accounts. There is no public sign-up page.</p>
      <form method="post" action="/admin/users">
        <input type="hidden" name="_csrf_token" value="{}">
        <div class="row">
          <div><label>Username</label><input name="username" required minlength="3" maxlength="80" pattern="[A-Za-z0-9_.@-]+" autocomplete="off"></div>
          <div><label>Display name</label><input name="display_name" required maxlength="120"></div>
        </div>
        <div class="row"><div><label>Temporary password (12+ characters)</label><input name="password" type="password" required minlength="12" autocomplete="new-password"></div>
        <div><label>Role</label><select name="role"><option value="user">User</option><option value="admin">Admin</option></select></div></div>
        <button type="submit" style="margin-top:18px">Create account +</button>
      </form>
    </section>
    <section class="card panel"><h2 style="margin-top:0">Workspace access</h2>
      <table><thead><tr><th>Username</th><th>Display name</th><th>Role</th><th>Status</th><th>Action</th></tr></thead>
      <tbody>{}</tbody></table>
    </section>
    """.format(csrf_token(), "".join(rows))
    return page("User access", "users", content)


@app.post("/admin/users")
@admin_required
def create_user():
    username = request.form.get("username", "").strip()
    display_name = request.form.get("display_name", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "user")
    if not re.fullmatch(r"[A-Za-z0-9_.@-]{3,80}", username):
        flash("Username must be 3-80 characters and use letters, numbers, dot, underscore, @, or hyphen.")
        return redirect(url_for("users_page"))
    if not display_name or len(display_name) > 120 or len(password) < 12:
        flash("Provide a display name and a password with at least 12 characters.")
        return redirect(url_for("users_page"))
    if role not in {"user", "admin"}:
        abort(400)
    try:
        execute(
            """INSERT INTO app_users
               (username, display_name, password_hash, role, is_active)
               VALUES (%s, %s, %s, %s, TRUE)""",
            (username, display_name, generate_password_hash(password), role),
        )
    except IntegrityError:
        flash("That username already exists.")
        return redirect(url_for("users_page"))
    flash("Account created. Share credentials with the user securely.")
    return redirect(url_for("users_page"))


@app.post("/admin/users/<int:user_id>/toggle")
@admin_required
def toggle_user(user_id):
    if user_id == request.current_user["id"]:
        flash("You cannot deactivate your own account.")
        return redirect(url_for("users_page"))
    target = query_one("SELECT id, is_active FROM app_users WHERE id = %s", (user_id,))
    if not target:
        abort(404)
    execute(
        "UPDATE app_users SET is_active = %s WHERE id = %s",
        (not bool(target["is_active"]), user_id),
    )
    flash("User access updated.")
    return redirect(url_for("users_page"))


@app.errorhandler(403)
def forbidden(_error):
    return (
        "<h1>403 — Access denied</h1><p>Your account does not have permission "
        "to access this page.</p><p><a href='/dashboard'>Return to workspace</a></p>",
        403,
    )


@app.errorhandler(400)
def bad_request(error):
    message = getattr(error, "description", "Bad request")
    return f"<h1>400 — Request rejected</h1><p>{message}</p>", 400


# Initialize tables and optional bootstrap admin for both direct execution and Gunicorn.
# Configure DB_* environment variables before starting this module.
init_db()

if __name__ == "__main__":
    # For production, use Gunicorn behind the ALB instead of Flask's development server.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), debug=False)
