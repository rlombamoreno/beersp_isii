import os
import webbrowser
import threading
import time
import uuid
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect  # ✅ NUEVO: seguridad CSRF

# ————— CONFIGURACIÓN INICIAL —————
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(basedir, 'instance')
static_fotos_dir = os.path.join(basedir, 'static', 'fotos')

os.makedirs(instance_dir, exist_ok=True)
os.makedirs(static_fotos_dir, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB

# ————— APP FLASK —————
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or 'una_clave_secreta_muy_segura_2025'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_dir, "beersp.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ✅ CSRF: activado por defecto
csrf = CSRFProtect(app)

# Configuración de correo (mantiene tu lógica de Render)
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = ("BeerSp 🍻", os.getenv('MAIL_USERNAME'))

# ✅ Seguridad de sesión: cookies seguras
from flask.sessions import SecureCookieSessionInterface
class CustomSessionInterface(SecureCookieSessionInterface):
    def get_cookie_secure(self, app):
        # Solo secure en producción (Render)
        return os.getenv('RENDER') is not None
    def get_cookie_samesite(self, app):
        return 'Lax'
app.session_interface = CustomSessionInterface()

db = SQLAlchemy(app)
mail = Mail(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])


# ————— MODELOS —————
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(80), unique=True, nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    contraseña_hash = db.Column(db.String(128), nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    fecha_registro = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    verificado = db.Column(db.Boolean, default=False)
    nombre = db.Column(db.String(50))
    apellidos = db.Column(db.String(80))
    ubicacion = db.Column(db.String(100))
    genero = db.Column(db.String(20))
    presentacion = db.Column(db.Text)
    foto = db.Column(db.String(200))

class Amistad(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    amigo_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    estado = db.Column(db.String(20), default='pendiente')
    fecha_solicitud = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint('usuario_id', 'amigo_id', name='_amistad_uc'),)

class Cerveza(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    estilo = db.Column(db.String(50), nullable=False)
    pais_procedencia = db.Column(db.String(50), nullable=False)
    porcentaje_alcohol = db.Column(db.Float, nullable=False)
    ibu = db.Column(db.Integer)  # International Bitterness Units
    color = db.Column(db.String(50))

class Degustacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    cerveza_id = db.Column(db.Integer, db.ForeignKey('cerveza.id'), nullable=False)
    puntuacion = db.Column(db.Float)  # 0–5, puede ser NULL
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    comentario = db.Column(db.Text)

class Galardon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.Text)

class UsuarioGalardon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    galardon_id = db.Column(db.Integer, db.ForeignKey('galardon.id'), nullable=False)
    nivel = db.Column(db.Integer, default=1)
    fecha_obtenido = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint('usuario_id', 'galardon_id', name='_usuario_galardon_uc'),)


# ————— FUNCIONES AUXILIARES —————
def es_mayor_edad(fecha_nac):
    hoy = datetime.now(timezone.utc).date()
    edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
    return edad >= 18

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def enviar_correo_verificacion(correo, nombre_usuario):
    if os.getenv('RENDER'):
        print(f"[RENDER] Simulando verificación para {correo}")
        return True
    try:
        token = serializer.dumps(correo, salt='verificacion-email')
        enlace = url_for('verificar_email', token=token, _external=True)
        from flask_mail import Message
        msg = Message(
            subject="¡Verifica tu cuenta en BeerSp!",
            recipients=[correo],
            body=f"Hola {nombre_usuario},\n\nHaz clic aquí para verificar: {enlace}\n(Válido 1 hora)"
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False

def seed_cervezas():
    """Precarga 12 cervezas españolas reales si la tabla está vacía."""
    if Cerveza.query.count() == 0:
        cervezas_data = [
            # 🇪🇸 Cervezas artesanales y reconocidas de España
            ("Moritz", "Lager", "España", 4.8, 18, "Dorado claro"),
            ("Estrella Galicia", "Lager", "España", 5.5, 20, "Dorado pálido"),
            ("Mahou Cinco Estrellas", "Lager", "España", 5.5, 22, "Dorado ámbar"),
            ("Alhambra Reserva 1925", "Premium Lager", "España", 6.4, 25, "Ámbar dorado"),
            ("La Virgen IPA", "American IPA", "España", 6.5, 65, "Ámbar dorado"),
            ("Moaña Stout", "Oatmeal Stout", "España", 5.8, 35, "Negro con espuma tostada"),
            ("Black Albert", "Belgian Strong Dark Ale", "España", 10.0, 30, "Marrón oscuro"),
            ("Ahó!", "Pale Ale", "España", 5.4, 45, "Ámbar claro"),
            ("Cerveza 1906 Reserva Especial", "Imperial Lager", "España", 7.2, 28, "Ámbar profundo"),
            ("Galeton", "Barleywine", "España", 10.5, 40, "Marrón rojizo"),
            ("Zaragoza IPA", "West Coast IPA", "España", 6.8, 70, "Dorado turbio"),
            ("Lupulus H-75", "Double IPA", "España", 7.5, 85, "Ámbar intenso"),
        ]
        for nombre, estilo, pais, abv, ibu, color in cervezas_data:
            db.session.add(Cerveza(
                nombre=nombre,
                estilo=estilo,
                pais_procedencia=pais,
                porcentaje_alcohol=abv,
                ibu=ibu,
                color=color
            ))
        db.session.commit()
        print("✅ 12 cervezas españolas reales precargadas.")


# ————— RUTAS —————
@app.route('/')
def index():
    return redirect(url_for('registro'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre_usuario = request.form['nombre_usuario'].strip()
        correo = request.form['correo'].strip()
        contraseña = request.form['contraseña']
        contraseña2 = request.form['contraseña2']
        fecha_nac_str = request.form['fecha_nacimiento']

        if contraseña != contraseña2:
            flash("Las contraseñas no coinciden.", "error")
            return render_template('registro.html', RENDER=os.getenv('RENDER') is not None)

        try:
            fecha_nac = datetime.strptime(fecha_nac_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Fecha de nacimiento inválida.", "error")
            return render_template('registro.html', RENDER=os.getenv('RENDER') is not None)

        if not es_mayor_edad(fecha_nac):
            flash("Debes ser mayor de 18 años para registrarte.", "error")
            return render_template('registro.html', RENDER=os.getenv('RENDER') is not None)

        if Usuario.query.filter_by(nombre_usuario=nombre_usuario).first():
            flash("Nombre de usuario ya existe.", "error")
            return render_template('registro.html', RENDER=os.getenv('RENDER') is not None)

        if Usuario.query.filter_by(correo=correo).first():
            flash("Correo ya registrado.", "error")
            return render_template('registro.html', RENDER=os.getenv('RENDER') is not None)

        nuevo_usuario = Usuario(
            nombre_usuario=nombre_usuario,
            correo=correo,
            contraseña_hash=generate_password_hash(contraseña),
            fecha_nacimiento=fecha_nac,
            verificado=False
        )
        db.session.add(nuevo_usuario)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash("Error interno. Intenta de nuevo.", "error")
            return render_template('registro.html', RENDER=os.getenv('RENDER') is not None)

        if os.getenv('RENDER'):
            # ✅ En Render: verificamos automáticamente
            nuevo_usuario.verificado = True
            db.session.commit()
            flash("Registro exitoso. Cuenta verificada automáticamente.", "success")
        else:
            # En local: enviamos correo
            if enviar_correo_verificacion(correo, nombre_usuario):
                flash("¡Registro exitoso! Revisa tu correo para verificar tu cuenta.", "success")
            else:
                flash("Error al enviar el correo de verificación.", "error")
                return render_template('registro.html', RENDER=False)

        return redirect(url_for('login'))

    return render_template('registro.html', RENDER=os.getenv('RENDER') is not None)


@app.route('/verificar/<token>')
def verificar_email(token):
    try:
        correo = serializer.loads(token, salt='verificacion-email', max_age=3600)
    except:
        flash("El enlace de verificación es inválido o ha expirado.", "error")
        return redirect(url_for('registro'))

    usuario = Usuario.query.filter_by(correo=correo).first()
    if usuario:
        usuario.verificado = True
        db.session.commit()
        flash("¡Tu cuenta ha sido verificada! Ahora puedes iniciar sesión.", "success")
    else:
        flash("Usuario no encontrado.", "error")
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombre_usuario = request.form['nombre_usuario']
        contraseña = request.form['contraseña']
        usuario = Usuario.query.filter_by(nombre_usuario=nombre_usuario).first()

        if not usuario:
            flash("Usuario no encontrado.", "error")
        elif not usuario.verificado:
            flash("Por favor, verifica tu cuenta antes de iniciar sesión.", "error")
        elif not check_password_hash(usuario.contraseña_hash, contraseña):
            flash("Contraseña incorrecta.", "error")
        else:
            # ✅ Seguro: no guardamos toda la entidad, solo el ID
            session['user_id'] = usuario.id
            flash(f"¡Bienvenido, {usuario.nombre_usuario}!", "success")
            return redirect(url_for('inicio', id=usuario.id))

    return render_template('login.html')


@app.route('/olvide_contrasena', methods=['GET', 'POST'])
def olvide_contrasena():
    if request.method == 'POST':
        correo = request.form['correo']
        # ✅ Seguridad: nunca revelamos si el correo existe
        flash("Si tu correo está registrado, recibirás un enlace para restablecer tu contraseña.", "success")
        return redirect(url_for('login'))
    return render_template('olvide_contrasena.html')


@app.route('/restablecer/<token>', methods=['GET', 'POST'])
def restablecer_contrasena(token):
    try:
        correo = serializer.loads(token, salt='restablecer-contrasena', max_age=3600)
    except:
        flash("El enlace es inválido o ha expirado.", "error")
        return redirect(url_for('olvide_contrasena'))

    if request.method == 'POST':
        contraseña_nueva = request.form['contraseña_nueva']
        contraseña_confirm = request.form['contraseña_confirm']
        if contraseña_nueva != contraseña_confirm:
            flash("Las contraseñas no coinciden.", "error")
            return render_template('restablecer.html', token=token)
        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario:
            usuario.contraseña_hash = generate_password_hash(contraseña_nueva)
            db.session.commit()
            flash("Tu contraseña ha sido actualizada. Ya puedes iniciar sesión.", "success")
            return redirect(url_for('login'))
    return render_template('restablecer.html', token=token)


@app.route('/buscar_cervezas')
def buscar_cervezas():
    q = request.args.get('q', '').strip()
    if not q:
        # ✅ Al cargar: devolver "recomendadas" → top por ABV o aleatorias
        cervezas = Cerveza.query.order_by(db.func.random()).limit(8).all()
    else:
        cervezas = Cerveza.query.filter(
            (Cerveza.nombre.ilike(f"%{q}%")) |
            (Cerveza.estilo.ilike(f"%{q}%"))
        ).limit(10).all()
    
    return jsonify({
        "cervezas": [
            {
                "id": c.id,
                "nombre": c.nombre,
                "estilo": c.estilo,
                "pais_procedencia": c.pais_procedencia,
                "porcentaje_alcohol": c.porcentaje_alcohol,
                "ibu": c.ibu,
                "color": c.color
            } for c in cervezas
        ]
    })
    
@app.route('/cervezas_por_ids')
def cervezas_por_ids():
    ids_str = request.args.get('ids', '')
    if not ids_str:
        return jsonify({"cervezas": []})
    try:
        ids = [int(x) for x in ids_str.split(',') if x.isdigit()]
        cervezas = Cerveza.query.filter(Cerveza.id.in_(ids)).all()
        return jsonify({
            "cervezas": [
                {
                    "id": c.id,
                    "nombre": c.nombre,
                    "estilo": c.estilo,
                    "pais_procedencia": c.pais_procedencia,
                    "porcentaje_alcohol": c.porcentaje_alcohol,
                    "ibu": c.ibu,
                    "color": c.color
                } for c in cervezas
            ]
        })
    except Exception as e:
        print("Error en /cervezas_por_ids:", e)
        return jsonify({"cervezas": []})

@app.route('/inicio/<int:id>')
def inicio(id):
    usuario = Usuario.query.get_or_404(id)

    # Estadísticas
    degustaciones = Degustacion.query.filter_by(usuario_id=id).count()
    solicitudes_amistad = Amistad.query.filter_by(amigo_id=id, estado='pendiente').count()

    # Amigos activos (últimas degustaciones)
    amigos_ids_1 = db.session.query(Amistad.amigo_id).filter_by(usuario_id=id, estado='aceptado')
    amigos_ids_2 = db.session.query(Amistad.usuario_id).filter_by(amigo_id=id, estado='aceptado')
    amigos_ids = {r[0] for r in amigos_ids_1.union(amigos_ids_2)}

    amigos_activos = []
    for amigo_id in list(amigos_ids)[:5]:
        amigo = Usuario.query.get(amigo_id)
        ultima_deg = Degustacion.query.filter_by(usuario_id=amigo_id).order_by(Degustacion.fecha.desc()).first()
        if ultima_deg and amigo:
            cerveza = Cerveza.query.get(ultima_deg.cerveza_id)
            if cerveza:
                amigos_activos.append({
                    'nombre_usuario': amigo.nombre_usuario,
                    'ultima_cerveza': cerveza.nombre
                })

    # Cervezas favoritas (≥4.0)
    degustaciones_altas = Degustacion.query.filter(
        Degustacion.usuario_id == id,
        Degustacion.puntuacion >= 4.0
    ).order_by(Degustacion.puntuacion.desc()).limit(6).all()  # hasta 6 para "Ver todas"

    cervezas_favoritas = []
    for d in degustaciones_altas:
        c = Cerveza.query.get(d.cerveza_id)
        if c:
            cervezas_favoritas.append({
                'nombre': c.nombre,
                'estilo': c.estilo,
                'puntuacion': d.puntuacion
            })

    # Galardones
    galardones_db = db.session.query(UsuarioGalardon, Galardon)\
        .join(Galardon)\
        .filter(UsuarioGalardon.usuario_id == id)\
        .order_by(UsuarioGalardon.fecha_obtenido.desc())\
        .limit(5).all()
    galardones = [{'nombre': g.Galardon.nombre, 'nivel': g.UsuarioGalardon.nivel} for g in galardones_db]

    return render_template(
        'inicio.html',
        usuario=usuario,
        stats={
            'degustaciones': degustaciones,
            'locales_nuevos': 0,
            'solicitudes_amistad': solicitudes_amistad
        },
        amigos_activos=amigos_activos,
        cervezas_favoritas=cervezas_favoritas,
        galardones=galardones
    )


@app.route('/perfil/<int:id>')
def perfil(id):
    usuario = Usuario.query.get_or_404(id)
    return render_template('perfil.html', usuario=usuario)


@app.route('/perfil/<int:id>/editar', methods=['GET', 'POST'])
def editar_perfil(id):
    usuario = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        # Protección CSRF ya activa globalmente

        nuevo_usuario = request.form['nombre_usuario'].strip()
        if nuevo_usuario != usuario.nombre_usuario:
            if Usuario.query.filter_by(nombre_usuario=nuevo_usuario).first():
                flash("Nombre de usuario ya en uso.", "error")
                return render_template('editar_perfil.html', usuario=usuario)

        usuario.nombre_usuario = nuevo_usuario
        usuario.nombre = request.form.get('nombre') or None
        usuario.apellidos = request.form.get('apellidos') or None
        usuario.ubicacion = request.form.get('ubicacion') or None
        usuario.genero = request.form.get('genero') or None
        usuario.presentacion = request.form.get('presentacion') or None

        # ✅ Subida de foto: sin bug de file.read()
        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename != '':
                if not allowed_file(file.filename):
                    flash("Tipo de archivo no permitido. Usa JPG, PNG o GIF.", "error")
                    return render_template('editar_perfil.html', usuario=usuario)

                # ✅ Medición segura del tamaño
                file.seek(0, os.SEEK_END)
                size = file.tell()
                file.seek(0)
                if size > MAX_FILE_SIZE:
                    flash("La imagen es demasiado grande (máx. 2 MB).", "error")
                    return render_template('editar_perfil.html', usuario=usuario)

                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"user_{usuario.id}_{uuid.uuid4().hex[:8]}.{ext}"
                filepath = os.path.join(static_fotos_dir, filename)
                file.save(filepath)

                # Borrar foto anterior
                if usuario.foto and usuario.foto.startswith('user_'):
                    old_path = os.path.join(static_fotos_dir, usuario.foto)
                    if os.path.exists(old_path):
                        os.remove(old_path)

                usuario.foto = filename

        try:
            db.session.commit()
            flash("Perfil actualizado correctamente.", "success")
            return redirect(url_for('perfil', id=usuario.id))
        except Exception as e:
            db.session.rollback()
            flash("Error al guardar los cambios.", "error")

    return render_template('editar_perfil.html', usuario=usuario)


@app.route('/eliminar_cuenta/<int:id>', methods=['GET', 'POST'])
def eliminar_cuenta(id):
    usuario = Usuario.query.get_or_404(id)
    if request.method == 'POST':
        confirmacion = request.form.get('confirmar')
        if confirmacion == 'si':
            Degustacion.query.filter_by(usuario_id=id).delete()
            Amistad.query.filter((Amistad.usuario_id == id) | (Amistad.amigo_id == id)).delete()
            UsuarioGalardon.query.filter_by(usuario_id=id).delete()
            db.session.delete(usuario)
            db.session.commit()
            session.pop('user_id', None)
            flash("Tu cuenta ha sido eliminada permanentemente.", "success")
            return redirect(url_for('registro'))
        else:
            flash("Debes confirmar la eliminación de tu cuenta.", "error")
    return render_template('eliminar_cuenta.html', usuario=usuario)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for('login'))


# ————— INICIALIZACIÓN —————
with app.app_context():
    db.create_all()
    seed_cervezas()  # ✅ Precarga cervezas


# ————— AUTOABRIR NAVEGADOR (solo en local) —————
def abrir_navegador():
    time.sleep(1.5)
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == '__main__':
    if os.getenv('RENDER') is None:
        threading.Thread(target=abrir_navegador, daemon=True).start()
        app.run(host='127.0.0.1', port=5000, debug=False)
    else:
        port = int(os.environ.get('PORT', 10000))
        app.run(host='0.0.0.0', port=port, debug=False)