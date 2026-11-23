import os
import re
import json

import secrets
from datetime import datetime, date, timedelta
from markupsafe import escape
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, abort,jsonify
)
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", secrets.token_hex(32))
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///law.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# --- UPDATE THIS IN YOUR CONFIG SECTION ---
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB max upload for multiple attachments

NEWSLETTER_UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads", "newsletters")
os.makedirs(NEWSLETTER_UPLOAD_FOLDER, exist_ok=True)

# Mail (Namecheap Shared Hosting / cPanel Email)
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "your-cpanel-server-hostname")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 465))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "False").lower() in ("true", "1", "yes")
app.config["MAIL_USE_SSL"] = os.getenv("MAIL_USE_SSL", "True").lower() in ("true", "1", "yes")
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "info@thehouseoflaws.org")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv(
    "MAIL_DEFAULT_SENDER",
    ("The House of Laws – General Public Welfare", "info@thehouseoflaws.org"),
)
db = SQLAlchemy(app)
mail = Mail(app)

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads", "admins")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}






# Register the fromjson filter for Jinja templates
app.jinja_env.filters['fromjson'] = json.loads




# ============================================================
# RANDOM HARD-TO-GUESS ROUTES (change these if you want new ones)
# ============================================================
SECRET_SIGNUP_PATH    = "k9m2x7p-q4w8-admin-reg-n3v6"
SECRET_LOGIN_PATH     = "h4j8r1t-z5c2-portal-auth-b7n0"
SECRET_DASHBOARD_PATH = "p3v9m6k-w2x5-secure-panel-f8q1"
SECRET_LOGOUT_PATH    = "t6n0b4j-r8h3-exit-session-y5c7"
SECRET_ACTIVITY_LOGS_PATH = "audit-logs-x9q2-chambers-tracker-77m"


# ---------- MODEL ----------
class AdminLaw(db.Model):
    __tablename__ = "adminlaws"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# --- ACTIVITY LOG MODEL ---
class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_identifier = db.Column(db.String(150), nullable=False)
    ip_address = db.Column(db.String(50), nullable=True)
    method = db.Column(db.String(10), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# --- WIN CASES / TESTIMONIAL MODEL ---
class CaseTestimonial(db.Model):
    __tablename__ = "case_testimonials"

    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(150), nullable=False)
    case_title = db.Column(db.String(255), nullable=False)
    practice_area = db.Column(db.String(100), nullable=False)
    verdict_summary = db.Column(db.Text, nullable=False)
    client_testimonial = db.Column(db.Text, nullable=False)
    lead_counsel = db.Column(db.String(150), nullable=False)
    case_date = db.Column(db.String(50), nullable=False)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "client_name": self.client_name,
            "case_title": self.case_title,
            "practice_area": self.practice_area,
            "verdict_summary": self.verdict_summary,
            "client_testimonial": self.client_testimonial,
            "lead_counsel": self.lead_counsel,
            "case_date": self.case_date,
            "is_published": self.is_published
        }




class Newsletter(db.Model):
    __tablename__ = "newsletter"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)





# --- ADD THIS MODEL RIGHT BELOW YOUR Newsletter MODEL ---
class NewsletterLog(db.Model):
    __tablename__ = "newsletter_logs"

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    attachments = db.Column(db.Text, nullable=True)  # Comma-separated saved filenames
    recipient_count = db.Column(db.Integer, default=0)
    sent_by_name = db.Column(db.String(150), nullable=False)
    sent_by_role = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)




class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    reference_code = db.Column(db.String(20), unique=True, nullable=False)
    office = db.Column(db.String(50), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    preferred_date = db.Column(db.String(20), nullable=False)
    preferred_time = db.Column(db.String(20), nullable=False)
    practice_area = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=True)

    # Status: Pending, Confirmed, Rescheduled, Completed, Declined
    status = db.Column(db.String(30), default="Pending", nullable=False)
    admin_response = db.Column(db.Text, nullable=True)
    handled_by_name = db.Column(db.String(150), nullable=True)
    handled_by_role = db.Column(db.String(80), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    office = db.Column(db.String(50), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="New") # New, Replied
    admin_reply = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)




class JobPosting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    employment_type = db.Column(db.String(50), nullable=False) # Full-time, Intern, etc.
    description = db.Column(db.Text, nullable=False)
    closing_date = db.Column(db.String(50))
    status = db.Column(db.String(20), default="Open") # Open, Closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to dynamic fields & applications
    fields = db.relationship('JobField', backref='job', cascade='all, delete-orphan')
    applications = db.relationship('JobApplication', backref='job', cascade='all, delete-orphan')

class JobField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_posting.id'), nullable=False)
    field_label = db.Column(db.String(150), nullable=False) # e.g. "Years of Experience", "Upload CV"
    field_type = db.Column(db.String(50), nullable=False)   # text, textarea, file, number, select
    is_required = db.Column(db.Boolean, default=True)

class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_posting.id'), nullable=False)
    applicant_name = db.Column(db.String(120), nullable=False)
    applicant_email = db.Column(db.String(120), nullable=False)
    applicant_phone = db.Column(db.String(30), nullable=False)
    answers_json = db.Column(db.Text) # Stores JSON of custom field responses/file paths
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)


class Staff(db.Model):
    __tablename__ = "staff"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    branch = db.Column(db.String(100), nullable=False)
    role_title = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    photo = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- ADD THIS METHOD ---
    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "branch": self.branch,
            "role_title": self.role_title,
            "department": self.department,
            "bio": self.bio or ""
        }


class Publication(db.Model):
    __tablename__ = "publications"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    category = db.Column(db.String(100), nullable=False) # e.g. Case Law Analysis, Corporate Law, Human Rights
    author_name = db.Column(db.String(150), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    cover_image = db.Column(db.String(255), nullable=True)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "category": self.category,
            "author_name": self.author_name,
            "summary": self.summary,
            "content": self.content,
            "cover_image": self.cover_image,
            "is_published": self.is_published
        }



SECRET_APPOINTMENTS_PATH = "appt-k9w2-chambers-77x-schedule-desk-m4v8-29qr"
def generate_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]

app.jinja_env.globals["csrf_token"] = generate_csrf_token


def verify_csrf():
    token = session.get("_csrf_token")
    form_token = request.form.get("csrf_token")
    if not token or not form_token or not secrets.compare_digest(token, form_token):
        abort(403)


# ---------- GLOBAL AUTOMATIC ACTIVITY LOGGER HOOK ----------
@app.after_request
def log_website_activity(response):
    # Ignore static assets and favicon requests to keep activity tables clean
    if request.path.startswith('/static') or request.path == '/favicon.ico':
        return response

    try:
        # Determine whether the user is a logged-in admin or a general visitor
        admin_name = session.get("admin_name")
        admin_role = session.get("admin_role")
        if admin_name:
            user_desc = f"Admin: {admin_name} ({admin_role})"
        else:
            user_desc = "Visitor / Anonymous User"

        ip = request.headers.get("X-Forwarded-For", request.remote_addr)

        log_entry = ActivityLog(
            user_identifier=user_desc,
            ip_address=ip,
            method=request.method,
            path=request.path,
            description=f"{request.method} request to {request.path}"
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Activity logging error: {e}")

    return response


# ---------- HELPERS ----------
def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def send_email(subject, recipients, body):
    """Send email; fails silently in logs if misconfigured."""
    try:
        msg = Message(subject=subject, recipients=recipients, body=body)
        mail.send(msg)
    except Exception as e:
        app.logger.error(f"Email failed: {e}")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


# ---------- ROUTES ----------
# ---------- ROUTES ----------
@app.route("/")
def home():
    return render_template("index.html")

# Alias route to satisfy any templates calling url_for('index')
@app.route("/index")
def index():
    return redirect(url_for("home"))

@app.route('/about')
def about():
    return render_template('about.html')













# ===== OBSCURE SIGNUP =====
@app.route(f"/{SECRET_SIGNUP_PATH}", methods=["GET", "POST"])
def admin_signup():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        username = request.form.get("username", "").strip().lower()
        role = request.form.get("role", "").strip()
        details = request.form.get("details", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        photo = request.files.get("profile_picture")

        errors = []

        if not all([first_name, last_name, email, phone, username, role, details, password]):
            errors.append("All fields are required.")

        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")

        if password != confirm:
            errors.append("Passwords do not match.")

        if AdminLaw.query.filter_by(email=email).first():
            errors.append("Email already registered.")

        if AdminLaw.query.filter_by(username=username).first():
            errors.append("Username already taken.")

        if not photo or photo.filename == "":
            errors.append("Profile picture is required. Use your real photograph.")
        elif not allowed_file(photo.filename):
            errors.append("Only JPG, PNG or WebP images are allowed.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin-signup.html")

        # Save photo
        ext = photo.filename.rsplit(".", 1)[1].lower()
        filename = f"{username}_{secrets.token_hex(8)}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        photo.save(filepath)

        # Create admin
        admin = AdminLaw(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            username=username,
            role=role,
            details=details,
            profile_picture=f"uploads/admins/{filename}",
        )
        admin.set_password(password)

        db.session.add(admin)
        db.session.commit()

        # Email to new admin
        send_email(
            subject="Admin Account Created – The House of Laws",
            recipients=[email],
            body=(
                f"Hello {first_name},\n\n"
                f"Your admin account has been created successfully.\n\n"
                f"Username: {username}\n"
                f"Role: {role}\n\n"
                f"Login URL: /{SECRET_LOGIN_PATH}\n\n"
                f"— The House of Laws"
            ),
        )

        # Notify chambers
        notify = os.getenv("ADMIN_NOTIFY_EMAIL")
        if notify:
            send_email(
                subject="New Admin Signup – The House of Laws",
                recipients=[notify],
                body=(
                    f"New admin registered:\n\n"
                    f"Name: {first_name} {last_name}\n"
                    f"Email: {email}\n"
                    f"Phone: {phone}\n"
                    f"Username: {username}\n"
                    f"Role: {role}\n"
                    f"Details: {details}\n"
                    f"Time: {datetime.utcnow().isoformat()} UTC"
                ),
            )

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("admin_login"))

    return render_template("adminsignup.html")


# ===== OBSCURE LOGIN =====
@app.route(f"/{SECRET_LOGIN_PATH}", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        login_id = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        admin = AdminLaw.query.filter(
            (AdminLaw.email == login_id) | (AdminLaw.username == login_id)
        ).first()

        if not admin or not admin.check_password(password):
            flash("Invalid email/username or password.", "error")
            return render_template("admin-login.html")

        if not admin.is_active:
            flash("This account has been deactivated.", "error")
            return render_template("admin-login.html")

        # Session
        session.clear()
        session["admin_id"] = admin.id
        session["admin_name"] = f"{admin.first_name} {admin.last_name}"
        session["admin_role"] = admin.role
        session["admin_photo"] = admin.profile_picture

        admin.last_login = datetime.utcnow()
        db.session.commit()

        # Login email to admin
        send_email(
            subject="New Login – The House of Laws Admin",
            recipients=[admin.email],
            body=(
                f"Hello {admin.first_name},\n\n"
                f"A successful login to your admin account was recorded.\n\n"
                f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                f"If this was not you, contact the chambers immediately.\n\n"
                f"— The House of Laws"
            ),
        )

        # Notify chambers
        notify = os.getenv("ADMIN_NOTIFY_EMAIL")
        if notify:
            send_email(
                subject="Admin Login Alert – The House of Laws",
                recipients=[notify],
                body=(
                    f"Admin login:\n\n"
                    f"Name: {admin.first_name} {admin.last_name}\n"
                    f"Username: {admin.username}\n"
                    f"Role: {admin.role}\n"
                    f"Time: {datetime.utcnow().isoformat()} UTC"
                ),
            )

        flash(f"Welcome back, {admin.first_name}.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("adminlogin.html")


@app.route(f"/{SECRET_DASHBOARD_PATH}")
@admin_required
def admin_dashboard():
    admin = AdminLaw.query.get(session["admin_id"])
    total_admins = AdminLaw.query.count()
    
    # Real-time appointment statistics & recent list
    pending_appointments_count = Appointment.query.filter_by(status="Pending").count()
    
    today = datetime.utcnow().date()
    start_of_week = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    confirmed_this_week_count = Appointment.query.filter(
        Appointment.status == "Confirmed",
        Appointment.created_at >= start_of_week
    ).count()

    recent_appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(5).all()

    return render_template(
        "admindashboard.html",
        admin=admin,
        admin_name=session.get("admin_name"),
        admin_role=session.get("admin_role"),
        admin_photo=session.get("admin_photo"),
        total_admins=total_admins,
        pending_appointments_count=pending_appointments_count,
        confirmed_this_week_count=confirmed_this_week_count,
        recent_appointments=recent_appointments,
        SECRET_ACTIVITY_LOGS_PATH=SECRET_ACTIVITY_LOGS_PATH
    )

    





# ===== EDIT PROFILE =====
@app.route("/admin/update-profile", methods=["POST"])
@admin_required
def update_profile():
    admin = AdminLaw.query.get(session["admin_id"])
    if not admin:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("admin_login"))

    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    details = request.form.get("details", "").strip()
    photo = request.files.get("profile_picture")

    errors = []

    if not all([first_name, last_name, email, phone]):
        errors.append("Name, email and phone are required.")

    existing = AdminLaw.query.filter(
        AdminLaw.email == email,
        AdminLaw.id != admin.id
    ).first()
    if existing:
        errors.append("That email is already used by another admin.")

    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("admin_dashboard"))

    admin.first_name = first_name
    admin.last_name = last_name
    admin.email = email
    admin.phone = phone
    admin.details = details

    if photo and photo.filename:
        if not allowed_file(photo.filename):
            flash("Only JPG, PNG or WebP images are allowed.", "error")
            return redirect(url_for("admin_dashboard"))
        ext = photo.filename.rsplit(".", 1)[1].lower()
        filename = f"{admin.username}_{secrets.token_hex(8)}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        photo.save(filepath)
        admin.profile_picture = f"uploads/admins/{filename}"

    db.session.commit()

    session["admin_name"] = f"{admin.first_name} {admin.last_name}"
    session["admin_photo"] = admin.profile_picture

    send_email(
        subject="Profile Updated – The House of Laws",
        recipients=[admin.email],
        body=(
            f"Hello {admin.first_name},\n\n"
            f"Your admin profile was updated successfully.\n\n"
            f"Name: {admin.first_name} {admin.last_name}\n"
            f"Email: {admin.email}\n"
            f"Phone: {admin.phone}\n"
            f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
            f"If you did not make this change, contact the chambers immediately.\n\n"
            f"— The House of Laws"
        ),
    )

    notify = os.getenv("ADMIN_NOTIFY_EMAIL")
    if notify:
        send_email(
            subject="Admin Profile Updated – The House of Laws",
            recipients=[notify],
            body=(
                f"Admin profile updated:\n\n"
                f"Name: {admin.first_name} {admin.last_name}\n"
                f"Username: {admin.username}\n"
                f"Email: {admin.email}\n"
                f"Time: {datetime.utcnow().isoformat()} UTC"
            ),
        )

    flash("Profile updated successfully.", "success")
    return redirect(url_for("admin_dashboard"))


# ===== CHANGE PASSWORD =====
@app.route("/admin/change-password", methods=["POST"])
@admin_required
def change_password():
    admin = AdminLaw.query.get(session["admin_id"])
    if not admin:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("admin_login"))

    current = request.form.get("current_password", "")
    new_pass = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    if not admin.check_password(current):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("admin_dashboard"))

    if len(new_pass) < 8:
        flash("New password must be at least 8 characters.", "error")
        return redirect(url_for("admin_dashboard"))

    if new_pass != confirm:
        flash("New passwords do not match.", "error")
        return redirect(url_for("admin_dashboard"))

    admin.set_password(new_pass)
    db.session.commit()

    send_email(
        subject="Password Changed – The House of Laws",
        recipients=[admin.email],
        body=(
            f"Hello {admin.first_name},\n\n"
            f"Your admin password was changed successfully.\n\n"
            f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
            f"If you did not make this change, contact the chambers immediately "
            f"and reset your password.\n\n"
            f"— The House of Laws"
        ),
    )

    notify = os.getenv("ADMIN_NOTIFY_EMAIL")
    if notify:
        send_email(
            subject="Admin Password Changed – The House of Laws",
            recipients=[notify],
            body=(
                f"Password change for admin:\n\n"
                f"Name: {admin.first_name} {admin.last_name}\n"
                f"Username: {admin.username}\n"
                f"Email: {admin.email}\n"
                f"Time: {datetime.utcnow().isoformat()} UTC"
            ),
        )

    flash("Password changed successfully.", "success")
    return redirect(url_for("admin_dashboard"))




EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def send_html_email(subject, recipients, html_body, text_body=None):
    """Send a styled HTML email with plain-text fallback."""
    try:
        msg = Message(
            subject=subject,
            recipients=recipients,
            body=text_body or "Please view this email in an HTML-capable client.",
            html=html_body,
        )
        mail.send(msg)
    except Exception as e:
        app.logger.error(f"Email failed: {e}")


@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email", "").strip().lower()

    # --- Validation ---
    if not email:
        flash("Please enter your email address.", "error")
        return redirect(url_for("home") + "#newsletter")

    if not EMAIL_REGEX.match(email):
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("home") + "#newsletter")

    # Optional: prevent duplicates if using Newsletter model
    try:
        existing = Newsletter.query.filter_by(email=email).first()
        if existing:
            flash("You are already subscribed. Thank you!", "success")
            return redirect(url_for("home") + "#newsletter")

        sub = Newsletter(email=email)
        db.session.add(sub)
        db.session.commit()
    except NameError:
        # Newsletter model not defined — skip DB, still send emails
        pass
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Newsletter save failed: {e}")
        # Still continue to send confirmation email

    # --- Beautiful confirmation to subscriber ---
    subscriber_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="margin:0;padding:0;background:#f7f6f4;font-family:'Segoe UI',Helvetica,Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#f7f6f4;padding:40px 16px;">
        <tr>
          <td align="center">
            <table width="100%" style="max-width:560px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 8px 30px rgba(20,16,12,0.08);">
              <!-- Header -->
              <tr>
                <td style="background:#14100c;padding:36px 32px;text-align:center;">
                  <div style="font-size:28px;color:#ac835d;margin-bottom:8px;">⚖</div>
                  <h1 style="margin:0;font-size:22px;color:#ffffff;font-weight:500;letter-spacing:0.5px;">
                    The House of <span style="color:#ac835d;font-style:italic;">Laws</span>
                  </h1>
                  <p style="margin:8px 0 0;font-size:12px;color:rgba(255,255,255,0.55);letter-spacing:2px;text-transform:uppercase;">
                    Cicero Chambers
                  </p>
                </td>
              </tr>
              <!-- Body -->
              <tr>
                <td style="padding:36px 32px;">
                  <h2 style="margin:0 0 12px;font-size:20px;color:#14100c;font-weight:500;">
                    Welcome to our newsletter
                  </h2>
                  <p style="margin:0 0 16px;font-size:15px;line-height:1.7;color:#817f7c;">
                    Thank you for subscribing. You will now receive carefully curated legal insights,
                    publications and chambers updates from <strong style="color:#14100c;">The House of Laws</strong>.
                  </p>
                  <p style="margin:0 0 24px;font-size:15px;line-height:1.7;color:#817f7c;">
                    We respect your inbox — only meaningful content, never spam.
                  </p>
                  <table cellpadding="0" cellspacing="0" style="margin:0 auto 28px;">
                    <tr>
                      <td style="background:#ac835d;border-radius:50px;padding:14px 28px;">
                        <a href="https://thehouseoflaws.org" style="color:#ffffff;text-decoration:none;font-size:14px;font-weight:500;letter-spacing:0.3px;">
                          Visit Our Website
                        </a>
                      </td>
                    </tr>
                  </table>
                  <p style="margin:0;font-size:13px;color:#999;line-height:1.6;">
                    Subscribed as <strong style="color:#14100c;">{email}</strong>
                  </p>
                </td>
              </tr>
              <!-- Footer -->
              <tr>
                <td style="background:#f7f6f4;padding:24px 32px;text-align:center;border-top:1px solid #eee;">
                  <p style="margin:0 0 6px;font-size:12px;color:#999;">
                    The House of Laws · Ogbuka, Ogbuka &amp; Associates
                  </p>
                  <p style="margin:0;font-size:12px;color:#bbb;">
                    Nsukka · GRA Enugu · Abuja
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    subscriber_text = (
        f"Welcome to The House of Laws newsletter.\n\n"
        f"Thank you for subscribing ({email}). "
        f"You will receive legal insights and chambers updates.\n\n"
        f"— The House of Laws"
    )

    send_html_email(
        subject="Welcome to The House of Laws Newsletter",
        recipients=[email],
        html_body=subscriber_html,
        text_body=subscriber_text,
    )

    # --- Notify chambers ---
    notify = os.getenv("ADMIN_NOTIFY_EMAIL")
    if notify:
        send_html_email(
            subject="New Newsletter Subscriber – The House of Laws",
            recipients=[notify],
            html_body=f"""
            <div style="font-family:sans-serif;padding:24px;color:#333;">
              <h2 style="color:#14100c;">New newsletter subscriber</h2>
              <p><strong>Email:</strong> {email}</p>
              <p><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            </div>
            """,
            text_body=f"New subscriber: {email}\nTime: {datetime.utcnow().isoformat()} UTC",
        )

    flash("Thank you for subscribing! Please check your email.", "success")
    return redirect(url_for("home") + "#newsletter")




# --- ADD THESE ROUTES TO YOUR ADMIN SECTION IN app.py ---
@app.route("/{SECRET_NEWSLETTER_PATH}", methods=["GET", "POST"])
@admin_required
def admin_newsletter():
    admin = AdminLaw.query.get(session["admin_id"])
    subscribers = Newsletter.query.filter_by(is_active=True).order_by(Newsletter.created_at.desc()).all()
    sent_newsletters = NewsletterLog.query.order_by(NewsletterLog.created_at.desc()).all()

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        message_body = request.form.get("message", "").strip()
        uploaded_files = request.files.getlist("attachments")

        if not subject or not message_body:
            flash("Subject and newsletter message are required.", "error")
            return redirect(url_for("admin_newsletter"))

        if not subscribers:
            flash("There are no active subscribers to send this newsletter to.", "error")
            return redirect(url_for("admin_newsletter"))

        # Process optional multiple files
        saved_files_info = []
        saved_filenames = []

        for file in uploaded_files:
            if file and file.filename != "":
                safe_name = secure_filename(file.filename)
                unique_name = f"{secrets.token_hex(6)}_{safe_name}"
                file_path = os.path.join(NEWSLETTER_UPLOAD_FOLDER, unique_name)
                file.save(file_path)

                saved_filenames.append(unique_name)
                saved_files_info.append({
                    "original_name": safe_name,
                    "path": file_path,
                    "content_type": file.content_type or "application/octet-stream"
                })

        # Build styled HTML email
        formatted_message = message_body.replace("\n", "<br>")
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="margin:0;padding:0;background:#f7f6f4;font-family:'Segoe UI',Helvetica,Arial,sans-serif;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#f7f6f4;padding:40px 16px;">
            <tr>
              <td align="center">
                <table width="100%" style="max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 8px 30px rgba(20,16,12,0.08);">
                  <tr>
                    <td style="background:#14100c;padding:32px;text-align:center;">
                      <div style="font-size:26px;color:#ac835d;margin-bottom:6px;">⚖</div>
                      <h1 style="margin:0;font-size:22px;color:#ffffff;font-weight:500;">
                        The House of <span style="color:#ac835d;font-style:italic;">Laws</span>
                      </h1>
                      <p style="margin:6px 0 0;font-size:11px;color:rgba(255,255,255,0.6);letter-spacing:2px;text-transform:uppercase;">
                        Cicero Chambers · Official Dispatch
                      </p>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding:36px 32px;">
                      <h2 style="margin:0 0 18px;font-size:20px;color:#14100c;">{subject}</h2>
                      <div style="font-size:15px;line-height:1.75;color:#4a4845;">
                        {formatted_message}
                      </div>
                      <hr style="border:none;border-top:1px solid #eee;margin:28px 0;">
                      <p style="margin:0;font-size:13px;color:#817f7c;">
                        Issued by <strong>{admin.first_name} {admin.last_name}</strong> ({admin.role})<br>
                        The House of Laws · Ogbuka, Ogbuka &amp; Associates
                      </p>
                    </td>
                  </tr>
                  <tr>
                    <td style="background:#f7f6f4;padding:20px 32px;text-align:center;border-top:1px solid #eee;">
                      <p style="margin:0;font-size:12px;color:#999;">
                        Nsukka · GRA Enugu · Abuja | <a href="https://thehouseoflaws.org" style="color:#ac835d;text-decoration:none;">thehouseoflaws.org</a>
                      </p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </body>
        </html>
        """

        recipient_emails = [s.email for s in subscribers]

        try:
            # Send via BCC so subscribers don't see each other's email addresses
            msg = Message(
                subject=subject,
                recipients=[app.config["MAIL_DEFAULT_SENDER"] or admin.email],
                bcc=recipient_emails,
                body=message_body,
                html=html_content
            )

            # Attach all uploaded files
            for f_info in saved_files_info:
                with open(f_info["path"], "rb") as fp:
                    msg.attach(
                        filename=f_info["original_name"],
                        content_type=f_info["content_type"],
                        data=fp.read()
                    )

            mail.send(msg)

            # Save record to database so all admins can see it
            log_entry = NewsletterLog(
                subject=subject,
                message=message_body,
                attachments=",".join(saved_filenames) if saved_filenames else None,
                recipient_count=len(recipient_emails),
                sent_by_name=f"{admin.first_name} {admin.last_name}",
                sent_by_role=admin.role
            )
            db.session.add(log_entry)
            db.session.commit()

            flash(f"Newsletter successfully sent to {len(recipient_emails)} subscribers!", "success")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Bulk newsletter failed: {e}")
            flash(f"Failed to send newsletter: {str(e)}", "error")

        return redirect(url_for("admin_newsletter"))

    return render_template(
        "admin_newsletter.html",
        admin=admin,
        subscribers=subscribers,
        sent_newsletters=sent_newsletters,
        dashboard_url=url_for("admin_dashboard")
    )


@app.route("/admin/newsletter/delete-subscriber/<int:sub_id>", methods=["POST"])
@admin_required
def delete_subscriber(sub_id):
    sub = Newsletter.query.get_or_404(sub_id)
    db.session.delete(sub)
    db.session.commit()
    flash(f"Removed {sub.email} from subscribers.", "success")
    return redirect(url_for("admin_newsletter"))





VALID_OFFICES = {
    "nsukka": "Nsukka Office – No 88 Aku Road, Nsukka, Enugu",
    "gra": "GRA Office – No 30/31 Park Avenue GRA, Enugu",
    "abuja": "Abuja Office – House 49, G Close, Gwarimpa, FCT",
}

VALID_PRACTICE_AREAS = {
    "litigation": "Litigation & Advocacy",
    "human-rights": "Human Rights & Constitutional Law",
    "corporate": "Corporate & Commercial",
    "property": "Property & Real Estate",
    "arbitration": "Arbitration & ADR",
    "research": "Legal Research & Publications",
    "other": "Other / General Enquiry",
}

VALID_TIMES = {
    "09:00": "09:00 AM", "10:00": "10:00 AM", "11:00": "11:00 AM",
    "12:00": "12:00 PM", "13:00": "01:00 PM", "14:00": "02:00 PM",
    "15:00": "03:00 PM", "16:00": "04:00 PM", "17:00": "05:00 PM",
}


@app.route("/appointment", methods=["GET", "POST"])
def appointment():
    if request.method == "POST":
        verify_csrf()

        office_key = request.form.get("office", "").strip().lower()
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip().lower()
        pref_date = request.form.get("date", "").strip()
        pref_time = request.form.get("time", "").strip()
        practice_key = request.form.get("practice", "").strip().lower()
        matter_msg = request.form.get("message", "").strip()

        errors = []

        # 1. Server-side validation
        if office_key not in VALID_OFFICES:
            errors.append("Please select a valid chambers office.")

        if not name or len(name) < 2 or len(name) > 150:
            errors.append("Please enter your full name (2–150 characters).")

        clean_phone = re.sub(r"[\s\-\+\(\)]", "", phone)
        if not clean_phone.isdigit() or len(clean_phone) < 7 or len(clean_phone) > 15:
            errors.append("Please enter a valid phone number.")

        if not EMAIL_REGEX.match(email):
            errors.append("Please enter a valid email address.")

        try:
            parsed_date = datetime.strptime(pref_date, "%Y-%m-%d").date()
            if parsed_date < date.today():
                errors.append("Appointment date cannot be in the past.")
            elif parsed_date.weekday() == 6:  # Sunday
                errors.append("Our offices are closed on Sundays. Please select Monday–Saturday.")
        except ValueError:
            errors.append("Please select a valid appointment date.")

        if pref_time not in VALID_TIMES:
            errors.append("Please select a valid appointment time slot.")

        if practice_key not in VALID_PRACTICE_AREAS:
            errors.append("Please select a valid practice area.")

        if len(matter_msg) > 2000:
            errors.append("Brief description must be under 2,000 characters.")

        if errors:
            for err in errors:
                flash(err, "error")
            return render_template("appointment.html", form_data=request.form)

        # 2. Save to database
        ref_code = f"THL-{secrets.token_hex(3).upper()}"
        office_label = VALID_OFFICES[office_key]
        time_label = VALID_TIMES[pref_time]
        practice_label = VALID_PRACTICE_AREAS[practice_key]

        appt = Appointment(
            reference_code=ref_code,
            office=office_label,
            full_name=name,
            phone=phone,
            email=email,
            preferred_date=pref_date,
            preferred_time=time_label,
            practice_area=practice_label,
            message=matter_msg or None,
            status="Pending",
        )
        db.session.add(appt)
        db.session.commit()

        # 3. Direct confirmation email to Client
        safe_name = escape(name)
        safe_office = escape(office_label)
        safe_practice = escape(practice_label)
        safe_msg = str(escape(matter_msg)).replace("\n", "<br>") if matter_msg else "<em>None provided</em>"

        client_html = f"""
        <div style="font-family:'Segoe UI',Arial,sans-serif;background:#f7f6f4;padding:32px 16px;">
          <div style="max-width:580px;margin:auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 8px 24px rgba(0,0,0,0.08);">
            <div style="background:#14100c;padding:28px;text-align:center;">
              <h2 style="color:#fff;margin:0;">The House of <span style="color:#ac835d;font-style:italic;">Laws</span></h2>
              <p style="color:#d4b48a;font-size:12px;letter-spacing:1.5px;margin:6px 0 0;">APPOINTMENT REQUEST RECEIVED</p>
            </div>
            <div style="padding:32px;color:#333;line-height:1.6;">
              <p>Dear <strong>{safe_name}</strong>,</p>
              <p>We have received your consultation request. Our clerks are reviewing counsel availability and will confirm your slot shortly.</p>
              <div style="background:#f7f6f4;padding:18px;border-radius:8px;margin:20px 0;font-size:14px;">
                <p style="margin:4px 0;"><strong>Reference ID:</strong> {ref_code}</p>
                <p style="margin:4px 0;"><strong>Office:</strong> {safe_office}</p>
                <p style="margin:4px 0;"><strong>Date &amp; Time:</strong> {pref_date} at {time_label}</p>
                <p style="margin:4px 0;"><strong>Practice Area:</strong> {safe_practice}</p>
                <p style="margin:4px 0;"><strong>Status:</strong> Pending Review</p>
              </div>
              <p style="font-size:13px;color:#777;">Please quote <strong>{ref_code}</strong> in any follow-up communication.</p>
            </div>
          </div>
        </div>
        """

        send_html_email(
            subject=f"Appointment Request Received [{ref_code}] – The House of Laws",
            recipients=[email],
            html_body=client_html,
            text_body=(
                f"Dear {name},\n\n"
                f"Your appointment request ({ref_code}) has been received.\n"
                f"Office: {office_label}\nDate: {pref_date} at {time_label}\n"
                f"Practice Area: {practice_label}\nStatus: Pending Review\n\n"
                f"— The House of Laws"
            ),
        )

        # 4. Direct alert email to Chambers Notify Email
        notify = os.getenv("ADMIN_NOTIFY_EMAIL")
        if notify:
            send_html_email(
                subject=f"New Appointment Booking [{ref_code}] – {name}",
                recipients=[notify],
                html_body=f"""
                <div style="font-family:sans-serif;padding:24px;color:#222;">
                  <h2 style="color:#14100c;">New Consultation Request ({ref_code})</h2>
                  <p><strong>Client:</strong> {safe_name} ({escape(email)} | {escape(phone)})</p>
                  <p><strong>Office:</strong> {safe_office}</p>
                  <p><strong>Requested Slot:</strong> {pref_date} at {time_label}</p>
                  <p><strong>Practice Area:</strong> {safe_practice}</p>
                  <p><strong>Brief Description:</strong><br>{safe_msg}</p>
                </div>
                """,
                text_body=f"New Appointment [{ref_code}] from {name} ({email}, {phone}) for {pref_date} at {time_label}.",
            )

        return render_template("appointment.html", submitted_appt=appt)

    return render_template("appointment.html")



ALLOWED_APPT_ACTIONS = {
    "Confirmed": ("Appointment Confirmed", "#1e7e34"),
    "Rescheduled": ("Appointment Rescheduled", "#b7791f"),
    "Completed": ("Consultation Completed", "#2b6cb0"),
    "Declined": ("Appointment Request Update", "#c53030"),
    "Reply": ("Message from Counsel", "#ac835d"),
}


@app.route(f"/{SECRET_APPOINTMENTS_PATH}", methods=["GET", "POST"])
@admin_required
def admin_appointments():
    admin = AdminLaw.query.get(session["admin_id"])
    if not admin or not admin.is_active:
        session.clear()
        flash("Session invalid. Please log in again.", "error")
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        verify_csrf()

        appt_id = request.form.get("appointment_id", type=int)
        action_type = request.form.get("action_type", "").strip()
        response_message = request.form.get("admin_response", "").strip()
        new_date = request.form.get("new_date", "").strip()
        new_time = request.form.get("new_time", "").strip()

        appt = Appointment.query.get_or_404(appt_id)

        if action_type not in ALLOWED_APPT_ACTIONS:
            flash("Invalid action selected.", "error")
            return redirect(url_for("admin_appointments"))

        if not response_message:
            flash("Please enter a direct response message to send to the client.", "error")
            return redirect(url_for("admin_appointments"))

        # Update date/time if admin reschedules
        if action_type == "Rescheduled":
            if new_date:
                appt.preferred_date = new_date
            if new_time in VALID_TIMES:
                appt.preferred_time = VALID_TIMES[new_time]

        # Update status unless it's a pure informational reply
        if action_type != "Reply":
            appt.status = action_type

        appt.admin_response = response_message
        appt.handled_by_name = f"{admin.first_name} {admin.last_name}"
        appt.handled_by_role = admin.role
        db.session.commit()

        # Send direct email to client for EVERY action taken
        email_heading, badge_color = ALLOWED_APPT_ACTIONS[action_type]
        safe_client = escape(appt.full_name)
        safe_reply = str(escape(response_message)).replace("\n", "<br>")
        safe_admin = escape(f"{admin.first_name} {admin.last_name}")
        safe_role = escape(admin.role)

        client_email_html = f"""
        <div style="font-family:'Segoe UI',Arial,sans-serif;background:#f7f6f4;padding:32px 16px;">
          <div style="max-width:600px;margin:auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 8px 24px rgba(0,0,0,0.08);">
            <div style="background:#14100c;padding:28px;text-align:center;">
              <h2 style="color:#fff;margin:0;">The House of <span style="color:#ac835d;font-style:italic;">Laws</span></h2>
              <p style="color:#d4b48a;font-size:12px;letter-spacing:1.5px;margin:6px 0 0;">{email_heading.upper()}</p>
            </div>
            <div style="padding:32px;color:#333;line-height:1.65;">
              <p>Dear <strong>{safe_client}</strong>,</p>
              <div style="display:inline-block;background:{badge_color};color:#fff;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600;margin-bottom:16px;">
                Status: {escape(appt.status)} · Ref: {appt.reference_code}
              </div>
              <div style="background:#fdfbf8;border-left:4px solid #ac835d;padding:16px 20px;margin:16px 0;color:#14100c;">
                {safe_reply}
              </div>
              <div style="background:#f7f6f4;padding:16px;border-radius:8px;margin-top:20px;font-size:14px;">
                <p style="margin:4px 0;"><strong>Office:</strong> {escape(appt.office)}</p>
                <p style="margin:4px 0;"><strong>Scheduled Date &amp; Time:</strong> {escape(appt.preferred_date)} at {escape(appt.preferred_time)}</p>
                <p style="margin:4px 0;"><strong>Practice Area:</strong> {escape(appt.practice_area)}</p>
              </div>
              <p style="margin-top:24px;font-size:13px;color:#777;">
                Responded by <strong>{safe_admin}</strong> ({safe_role})<br>
                The House of Laws · Ogbuka, Ogbuka &amp; Associates
              </p>
            </div>
          </div>
        </div>
        """

        send_html_email(
            subject=f"{email_heading} [{appt.reference_code}] – The House of Laws",
            recipients=[appt.email],
            html_body=client_email_html,
            text_body=(
                f"Dear {appt.full_name},\n\n"
                f"Appointment Ref: {appt.reference_code}\n"
                f"Current Status: {appt.status}\n"
                f"Date & Time: {appt.preferred_date} at {appt.preferred_time}\n"
                f"Office: {appt.office}\n\n"
                f"Message from {admin.first_name} {admin.last_name} ({admin.role}):\n"
                f"{response_message}\n\n"
                f"— The House of Laws"
            ),
        )

        # Audit email to ADMIN_NOTIFY_EMAIL for every action taken
        notify = os.getenv("ADMIN_NOTIFY_EMAIL")
        if notify:
            send_email(
                subject=f"Appointment Action ({action_type}) [{appt.reference_code}] – {appt.full_name}",
                recipients=[notify],
                body=(
                    f"Appointment Action Logged:\n\n"
                    f"Reference: {appt.reference_code}\n"
                    f"Client: {appt.full_name} ({appt.email})\n"
                    f"Action Taken: {action_type}\n"
                    f"New Status: {appt.status}\n"
                    f"Date/Time: {appt.preferred_date} at {appt.preferred_time}\n"
                    f"Handled By: {admin.first_name} {admin.last_name} ({admin.role})\n"
                    f"Message Sent:\n{response_message}"
                ),
            )

        flash(f"Action '{action_type}' saved and direct email sent to {appt.email}.", "success")
        return redirect(url_for("admin_appointments"))

    status_filter = request.args.get("status", "All")
    query = Appointment.query
    if status_filter != "All":
        query = query.filter_by(status=status_filter)

    appointments = query.order_by(Appointment.created_at.desc()).all()
    counts = {
        "All": Appointment.query.count(),
        "Pending": Appointment.query.filter_by(status="Pending").count(),
        "Confirmed": Appointment.query.filter_by(status="Confirmed").count(),
        "Rescheduled": Appointment.query.filter_by(status="Rescheduled").count(),
        "Completed": Appointment.query.filter_by(status="Completed").count(),
        "Declined": Appointment.query.filter_by(status="Declined").count(),
    }

    return render_template(
        "admin_appointments.html",
        admin=admin,
        appointments=appointments,
        counts=counts,
        status_filter=status_filter,
        valid_times=VALID_TIMES,
    )


@app.route(f"/{SECRET_APPOINTMENTS_PATH}/delete/<int:appt_id>", methods=["POST"])
@admin_required
def delete_appointment(appt_id):
    verify_csrf()
    admin = AdminLaw.query.get(session["admin_id"])
    appt = Appointment.query.get_or_404(appt_id)

    client_email = appt.email
    client_name = appt.full_name
    ref_code = appt.reference_code
    reason = request.form.get("delete_reason", "").strip() or (
        "Your appointment request has been cancelled and removed from our active schedule. "
        "Please contact our chambers if you wish to rebook."
    )

    db.session.delete(appt)
    db.session.commit()

    # Send direct cancellation email upon deletion
    send_html_email(
        subject=f"Appointment Cancelled [{ref_code}] – The House of Laws",
        recipients=[client_email],
        html_body=f"""
        <div style="font-family:'Segoe UI',Arial,sans-serif;padding:24px;background:#f7f6f4;">
          <div style="max-width:560px;margin:auto;background:#fff;padding:28px;border-radius:10px;">
            <h3 style="color:#14100c;margin-top:0;">Appointment Cancelled ({ref_code})</h3>
            <p>Dear <strong>{escape(client_name)}</strong>,</p>
            <p>{str(escape(reason)).replace(chr(10), '<br>')}</p>
            <p style="font-size:13px;color:#777;margin-top:20px;">
              Processed by {escape(admin.first_name)} {escape(admin.last_name)} · The House of Laws
            </p>
          </div>
        </div>
        """,
        text_body=f"Dear {client_name},\n\nAppointment {ref_code} has been cancelled.\n\n{reason}\n\n— The House of Laws",
    )

    flash(f"Appointment {ref_code} deleted and cancellation email sent to {client_email}.", "success")
    return redirect(url_for("admin_appointments"))


@app.route("/admin/directory")
@admin_required
def admin_list():
    admin = AdminLaw.query.get(session["admin_id"])
    admins = AdminLaw.query.order_by(AdminLaw.created_at.desc()).all()
    total_admins = AdminLaw.query.count()

    return render_template(
        "admin_directory.html",
        admin=admin,
        admins=admins,
        total_admins=total_admins,
        admin_name=session.get("admin_name"),
        admin_role=session.get("admin_role"),
        admin_photo=session.get("admin_photo"),
    )




@app.route('/contact')
def contact():
    return render_template('contact.html')


# Route for public contact form submission
@app.route("/api/contact", methods=["GET", "POST"])
def submit_contact():
    if request.method == "GET":
        # Redirect direct GET visits to the Contact page
        return redirect(url_for("contact"))

    try:
        office = request.form.get("office") or request.form.get("office_location")
        name = request.form.get("name") or request.form.get("full_name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        subject = request.form.get("subject") or "General Enquiry"
        message_body = request.form.get("message") or request.form.get("message_body")

        if not all([office, name, phone, email, message_body]):
            return jsonify({
                "success": False, 
                "error": "All required contact fields (Office, Name, Phone, Email, Message) must be filled out."
            }), 400

        new_msg = ContactMessage(
            office=office,
            full_name=name,
            phone=phone,
            email=email,
            subject=subject,
            message=message_body
        )
        db.session.add(new_msg)
        db.session.commit()

        return jsonify({"success": True, "message": "Message sent successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500




# Route to view all client contact messages
@app.route(f"/{SECRET_DASHBOARD_PATH}/messages")
@admin_required
def admin_messages():
    admin = AdminLaw.query.get(session["admin_id"])
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template(
        "admin_messages.html",
        admin=admin,
        messages=messages,
        admin_name=session.get("admin_name"),
        admin_role=session.get("admin_role"),
        admin_photo=session.get("admin_photo"),
    )

# Route to reply to a contact message and email the sender
@app.route(f"/{SECRET_DASHBOARD_PATH}/messages/reply/<int:msg_id>", methods=["POST"])
@admin_required
def reply_contact_message(msg_id):
    contact_msg = ContactMessage.query.get_or_404(msg_id)
    reply_text = request.form.get("reply_message")

    if not reply_text:
        flash("Reply message cannot be empty.", "error")
        return redirect(url_for("admin_messages"))

    try:
        msg = Message(
            subject=f"Re: {contact_msg.subject or 'Enquiry'} – The House of Laws",
            recipients=[contact_msg.email]
        )
        msg.body = f"Dear {contact_msg.full_name},\n\nThank you for reaching out to The House of Laws.\n\nHere is our response to your enquiry:\n\n{reply_text}\n\nBest regards,\nThe House of Laws Chambers"
        mail.send(msg)

        contact_msg.status = "Replied"
        contact_msg.admin_reply = reply_text
        db.session.commit()

        flash(f"Reply successfully sent to {contact_msg.email}!", "success")
    except Exception as e:
        flash(f"Failed to send email: {str(e)}", "error")

    return redirect(url_for("admin_messages"))


# Public route to list all open job opportunities
@app.route("/careers")
def careers():
    open_jobs = JobPosting.query.filter_by(status="Open").all()
    return render_template("careers.html", jobs=open_jobs)

# Admin view to manage/create job postings
@app.route(f"/{SECRET_DASHBOARD_PATH}/jobs")
@admin_required
def admin_jobs():
    admin = AdminLaw.query.get(session["admin_id"])
    jobs = JobPosting.query.order_by(JobPosting.created_at.desc()).all()
    return render_template("admin_jobs.html", admin=admin, jobs=jobs)

# Handle creation of new job + custom form fields
@app.route(f"/{SECRET_DASHBOARD_PATH}/jobs/create", methods=["POST"])
@admin_required
def create_job():
    title = request.form.get("title")
    department = request.form.get("department")
    location = request.form.get("location")
    employment_type = request.form.get("employment_type")
    description = request.form.get("description")
    closing_date = request.form.get("closing_date")

    new_job = JobPosting(
        title=title,
        department=department,
        location=location,
        employment_type=employment_type,
        description=description,
        closing_date=closing_date
    )
    db.session.add(new_job)
    db.session.commit()

    # Parse dynamic fields sent from the builder
    field_labels = request.form.getlist("field_labels[]")
    field_types = request.form.getlist("field_types[]")
    
    for label, ftype in zip(field_labels, field_types):
        if label.strip():
            custom_field = JobField(
                job_id=new_job.id,
                field_label=label.strip(),
                field_type=ftype,
                is_required=True
            )
            db.session.add(custom_field)
    
    db.session.commit()
    flash("Job opportunity successfully published with custom form fields!", "success")
    return redirect(url_for("admin_jobs"))

# Public route to view a job and apply
@app.route("/careers/<int:job_id>", methods=["GET", "POST"])
def public_job_apply(job_id):
    job = JobPosting.query.get_or_404(job_id)
    
    if request.method == "POST":
        name = request.form.get("applicant_name")
        email = request.form.get("applicant_email")
        phone = request.form.get("applicant_phone")
        
        # Collect dynamic responses and uploaded files
        responses = {}
        for field in job.fields:
            field_key = f"field_{field.id}"
            if field.field_type == "file":
                file = request.files.get(field_key)
                if file and file.filename:
                    filename = secure_filename(f"{name}_{file.filename}")
                    upload_folder = os.path.join(app.root_path, "static", "uploads", "applicants")
                    os.makedirs(upload_folder, exist_ok=True)
                    file.save(os.path.join(upload_folder, filename))
                    responses[field.field_label] = f"uploads/applicants/{filename}"
            else:
                responses[field.field_label] = request.form.get(field_key, "")

        application = JobApplication(
            job_id=job.id,
            applicant_name=name,
            applicant_email=email,
            applicant_phone=phone,
            answers_json=json.dumps(responses)
        )
        db.session.add(application)
        db.session.commit()
        
        return render_template("public_job_apply.html", job=job, success=True)

    return render_template("public_job_apply.html", job=job, success=False)




# Route to view all job applicants and reply to them
@app.route(f"/{SECRET_DASHBOARD_PATH}/jobs/applicants")
@admin_required
def admin_job_applicants():
    admin = AdminLaw.query.get(session["admin_id"])
    applications = JobApplication.query.order_by(JobApplication.submitted_at.desc()).all()
    jobs = JobPosting.query.all()
    
    return render_template(
        "admin_job_applicants.html",
        admin=admin,
        applications=applications,
        jobs=jobs,
        admin_name=session.get("admin_name"),
        admin_role=session.get("admin_role"),
        admin_photo=session.get("admin_photo"),
    )

# Route to send an email response to an applicant
@app.route(f"/{SECRET_DASHBOARD_PATH}/jobs/applicants/reply/<int:app_id>", methods=["POST"])
@admin_required
def reply_job_applicant(app_id):
    application = JobApplication.query.get_or_404(app_id)
    reply_text = request.form.get("reply_message")

    if not reply_text:
        flash("Reply message cannot be empty.", "error")
        return redirect(url_for("admin_job_applicants"))

    try:
        msg = Message(
            subject=f"Update regarding your application for {application.job.title} – The House of Laws",
            recipients=[application.applicant_email]
        )
        msg.body = f"Dear {application.applicant_name},\n\nThank you for applying for the position of {application.job.title} at The House of Laws.\n\n{reply_text}\n\nBest regards,\nHiring Committee\nThe House of Laws Chambers"
        mail.send(msg)

        flash(f"Response successfully emailed to {application.applicant_email}!", "success")
    except Exception as e:
        flash(f"Failed to send email: {str(e)}", "error")

    return redirect(url_for("admin_job_applicants"))




STAFF_UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads", "staff")
os.makedirs(STAFF_UPLOAD_FOLDER, exist_ok=True)

@app.route(f"/{SECRET_DASHBOARD_PATH}/staff", methods=["GET", "POST"])
@admin_required
def admin_staff():
    admin = AdminLaw.query.get(session["admin_id"])
    
    if request.method == "POST":
        verify_csrf()
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        branch = request.form.get("branch", "").strip()
        role_title = request.form.get("role_title", "").strip()
        department = request.form.get("department", "").strip()
        bio = request.form.get("bio", "").strip()
        photo_file = request.files.get("photo")

        if not all([full_name, email, phone, branch, role_title, department]):
            flash("All required staff fields must be filled out.", "error")
            return redirect(url_for("admin_staff"))

        if Staff.query.filter_by(email=email).first():
            flash("A staff member with this email address already exists.", "error")
            return redirect(url_for("admin_staff"))

        photo_path = None
        if photo_file and photo_file.filename:
            if not allowed_file(photo_file.filename):
                flash("Invalid image format. Allowed: JPG, PNG, WebP.", "error")
                return redirect(url_for("admin_staff"))
            ext = photo_file.filename.rsplit(".", 1)[1].lower()
            filename = f"staff_{secrets.token_hex(6)}.{ext}"
            photo_file.save(os.path.join(STAFF_UPLOAD_FOLDER, filename))
            photo_path = f"uploads/staff/{filename}"

        new_staff = Staff(
            full_name=full_name,
            email=email,
            phone=phone,
            branch=branch,
            role_title=role_title,
            department=department,
            bio=bio,
            photo=photo_path
        )
        db.session.add(new_staff)
        db.session.commit()

        # Send welcome email to staff
        send_html_email(
            subject="Your Staff Profile Has Been Created – The House of Laws",
            recipients=[email],
            html_body=f"""
            <div style="font-family:'Segoe UI',Arial,sans-serif;padding:32px;background:#f7f6f4;">
              <div style="max-width:560px;margin:auto;background:#fff;padding:32px;border-radius:12px;">
                <h2 style="color:#14100c;margin-top:0;">Welcome to the Team, {escape(full_name)}!</h2>
                <p>Your official staff profile for <strong>{escape(branch)} Office</strong> has been set up under the {escape(department)} department as <strong>{escape(role_title)}</strong>.</p>
                <p>You can now receive internal briefs and chambers dispatches directly.</p>
                <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
                <p style="font-size:12px;color:#888;">The House of Laws Chambers · Administration</p>
              </div>
            </div>
            """,
            text_body=f"Welcome {full_name}, your staff profile has been created at The House of Laws ({branch})."
        )

        flash(f"Staff member {full_name} successfully added.", "success")
        return redirect(url_for("admin_staff"))

    staff_members = Staff.query.order_by(Staff.created_at.desc()).all()
    return render_template("admin_staff.html", admin=admin, staff_members=staff_members)


@app.route(f"/{SECRET_DASHBOARD_PATH}/staff/edit/<int:staff_id>", methods=["POST"])
@admin_required
def edit_staff(staff_id):
    verify_csrf()
    staff = Staff.query.get_or_404(staff_id)
    
    staff.full_name = request.form.get("full_name", "").strip()
    new_email = request.form.get("email", "").strip().lower()
    staff.phone = request.form.get("phone", "").strip()
    staff.branch = request.form.get("branch", "").strip()
    staff.role_title = request.form.get("role_title", "").strip()
    staff.department = request.form.get("department", "").strip()
    staff.bio = request.form.get("bio", "").strip()
    
    photo_file = request.files.get("photo")
    if photo_file and photo_file.filename:
        if allowed_file(photo_file.filename):
            ext = photo_file.filename.rsplit(".", 1)[1].lower()
            filename = f"staff_{secrets.token_hex(6)}.{ext}"
            photo_file.save(os.path.join(STAFF_UPLOAD_FOLDER, filename))
            staff.photo = f"uploads/staff/{filename}"

    staff.email = new_email
    db.session.commit()

    # Send direct notification email about profile updates
    send_html_email(
        subject="Your Staff Profile Was Updated – The House of Laws",
        recipients=[new_email],
        html_body=f"""
        <div style="font-family:'Segoe UI',Arial,sans-serif;padding:32px;background:#f7f6f4;">
          <div style="max-width:560px;margin:auto;background:#fff;padding:32px;border-radius:12px;">
            <h2 style="color:#14100c;margin-top:0;">Profile Update Notice</h2>
            <p>Dear <strong>{escape(staff.full_name)}</strong>,</p>
            <p>Your personnel profile at <strong>The House of Laws</strong> has been updated by administration:</p>
            <ul style="color:#444;line-height:1.6;">
              <li><strong>Branch Office:</strong> {escape(staff.branch)}</li>
              <li><strong>Role / Title:</strong> {escape(staff.role_title)}</li>
              <li><strong>Department:</strong> {escape(staff.department)}</li>
              <li><strong>Phone:</strong> {escape(staff.phone)}</li>
            </ul>
            <p>If you have any questions regarding these updates, please reach out to the administrative desk.</p>
            <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
            <p style="font-size:12px;color:#888;">The House of Laws Chambers · Administration</p>
          </div>
        </div>
        """,
        text_body=f"Hello {staff.full_name}, your staff profile details have been updated by administration."
    )

    flash(f"Staff member {staff.full_name} updated successfully. Notification email sent.", "success")
    return redirect(url_for("admin_staff"))


@app.route(f"/{SECRET_DASHBOARD_PATH}/staff/delete/<int:staff_id>", methods=["POST"])
@admin_required
def delete_staff(staff_id):
    verify_csrf()
    staff = Staff.query.get_or_404(staff_id)
    db.session.delete(staff)
    db.session.commit()
    flash("Staff record removed successfully.", "success")
    return redirect(url_for("admin_staff"))



PUB_UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads", "publications")
os.makedirs(PUB_UPLOAD_FOLDER, exist_ok=True)

def generate_slug(title):
    slug = re.sub(r'[^\w\s-]', '', title).strip().lower()
    slug = re.sub(r'[\s_-]+', '-', slug)
    return f"{slug}-{secrets.token_hex(4)}"

# --- Public Routes ---
@app.route("/publications")
def public_publications():
    pubs = Publication.query.filter_by(is_published=True).order_by(Publication.created_at.desc()).all()
    return render_template("publications.html", publications=pubs)

@app.route("/publications/<slug>")
def public_publication_detail(slug):
    pub = Publication.query.filter_by(slug=slug, is_published=True).first_or_404()
    recent_pubs = Publication.query.filter(Publication.id != pub.id, Publication.is_published == True).order_by(Publication.created_at.desc()).limit(3).all()
    return render_template("publication_detail.html", publication=pub, recent_publications=recent_pubs)

# --- Admin Routes ---
@app.route(f"/{SECRET_DASHBOARD_PATH}/publications", methods=["GET", "POST"])
@admin_required
def admin_publications():
    admin = AdminLaw.query.get(session["admin_id"])
    
    if request.method == "POST":
        verify_csrf()
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        author_name = request.form.get("author_name", "").strip()
        summary = request.form.get("summary", "").strip()
        content = request.form.get("content", "").strip()
        is_published = True if request.form.get("is_published") else False
        cover_file = request.files.get("cover_image")

        if not all([title, category, author_name, summary, content]):
            flash("All required publication fields must be completed.", "error")
            return redirect(url_for("admin_publications"))

        cover_path = None
        if cover_file and cover_file.filename:
            if not allowed_file(cover_file.filename):
                flash("Invalid cover image format. Allowed: JPG, PNG, WebP.", "error")
                return redirect(url_for("admin_publications"))
            ext = cover_file.filename.rsplit(".", 1)[1].lower()
            filename = f"pub_{secrets.token_hex(6)}.{ext}"
            cover_file.save(os.path.join(PUB_UPLOAD_FOLDER, filename))
            cover_path = f"uploads/publications/{filename}"

        pub = Publication(
            title=title,
            slug=generate_slug(title),
            category=category,
            author_name=author_name,
            summary=summary,
            content=content,
            cover_image=cover_path,
            is_published=is_published
        )
        db.session.add(pub)
        db.session.commit()

        flash("Article publication successfully published!", "success")
        return redirect(url_for("admin_publications"))

    publications = Publication.query.order_by(Publication.created_at.desc()).all()
    return render_template("admin_publications.html", admin=admin, publications=publications)

@app.route(f"/{SECRET_DASHBOARD_PATH}/publications/edit/<int:pub_id>", methods=["POST"])
@admin_required
def edit_publication(pub_id):
    verify_csrf()
    pub = Publication.query.get_or_404(pub_id)
    
    pub.title = request.form.get("title", "").strip()
    pub.category = request.form.get("category", "").strip()
    pub.author_name = request.form.get("author_name", "").strip()
    pub.summary = request.form.get("summary", "").strip()
    pub.content = request.form.get("content", "").strip()
    pub.is_published = True if request.form.get("is_published") else False

    cover_file = request.files.get("cover_image")
    if cover_file and cover_file.filename:
        if allowed_file(cover_file.filename):
            ext = cover_file.filename.rsplit(".", 1)[1].lower()
            filename = f"pub_{secrets.token_hex(6)}.{ext}"
            cover_file.save(os.path.join(PUB_UPLOAD_FOLDER, filename))
            pub.cover_image = f"uploads/publications/{filename}"

    db.session.commit()
    flash(f"Publication '{pub.title}' updated successfully.", "success")
    return redirect(url_for("admin_publications"))

@app.route(f"/{SECRET_DASHBOARD_PATH}/publications/delete/<int:pub_id>", methods=["POST"])
@admin_required
def delete_publication(pub_id):
    verify_csrf()
    pub = Publication.query.get_or_404(pub_id)
    db.session.delete(pub)
    db.session.commit()
    flash("Publication deleted successfully.", "success")
    return redirect(url_for("admin_publications"))

SECRET_SUPER_ADMIN_PATH = "super-mgmt-x9q2-control-panel-77m"

@app.route(f"/{SECRET_SUPER_ADMIN_PATH}", methods=["GET"])
def super_admin_control_panel():
    admins = AdminLaw.query.order_by(AdminLaw.created_at.desc()).all()
    return render_template(
        "super_admin_panel.html", 
        admins=admins, 
        SECRET_SUPER_ADMIN_PATH=SECRET_SUPER_ADMIN_PATH
    )

@app.route(f"/{SECRET_SUPER_ADMIN_PATH}/edit/<int:admin_id>", methods=["POST"])
def super_admin_edit(admin_id):
    admin = AdminLaw.query.get_or_404(admin_id)
    
    admin.first_name = request.form.get("first_name", "").strip()
    admin.last_name = request.form.get("last_name", "").strip()
    admin.email = request.form.get("email", "").strip().lower()
    admin.phone = request.form.get("phone", "").strip()
    admin.role = request.form.get("role", "").strip()
    admin.details = request.form.get("details", "").strip()
    
    new_password = request.form.get("new_password", "").strip()
    if new_password:
        if len(new_password) < 8:
            flash("New password must be at least 8 characters.", "error")
            return redirect(url_for("super_admin_control_panel"))
        admin.set_password(new_password)

    db.session.commit()
    flash(f"Admin {admin.username} updated successfully.", "success")
    return redirect(url_for("super_admin_control_panel"))

@app.route(f"/{SECRET_SUPER_ADMIN_PATH}/delete/<int:admin_id>", methods=["POST"])
def super_admin_delete(admin_id):
    admin = AdminLaw.query.get_or_404(admin_id)
    db.session.delete(admin)
    db.session.commit()
    flash("Admin account permanently deleted.", "success")
    return redirect(url_for("super_admin_control_panel"))


# --- ACTIVITY LOG AUDIT TRAIL ROUTE ---
@app.route(f"/{SECRET_ACTIVITY_LOGS_PATH}", methods=["GET"])
@admin_required
def view_activity_logs():
    admin = AdminLaw.query.get(session["admin_id"])
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(300).all()
    return render_template("admin_activity_logs.html", admin=admin, logs=logs)


# --- WIN CASES / TESTIMONIALS (ADMIN & PUBLIC ROUTES) ---

@app.route("/testimonials", methods=["GET"])
def public_testimonials():
    testimonials = CaseTestimonial.query.filter_by(is_published=True).order_by(CaseTestimonial.created_at.desc()).all()
    return render_template("testimonials.html", testimonials=testimonials)


@app.route(f"/{SECRET_DASHBOARD_PATH}/testimonials", methods=["GET", "POST"])
@admin_required
def admin_testimonials():
    admin = AdminLaw.query.get(session["admin_id"])

    if request.method == "POST":
        verify_csrf()
        client_name = request.form.get("client_name", "").strip()
        case_title = request.form.get("case_title", "").strip()
        practice_area = request.form.get("practice_area", "").strip()
        verdict_summary = request.form.get("verdict_summary", "").strip()
        client_testimonial = request.form.get("client_testimonial", "").strip()
        lead_counsel = request.form.get("lead_counsel", "").strip()
        case_date = request.form.get("case_date", "").strip()
        is_published = True if request.form.get("is_published") else False

        if not all([client_name, case_title, practice_area, verdict_summary, client_testimonial, lead_counsel, case_date]):
            flash("All fields are required to log a win case testimonial.", "error")
            return redirect(url_for("admin_testimonials"))

        testimonial = CaseTestimonial(
            client_name=client_name,
            case_title=case_title,
            practice_area=practice_area,
            verdict_summary=verdict_summary,
            client_testimonial=client_testimonial,
            lead_counsel=lead_counsel,
            case_date=case_date,
            is_published=is_published
        )
        db.session.add(testimonial)
        db.session.commit()

        flash("Successful case verdict & testimonial published successfully!", "success")
        return redirect(url_for("admin_testimonials"))

    testimonials = CaseTestimonial.query.order_by(CaseTestimonial.created_at.desc()).all()
    return render_template("admin_testimonials.html", admin=admin, testimonials=testimonials)


@app.route(f"/{SECRET_DASHBOARD_PATH}/testimonials/delete/<int:test_id>", methods=["POST"])
@admin_required
def delete_testimonial(test_id):
    verify_csrf()
    testimonial = CaseTestimonial.query.get_or_404(test_id)
    db.session.delete(testimonial)
    db.session.commit()
    flash("Testimonial case record removed successfully.", "success")
    return redirect(url_for("admin_testimonials"))


@app.route(f"/{SECRET_LOGOUT_PATH}")
def admin_logout():
    admin_id = session.get("admin_id")

    if admin_id:
        admin = AdminLaw.query.get(admin_id)
        if admin:
            send_email(
                subject="Admin Logout – The House of Laws",
                recipients=[admin.email],
                body=(
                    f"Hello {admin.first_name},\n\n"
                    f"You have been logged out of the admin portal.\n"
                    f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                    f"— The House of Laws"
                ),
            )

    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("admin_login"))


# ---------- INIT DB ----------
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    # Print secret routes once on startup (remove in production if you want)
    print("\n===== ADMIN SECRET ROUTES =====")
    print(f"Signup:      /{SECRET_SIGNUP_PATH}")
    print(f"Login:       /{SECRET_LOGIN_PATH}")
    print(f"Dashboard:   /{SECRET_DASHBOARD_PATH}")
    print(f"Logout:      /{SECRET_LOGOUT_PATH}")
    print(f"Audit Logs:  /{SECRET_ACTIVITY_LOGS_PATH}")
    print(f"Testimonials:/{SECRET_DASHBOARD_PATH}/testimonials (Admin)")
    print(f"Public Wins: /testimonials (Public)")
    print("================================\n")
    app.run(debug=True)
    
