from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///westcoastwalls.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Health & diagnostics ---
@app.route("/health")
def health():
    return {"status": "ok"}, 200

@app.route("/dbcheck")
def dbcheck():
    try:
        db.session.execute("SELECT 1")
        return {"database": "connected"}, 200
    except Exception as e:
        return {"database": "error", "detail": str(e)}, 500

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), default='Quoted')
    quote_amount = db.Column(db.Float)
    actual_cost = db.Column(db.Float)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# --- Routes ---
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Accept BOTH form posts and JSON
        data = None
        if request.is_json or "application/json" in request.headers.get("Content-Type", ""):
            data = request.get_json(silent=True) or {}
            username = data.get("username", "").strip()
            password = data.get("password", "")
            wants_json = True
        else:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            wants_json = False

        user = User.query.filter_by(username=username.lower()).first() or \
               User.query.filter_by(username=username).first()

        ok = bool(user and check_password_hash(user.password_hash, password))
        if ok:
            session["user_id"] = user.id
            session["username"] = user.username
            session["is_admin"] = user.is_admin
            if wants_json:
                return jsonify({"success": True})
            return redirect(url_for("index"))
        else:
            if wants_json:
                return jsonify({"success": False, "message": "Invalid credentials"}), 401
            return render_template("login.html", error="Invalid username or password")

    # GET
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/api/projects", methods=["GET", "POST"])
def projects():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "POST":
        data = request.get_json() or {}
        project = Project(
            customer_name=data["customer_name"],
            address=data["address"],
            status=data.get("status", "Quoted"),
            quote_amount=data.get("quote_amount"),
            actual_cost=data.get("actual_cost"),
            notes=data.get("notes"),
            user_id=session["user_id"],
        )
        db.session.add(project)
        db.session.commit()
        return jsonify({"success": True, "id": project.id})

    projects = Project.query.order_by(Project.created_at.desc()).all()
    return jsonify([
        {
            "id": p.id,
            "customer_name": p.customer_name,
            "address": p.address,
            "status": p.status,
            "quote_amount": p.quote_amount,
            "actual_cost": p.actual_cost,
            "notes": p.notes,
            "created_at": p.created_at.isoformat(),
        }
        for p in projects
    ])

@app.route("/api/projects/<int:id>", methods=["PUT", "DELETE"])
def project_detail(id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    project = Project.query.get_or_404(id)

    if request.method == "DELETE":
        db.session.delete(project)
        db.session.commit()
        return jsonify({"success": True})

    # PUT
    data = request.get_json() or {}
    project.customer_name = data.get("customer_name", project.customer_name)
    project.address = data.get("address", project.address)
    project.status = data.get("status", project.status)
    project.quote_amount = data.get("quote_amount", project.quote_amount)
    project.actual_cost = data.get("actual_cost", project.actual_cost)
    project.notes = data.get("notes", project.notes)
    db.session.commit()
    return jsonify({"success": True})

@app.route("/init-db")
def init_db():
    db.create_all()
    # Create default admin user if none exists
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            email="admin@westcoastwalls.com",
            password_hash=generate_password_hash("admin123"),
            is_admin=True,
        )
        db.session.add(admin)
        db.session.commit()
    return "Database initialized!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
