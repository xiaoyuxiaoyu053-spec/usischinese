import os
import random
import string
from datetime import datetime
from io import BytesIO

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, send_file, flash, abort
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# 基础配置
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "staons.db")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # 4MB 上传上限

db = SQLAlchemy(app)

# 开发者后台密码(按你的要求写死在这里)
DEV_PASSWORD = "starconssifu"

ALLOWED_IMG_EXT = {"png", "jpg", "jpeg", "gif", "webp"}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_banned = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    icon_filename = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMG_EXT


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def login_required(view):
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    wrapped.__name__ = view.__name__
    return wrapped


def dev_required(view):
    def wrapped(*args, **kwargs):
        if not session.get("is_dev"):
            return redirect(url_for("dev_login"))
        return view(*args, **kwargs)
    wrapped.__name__ = view.__name__
    return wrapped


def validate_username(username):
    # 参照 Roblox 的用户名规则:3-20 位,字母数字与下划线,且不能全是下划线
    if not (3 <= len(username) <= 20):
        return "用户名长度需在 3-20 个字符之间"
    if not all(c.isalnum() or c == "_" for c in username):
        return "用户名只能包含字母、数字和下划线"
    if username.startswith("_") or username.endswith("_"):
        return "用户名不能以下划线开头或结尾"
    return None


def validate_password(password):
    # 参照 Roblox 的密码规则:至少 8 位,且不能与用户名相同
    if len(password) < 8:
        return "密码长度至少需要 8 位"
    if len(password) > 50:
        return "密码过长"
    return None


# ---------------------------------------------------------------------------
# 验证码
# ---------------------------------------------------------------------------
def generate_captcha_text(length=5):
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace("0", "").replace("O", "").replace("1", "").replace("I", "")
    return "".join(random.choice(chars) for _ in range(length))


@app.route("/captcha.png")
def captcha_image():
    text = generate_captcha_text()
    session["captcha"] = text

    width, height = 160, 60
    img = Image.new("RGB", (width, height), color=(240, 242, 245))
    draw = ImageDraw.Draw(img)

    # 干扰线
    for _ in range(6):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=(200, 200, 210), width=2)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except Exception:
        font = ImageFont.load_default()

    for i, ch in enumerate(text):
        x = 15 + i * 28 + random.randint(-4, 4)
        y = random.randint(8, 16)
        color = (
            random.randint(30, 90),
            random.randint(30, 90),
            random.randint(30, 90),
        )
        draw.text((x, y), ch, font=font, fill=color)

    # 干扰点
    for _ in range(80):
        x, y = random.randint(0, width - 1), random.randint(0, height - 1)
        draw.point((x, y), fill=(210, 210, 220))

    buf = BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


# ---------------------------------------------------------------------------
# 首页 / 封面
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", user=current_user())


# ---------------------------------------------------------------------------
# 注册
# ---------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        captcha_input = request.form.get("captcha", "").strip().upper()

        error = None
        if captcha_input != session.get("captcha", ""):
            error = "人机验证码不正确"
        elif (err := validate_username(username)):
            error = err
        elif User.query.filter_by(username=username).first():
            error = "该用户名已被注册"
        elif (err := validate_password(password)):
            error = err
        elif password != confirm:
            error = "两次输入的密码不一致"

        # 验证码无论成功与否都用一次即失效
        session.pop("captcha", None)

        if error:
            flash(error, "error")
            return render_template("register.html", username=username)

        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()

        flash("注册成功,请登录你的账户", "success")
        return redirect(url_for("index"))

    return render_template("register.html", username="")


# ---------------------------------------------------------------------------
# 登录
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("用户名或密码错误", "error")
            return render_template("login.html", username=username)

        if user.is_banned:
            flash("该账户已被封禁", "error")
            return render_template("login.html", username=username)

        session["user_id"] = user.id
        return redirect(url_for("games"))

    return render_template("login.html", username="")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# 游戏大厅
# ---------------------------------------------------------------------------
@app.route("/games")
@login_required
def games():
    game_list = Game.query.order_by(Game.created_at.desc()).all()
    return render_template("games.html", user=current_user(), games=game_list)


# ---------------------------------------------------------------------------
# 开发者后台
# ---------------------------------------------------------------------------
@app.route("/dev", methods=["GET", "POST"])
def dev_login():
    if session.get("is_dev"):
        return redirect(url_for("admin"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if password == DEV_PASSWORD:
            session["is_dev"] = True
            return redirect(url_for("admin"))
        flash("开发者密码错误", "error")

    return render_template("dev_login.html")


@app.route("/dev/logout")
def dev_logout():
    session.pop("is_dev", None)
    return redirect(url_for("index"))


@app.route("/admin")
@dev_required
def admin():
    users = User.query.order_by(User.created_at.desc()).all()
    game_list = Game.query.order_by(Game.created_at.desc()).all()
    return render_template("admin.html", users=users, games=game_list)


@app.route("/admin/ban/<int:user_id>", methods=["POST"])
@dev_required
def admin_ban(user_id):
    user = User.query.get_or_404(user_id)
    user.is_banned = not user.is_banned
    db.session.commit()
    flash(f"已{'封禁' if user.is_banned else '解封'}账户 {user.username}", "success")
    return redirect(url_for("admin"))


@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@dev_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f"已删除账户 {user.username}", "success")
    return redirect(url_for("admin"))


@app.route("/admin/add_game", methods=["POST"])
@dev_required
def admin_add_game():
    name = request.form.get("name", "").strip()
    icon = request.files.get("icon")

    if not name:
        flash("请输入游戏名字", "error")
        return redirect(url_for("admin"))

    if not icon or icon.filename == "" or not allowed_file(icon.filename):
        flash("请上传合法的图标文件(png/jpg/jpeg/gif/webp)", "error")
        return redirect(url_for("admin"))

    ext = icon.filename.rsplit(".", 1)[1].lower()
    safe_name = secure_filename(name) or "game"
    filename = f"{safe_name}-{int(datetime.utcnow().timestamp())}.{ext}"
    icon.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    game = Game(name=name, icon_filename=filename)
    db.session.add(game)
    db.session.commit()

    flash(f"已添加游戏《{name}》", "success")
    return redirect(url_for("admin"))


@app.route("/admin/delete_game/<int:game_id>", methods=["POST"])
@dev_required
def admin_delete_game(game_id):
    game = Game.query.get_or_404(game_id)
    icon_path = os.path.join(app.config["UPLOAD_FOLDER"], game.icon_filename)
    if os.path.exists(icon_path):
        os.remove(icon_path)
    db.session.delete(game)
    db.session.commit()
    flash("已删除游戏", "success")
    return redirect(url_for("admin"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
