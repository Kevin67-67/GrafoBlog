import os
import secrets
from functools import wraps

import click
from flask import (
    Flask, abort, flash, g, redirect, render_template, request, session, url_for
)
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from werkzeug.security import check_password_hash, generate_password_hash

from .repository import BlogRepository


def create_app(repository=None, config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config:
        app.config.update(config)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("Configura FLASK_SECRET_KEY antes de iniciar la aplicación")

    repo = repository or BlogRepository(
        os.environ.get("NEO4J_URI", "neo4j://localhost:7687"),
        os.environ.get("NEO4J_USER", "neo4j"),
        os.environ.get("NEO4J_PASSWORD", ""),
        os.environ.get("NEO4J_DATABASE", "neo4j"),
    )
    app.extensions["blog_repo"] = repo

    @app.before_request
    def load_user():
        user_id = session.get("user_id")
        row = repo.user_by_id(user_id) if user_id else None
        g.user = row["usuario"] if row else None
        if user_id and not row:
            session.clear()
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        if request.method == "POST":
            supplied = request.form.get("csrf_token", "")
            if not secrets.compare_digest(supplied, session["csrf_token"]):
                abort(400, "Formulario inválido. Recarga la página e inténtalo de nuevo.")

    @app.context_processor
    def shared():
        return {"csrf_token": session.get("csrf_token", "")}

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not g.user:
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped

    def admin_required(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user["rol"] != "ADMIN":
                abort(403)
            return view(*args, **kwargs)
        return wrapped

    def clean(field, maximum):
        value = request.form.get(field, "").strip()
        if not value or len(value) > maximum:
            abort(400, f"{field}: debe contener entre 1 y {maximum} caracteres.")
        return value

    def selected_tags():
        allowed = {row["etiqueta"]["id"] for row in repo.tags()}
        ids = list(dict.fromkeys(request.form.getlist("tags")))
        if not set(ids).issubset(allowed):
            abort(400, "Etiqueta no válida")
        return ids

    def article_or_404(article_id):
        article = repo.article(article_id)
        if not article:
            abort(404)
        return article

    def can_edit(owner):
        return g.user and (g.user["rol"] == "ADMIN" or
                           (owner and owner["id"] == g.user["id"]))

    @app.get("/")
    def index():
        return render_template("index.html", articles=repo.articles())

    @app.route("/registro", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = clean("nombre", 80)
            email = clean("email", 254).lower()
            password = clean("password", 128)
            if len(password) < 8:
                abort(400, "La contraseña debe tener al menos 8 caracteres")
            if repo.user_by_email(email):
                flash("El correo ya está registrado.", "error")
            else:
                try:
                    repo.create_user(name, email, generate_password_hash(password))
                except Neo4jError:
                    flash("No se pudo registrar el correo. Comprueba si ya existe.", "error")
                else:
                    flash("Cuenta creada. Ya puedes iniciar sesión.", "ok")
                    return redirect(url_for("login"))
        return render_template("auth.html", heading="Crear cuenta", register=True)

    @app.route("/ingresar", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = clean("email", 254).lower()
            password = clean("password", 128)
            row = repo.user_by_email(email)
            user = row["usuario"] if row else None
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["csrf_token"] = secrets.token_urlsafe(32)
                return redirect(url_for("index"))
            flash("Correo o contraseña incorrectos.", "error")
        return render_template("auth.html", heading="Ingresar", register=False)

    @app.post("/salir")
    @login_required
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.get("/articulos/<article_id>")
    def article_detail(article_id):
        article = article_or_404(article_id)
        return render_template("article.html", item=article, comments=repo.comments(article_id))

    @app.route("/articulos/nuevo", methods=["GET", "POST"])
    @login_required
    def article_new():
        if request.method == "POST":
            article_id = repo.create_article(
                g.user["id"], clean("titulo", 160), clean("contenido", 20000), selected_tags()
            )
            return redirect(url_for("article_detail", article_id=article_id))
        return render_template("article_form.html", item=None, tags=repo.tags())

    @app.route("/articulos/<article_id>/editar", methods=["GET", "POST"])
    @login_required
    def article_edit(article_id):
        item = article_or_404(article_id)
        if not can_edit(item["autor"]):
            abort(403)
        if request.method == "POST":
            repo.update_article(article_id, clean("titulo", 160),
                                clean("contenido", 20000), selected_tags())
            return redirect(url_for("article_detail", article_id=article_id))
        return render_template("article_form.html", item=item, tags=repo.tags())

    @app.post("/articulos/<article_id>/eliminar")
    @login_required
    def article_delete(article_id):
        item = article_or_404(article_id)
        if not can_edit(item["autor"]):
            abort(403)
        repo.delete_article(article_id)
        flash("Artículo y sus comentarios eliminados.", "ok")
        return redirect(url_for("index"))

    @app.post("/articulos/<article_id>/comentarios")
    @login_required
    def comment_new(article_id):
        article_or_404(article_id)
        repo.create_comment(g.user["id"], article_id, clean("texto", 2000))
        return redirect(url_for("article_detail", article_id=article_id))

    @app.route("/comentarios/<comment_id>/editar", methods=["GET", "POST"])
    @login_required
    def comment_edit(comment_id):
        item = repo.comment(comment_id)
        if not item:
            abort(404)
        if not can_edit(item["autor"]):
            abort(403)
        if request.method == "POST":
            repo.update_comment(comment_id, clean("texto", 2000))
            return redirect(url_for("article_detail", article_id=item["articulo_id"]))
        return render_template("comment_form.html", item=item)

    @app.post("/comentarios/<comment_id>/eliminar")
    @login_required
    def comment_delete(comment_id):
        item = repo.comment(comment_id)
        if not item:
            abort(404)
        if not can_edit(item["autor"]):
            abort(403)
        repo.delete_comment(comment_id)
        return redirect(url_for("article_detail", article_id=item["articulo_id"]))

    @app.get("/admin")
    @admin_required
    def admin():
        return render_template("admin.html", users=repo.users(), tags=repo.tags())

    @app.post("/admin/etiquetas")
    @admin_required
    def tag_new():
        repo.create_tag(clean("nombre", 50))
        return redirect(url_for("admin"))

    @app.post("/admin/etiquetas/<tag_id>/editar")
    @admin_required
    def tag_edit(tag_id):
        if not any(r["etiqueta"]["id"] == tag_id for r in repo.tags()):
            abort(404)
        repo.rename_tag(tag_id, clean("nombre", 50))
        return redirect(url_for("admin"))

    @app.post("/admin/etiquetas/<tag_id>/eliminar")
    @admin_required
    def tag_delete(tag_id):
        if not any(r["etiqueta"]["id"] == tag_id for r in repo.tags()):
            abort(404)
        repo.delete_tag(tag_id)
        return redirect(url_for("admin"))

    @app.post("/admin/usuarios/<user_id>/rol")
    @admin_required
    def role_edit(user_id):
        role = request.form.get("rol")
        if role not in ("ADMIN", "USUARIO"):
            abort(400)
        if user_id == g.user["id"] and role != "ADMIN":
            abort(400, "No puedes quitarte tu propio rol de administrador")
        if not repo.user_by_id(user_id):
            abort(404)
        repo.set_role(user_id, role)
        return redirect(url_for("admin"))

    @app.post("/admin/usuarios/<user_id>/eliminar")
    @admin_required
    def user_delete(user_id):
        if user_id == g.user["id"]:
            abort(400, "No puedes eliminar tu propia cuenta")
        if not repo.user_by_id(user_id):
            abort(404)
        repo.delete_user(user_id)
        return redirect(url_for("admin"))

    @app.errorhandler(ServiceUnavailable)
    def database_unavailable(error):
        return render_template("error.html", message="No se pudo conectar a Neo4j."), 503

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    def http_error(error):
        return render_template("error.html", message=error.description), error.code

    @app.cli.command("init-db")
    def init_db():
        repo.schema()
        click.echo("Restricciones creadas.")

    @app.cli.command("create-admin")
    @click.option("--name", prompt="Nombre")
    @click.option("--email", prompt="Correo")
    @click.password_option()
    def create_admin(name, email, password):
        email = email.strip().lower()
        if len(password) < 8:
            raise click.ClickException("La contraseña debe tener al menos 8 caracteres")
        if repo.user_by_email(email):
            raise click.ClickException("El correo ya está registrado")
        repo.create_user(name.strip(), email, generate_password_hash(password), "ADMIN")
        click.echo("Administrador creado.")

    return app
