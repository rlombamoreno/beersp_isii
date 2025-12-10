import os
import webbrowser
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
from functools import wraps

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


app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = ("BeerSp 🍻", os.getenv('MAIL_USERNAME'))

from flask.sessions import SecureCookieSessionInterface
class CustomSessionInterface(SecureCookieSessionInterface):
    def get_cookie_secure(self, app):
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

class Favorita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id', ondelete='CASCADE'), nullable=False)
    cerveza_id = db.Column(db.Integer, db.ForeignKey('cerveza.id', ondelete='CASCADE'), nullable=False)
    fecha_agregada = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    usuario = db.relationship('Usuario', backref=db.backref('favoritas', lazy=True, cascade="all, delete-orphan"))
    cerveza = db.relationship('Cerveza', backref='favoritos')

class Cerveza(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    estilo = db.Column(db.String(50), nullable=False)
    pais_procedencia = db.Column(db.String(50), nullable=False)
    porcentaje_alcohol = db.Column(db.Float, nullable=False)
    ibu = db.Column(db.Integer)  # International Bitterness Units
    color = db.Column(db.String(50))

class Local(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200))
    ciudad = db.Column(db.String(50))
    pais = db.Column(db.String(50))
    latitud = db.Column(db.Float)
    longitud = db.Column(db.Float)
    me_gusta_count = db.Column(db.Integer, default=0)
    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Degustacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    cerveza_id = db.Column(db.Integer, db.ForeignKey('cerveza.id'), nullable=False)
    local_id = db.Column(db.Integer, db.ForeignKey('local.id'))
    puntuacion = db.Column(db.Float)
    comentario = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    tamaño = db.Column(db.String(20))
    formato = db.Column(db.String(20))
    pais_consumicion = db.Column(db.String(50))
    
    usuario = db.relationship('Usuario', backref=db.backref('degustaciones', lazy=True))
    cerveza = db.relationship('Cerveza', backref=db.backref('degustaciones', lazy=True))
    local = db.relationship('Local', backref=db.backref('degustaciones', lazy=True))

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

class ComentarioDegustacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    degustacion_id = db.Column(db.Integer, db.ForeignKey('degustacion.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    degustacion = db.relationship('Degustacion', backref=db.backref('comentarios', lazy=True, cascade="all, delete-orphan"))
    usuario = db.relationship('Usuario', backref=db.backref('comentarios_degustaciones', lazy=True))

# ————— DECORADOR PARA SESIÓN —————
def requiere_sesion(f):
    """Decorador para rutas que requieren sesión"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Rutas públicas que no requieren sesión
        rutas_publicas = ['registro', 'login', 'verificar_email', 
                         'olvide_contrasena', 'restablecer_contrasena', 
                         'static', 'index']
        
        if request.endpoint in rutas_publicas:
            return f(*args, **kwargs)
        
        # Verificar si hay sesión en la URL o en la sesión
        user_id_param = request.args.get('user_id')
        
        if user_id_param:
            try:
                # Si hay user_id en la URL, establecer sesión temporal
                session['user_id_temp'] = int(user_id_param)
                print(f"📝 Sesión temporal establecida: {user_id_param}")
            except ValueError:
                pass
        elif 'user_id' in session:
            # Si ya hay sesión, continuar
            print(f"✅ Usando sesión existente: {session['user_id']}")
            pass
        else:
            # No hay sesión
            flash("Debes iniciar sesión.", "error")
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function

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

def enviar_correo_restablecimiento(correo):
    if os.getenv('RENDER'):
        print(f"[RENDER] Simulando envío de restablecimiento para {correo}")
        return True
    
    try:
        token = serializer.dumps(correo, salt='restablecer-contrasena')
        enlace = url_for('restablecer_contrasena', token=token, _external=True)
        
        from flask_mail import Message
        msg = Message(
            subject="Restablece tu contraseña en BeerSp",
            recipients=[correo],
            body=f"""Hola,

Has solicitado restablecer tu contraseña en BeerSp.

Haz clic en el siguiente enlace para crear una nueva contraseña:
{enlace}

Este enlace expirará en 1 hora.

Si no solicitaste este cambio, ignora este mensaje.

¡Saludos!
El equipo BeerSp 🍻
"""
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error al enviar correo de restablecimiento: {e}")
        return False
    
def seed_cervezas():
    if Cerveza.query.count() == 0:
        cervezas_data = [
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

# ————— RUTAS PÚBLICAS (NO USAN DECORADOR) —————

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
            nuevo_usuario.verificado = True
            db.session.commit()
            flash("Registro exitoso. Cuenta verificada automáticamente.", "success")
        else:
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
    session.clear() 
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
            session['user_id'] = usuario.id
            flash(f"¡Bienvenido, {usuario.nombre_usuario}!", "success")
            return redirect(url_for('inicio'))

    return render_template('login.html')

@app.route('/olvide_contrasena', methods=['GET', 'POST'])
def olvide_contrasena():
    if request.method == 'POST':
        correo = request.form['correo'].strip()
        usuario = Usuario.query.filter_by(correo=correo).first()
        
        if usuario:
            if enviar_correo_restablecimiento(correo):
                flash("Se ha enviado un enlace de restablecimiento a tu correo.", "success")
            else:
                flash("Error al enviar el correo. Intenta nuevamente.", "error")
        else:
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

    usuario = Usuario.query.filter_by(correo=correo).first()
    if not usuario:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for('olvide_contrasena'))

    if request.method == 'POST':
        contraseña_nueva = request.form['contraseña_nueva']
        contraseña_confirm = request.form['contraseña_confirm']
        
        if contraseña_nueva != contraseña_confirm:
            flash("Las contraseñas no coinciden.", "error")
            return render_template('restablecer.html', token=token)
        
        if len(contraseña_nueva) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
            return render_template('restablecer.html', token=token)
        
        usuario.contraseña_hash = generate_password_hash(contraseña_nueva)
        db.session.commit()
        
        flash("Tu contraseña ha sido actualizada correctamente. Ya puedes iniciar sesión.", "success")
        return redirect(url_for('login'))
    
    return render_template('restablecer.html', token=token)

# ————— RUTAS PROTEGIDAS (CON DECORADOR) —————

@app.route('/inicio')
@requiere_sesion
def inicio():
    """Página de inicio del usuario logueado"""
    # Determinar qué ID de usuario usar
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        flash("Sesión no válida.", "error")
        return redirect(url_for('login'))
    
    usuario = db.session.get(Usuario, user_id)
    if not usuario:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for('login'))
    
    # Usar el user_id para todas las consultas
    usuario_id = user_id
    
    # Contar degustaciones reales
    degustaciones_count = Degustacion.query.filter_by(usuario_id=usuario_id).count()
    
    
    solicitudes_amistad = Amistad.query.filter_by(amigo_id=usuario_id, estado='pendiente').count()

    amigos_ids_1 = db.session.query(Amistad.amigo_id).filter_by(usuario_id=usuario_id, estado='aceptado')
    amigos_ids_2 = db.session.query(Amistad.usuario_id).filter_by(amigo_id=usuario_id, estado='aceptado')
    amigos_ids = {r[0] for r in amigos_ids_1.union(amigos_ids_2)}

    amigos_activos = []
    for amigo_id in list(amigos_ids)[:5]:
        amigo = db.session.get(Usuario, amigo_id)
        ultima_deg = Degustacion.query.filter_by(usuario_id=amigo_id).order_by(Degustacion.fecha.desc()).first()
        if ultima_deg and amigo:
            cerveza = db.session.get(Cerveza, ultima_deg.cerveza_id)
            if cerveza:
                amigos_activos.append({
                    'id': amigo.id,
                    'nombre_usuario': amigo.nombre_usuario,
                    'foto': amigo.foto,
                    'ultima_cerveza': cerveza.nombre
                })

    degustaciones_altas = Degustacion.query.filter(
        Degustacion.usuario_id == usuario_id,
        Degustacion.puntuacion >= 4.0
    ).order_by(Degustacion.puntuacion.desc()).limit(6).all()

    cervezas_favoritas = []
    for d in degustaciones_altas:
        c = db.session.get(Cerveza, d.cerveza_id)
        if c:
            cervezas_favoritas.append({
                'nombre': c.nombre,
                'estilo': c.estilo,
                'puntuacion': d.puntuacion
            })

    # Galardones
    galardones_db = db.session.query(UsuarioGalardon, Galardon)\
        .join(Galardon)\
        .filter(UsuarioGalardon.usuario_id == usuario_id)\
        .order_by(UsuarioGalardon.fecha_obtenido.desc())\
        .limit(5).all()
    galardones = [{'nombre': g.Galardon.nombre, 'nivel': g.UsuarioGalardon.nivel} for g in galardones_db]

    # Cargar IDs de favoritas
    favoritas_ids = [f.cerveza_id for f in Favorita.query.filter_by(usuario_id=usuario_id).all()]

    return render_template(
        'inicio.html',
        usuario=usuario,
        user_id=user_id,  # Pasar user_id al template
        stats={
            'degustaciones': degustaciones_count,
            'solicitudes_amistad': solicitudes_amistad
        },
        amigos_activos=amigos_activos,
        cervezas_favoritas=cervezas_favoritas,
        galardones=galardones,
        favoritas_ids=favoritas_ids
    )

# --- RUTAS DE BÚSQUEDA Y CERVEZAS ---

@app.route('/buscar_cervezas')
@requiere_sesion
def buscar_cervezas():
    q = request.args.get('q', '').strip()
    if not q:
        cervezas = Cerveza.query.order_by(db.func.random()).limit(8).all()
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
            ],
            "query": ""
        })
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
            ],
            "query": q
        })
    
@app.route('/cervezas_por_ids')
@requiere_sesion
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

@app.route('/toggle_favorita', methods=['POST'])
@requiere_sesion
def toggle_favorita():
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    data = request.form if request.form else request.get_json() or {}
    cerveza_id = data.get('cerveza_id')
    
    if not cerveza_id:
        return jsonify({"success": False, "message": "ID de cerveza no proporcionado"}), 400
    
    try:
        cerveza_id = int(cerveza_id)
    except:
        return jsonify({"success": False, "message": "ID de cerveza inválido"}), 400
    
    favorita = Favorita.query.filter_by(usuario_id=user_id, cerveza_id=cerveza_id).first()

    if favorita:
        db.session.delete(favorita)
        db.session.commit()
        return jsonify({"success": True, "action": "removed"})
    else:
        nueva_favorita = Favorita(usuario_id=user_id, cerveza_id=cerveza_id)
        db.session.add(nueva_favorita)
        db.session.commit()
        return jsonify({"success": True, "action": "added"})
    
@app.route('/mis_favoritas')
@requiere_sesion
def mis_favoritas():
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        return jsonify({"cervezas": []}), 401

    favoritas_ids = [f.cerveza_id for f in Favorita.query.filter_by(usuario_id=user_id).all()]
    if not favoritas_ids:
        return jsonify({"cervezas": []})

    cervezas = Cerveza.query.filter(Cerveza.id.in_(favoritas_ids)).all()
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

# --- RUTAS PARA DEGUSTACIONES Y LOCALES ---

@app.route('/api/locales')
@requiere_sesion
def api_locales():
    locales = Local.query.order_by(Local.nombre).all()
    return jsonify({
        "locales": [
            {
                "id": l.id,
                "nombre": l.nombre,
                "direccion": l.direccion,
                "ciudad": l.ciudad,
                "pais": l.pais
            } for l in locales
        ]
    })

@app.route('/api/local/nuevo', methods=['POST'])
@requiere_sesion
def api_local_nuevo():
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Datos no válidos"}), 400
            
        nombre = data.get('nombre', '').strip()
        direccion = data.get('direccion', '').strip()
        ciudad = data.get('ciudad', '').strip()
        pais = data.get('pais', '').strip()
        
        if not nombre:
            return jsonify({"success": False, "message": "El nombre es obligatorio"}), 400
        
        nuevo_local = Local(
            nombre=nombre,
            direccion=direccion or None,
            ciudad=ciudad or None,
            pais=pais or "España"
        )
        
        db.session.add(nuevo_local)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "local_id": nuevo_local.id,
            "message": "Local creado exitosamente"
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creando local: {e}")
        return jsonify({"success": False, "message": "Error interno del servidor"}), 500
    
@app.route('/api/cerveza/nueva', methods=['POST'])
@requiere_sesion
def api_cerveza_nueva():
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Datos no válidos"}), 400
            
        nombre = data.get('nombre', '').strip()
        estilo = data.get('estilo', '').strip()
        pais_procedencia = data.get('pais_procedencia', '').strip()
        porcentaje_alcohol = data.get('porcentaje_alcohol')
        ibu = data.get('ibu')
        color = data.get('color', '').strip()
        
        if not nombre:
            return jsonify({"success": False, "message": "El nombre es obligatorio"}), 400
        if not estilo:
            return jsonify({"success": False, "message": "El estilo es obligatorio"}), 400
        if not pais_procedencia:
            return jsonify({"success": False, "message": "El país es obligatorio"}), 400
        if not porcentaje_alcohol:
            return jsonify({"success": False, "message": "El porcentaje de alcohol es obligatorio"}), 400
        
        cerveza_existente = Cerveza.query.filter_by(nombre=nombre).first()
        if cerveza_existente:
            return jsonify({"success": False, "message": "Ya existe una cerveza con ese nombre"}), 400
        
        nueva_cerveza = Cerveza(
            nombre=nombre,
            estilo=estilo,
            pais_procedencia=pais_procedencia,
            porcentaje_alcohol=float(porcentaje_alcohol),
            ibu=int(ibu) if ibu and ibu.isdigit() else None,
            color=color or None
        )
        
        db.session.add(nueva_cerveza)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "cerveza_id": nueva_cerveza.id,
            "message": f"¡Cerveza '{nombre}' creada exitosamente!"
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creando cerveza: {e}")
        return jsonify({"success": False, "message": "Error interno del servidor"}), 500
    
@app.route('/api/degustacion/nueva', methods=['POST'])
@requiere_sesion
def api_degustacion_nueva():
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    data = request.get_json()
    cerveza_id = data.get('cerveza_id')
    puntuacion = data.get('puntuacion')
    comentario = data.get('comentario', '').strip()
    tamaño = data.get('tamaño')
    formato = data.get('formato')
    local_id = data.get('local_id')
    pais_consumicion = data.get('pais_consumicion')
    
    if not cerveza_id:
        return jsonify({"success": False, "message": "Cerveza no especificada"}), 400
    
    cerveza = Cerveza.query.get(cerveza_id)
    if not cerveza:
        return jsonify({"success": False, "message": "Cerveza no encontrada"}), 404
    
    # LÓGICA MEJORADA PARA PAÍS DE CONSUMO
    pais_final = None
    
    if local_id:
        local = Local.query.get(local_id)
        if not local:
            return jsonify({"success": False, "message": "Local no encontrado"}), 404
        
        # PRIORIDAD 1: País del local
        if local.pais:
            pais_final = local.pais
        # PRIORIDAD 2: País especificado manualmente
        elif pais_consumicion:
            pais_final = pais_consumicion
    # PRIORIDAD 3: Solo país especificado (sin local)
    elif pais_consumicion:
        pais_final = pais_consumicion
    
    nueva_degustacion = Degustacion(
        usuario_id=user_id,
        cerveza_id=cerveza_id,
        local_id=local_id,
        puntuacion=float(puntuacion) if puntuacion else None,
        comentario=comentario or None,
        tamaño=tamaño or None,
        formato=formato or None,
        pais_consumicion=pais_final  # Puede ser None si no hay info
    )
    
    db.session.add(nueva_degustacion)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "degustacion_id": nueva_degustacion.id,
        "message": "¡Degustación registrada exitosamente!",
        "pais_usado": pais_final or "No especificado"
    })
    
    
@app.route('/api/local/<int:id>/info')
@requiere_sesion
def api_local_info(id):
    """Obtener información de un local específico"""
    local = Local.query.get(id)
    if not local:
        return jsonify({"success": False, "message": "Local no encontrado"}), 404
    
    return jsonify({
        "success": True,
        "local": {
            "id": local.id,
            "nombre": local.nombre,
            "direccion": local.direccion,
            "ciudad": local.ciudad,
            "pais": local.pais
        }
    })

@app.route('/mis_degustaciones')
@requiere_sesion
def mis_degustaciones():
    """Mis degustaciones (del usuario logueado)"""
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        flash("No autorizado.", "error")
        return redirect(url_for('login'))
    
    usuario = db.session.get(Usuario, user_id)
    if not usuario:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for('login'))
    
    # Obtener degustaciones con comentarios y usuarios
    degustaciones = Degustacion.query.filter_by(
        usuario_id=user_id
    ).order_by(Degustacion.fecha.desc()).all()
    
    # Para cada degustación, cargar los comentarios con información del usuario
    degustaciones_con_comentarios = []
    for deg in degustaciones:
        # Obtener comentarios con información del usuario
        comentarios_db = db.session.query(ComentarioDegustacion, Usuario).join(
            Usuario, ComentarioDegustacion.usuario_id == Usuario.id
        ).filter(
            ComentarioDegustacion.degustacion_id == deg.id
        ).order_by(ComentarioDegustacion.fecha.desc()).all()
        
        # Convertir a formato más fácil para el template
        comentarios_formateados = []
        for comentario, usuario_comentario in comentarios_db:
            comentarios_formateados.append({
                'id': comentario.id,
                'texto': comentario.texto,
                'fecha': comentario.fecha,
                'usuario': {
                    'id': usuario_comentario.id,
                    'nombre_usuario': usuario_comentario.nombre_usuario,
                    'foto': usuario_comentario.foto
                }
            })
        
        # Crear una copa de la degustación con los comentarios
        degustacion_dict = {
            'id': deg.id,
            'cerveza': deg.cerveza,
            'puntuacion': deg.puntuacion,
            'comentario': deg.comentario,
            'fecha': deg.fecha,
            'tamaño': deg.tamaño,
            'formato': deg.formato,
            'local': deg.local,
            'pais_consumicion': deg.pais_consumicion,
            'comentarios': comentarios_formateados
        }
        degustaciones_con_comentarios.append(degustacion_dict)
    
    return render_template('mis_degustaciones.html', 
                         usuario=usuario,
                         user_id=user_id,
                         degustaciones=degustaciones_con_comentarios)

# --- RUTAS DE PERFILES ---

@app.route('/perfil')
@requiere_sesion
def mi_perfil():
    """MI perfil (sin parámetro en URL)"""
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        flash("Debes iniciar sesión.", "error")
        return redirect(url_for('login'))
    
    usuario = db.session.get(Usuario, user_id)
    if not usuario:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for('login'))
    
    return render_template('perfil.html', usuario=usuario, user_id=user_id)

@app.route('/perfil/<int:id>/info')
@requiere_sesion
def perfil_usuario_info(id):
    """Obtener información básica del perfil para modales"""
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    usuario = db.session.get(Usuario, id)
    if not usuario:
        return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
    
    return jsonify({
        "success": True,
        "usuario": {
            "id": usuario.id,
            "nombre_usuario": usuario.nombre_usuario,
            "foto": usuario.foto,
            "ubicacion": usuario.ubicacion,
            "presentacion": usuario.presentacion,
            "fecha_registro": usuario.fecha_registro.strftime('%d/%m/%Y') if usuario.fecha_registro else 'N/A'
        }
    })

@app.route('/perfil/editar', methods=['GET', 'POST'])
@requiere_sesion
def editar_perfil():
    """Editar MI perfil"""
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        flash("Debes iniciar sesión.", "error")
        return redirect(url_for('login'))
    
    usuario = db.session.get(Usuario, user_id)
    if not usuario:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        nuevo_usuario = request.form['nombre_usuario'].strip()
        if nuevo_usuario != usuario.nombre_usuario:
            if Usuario.query.filter_by(nombre_usuario=nuevo_usuario).first():
                flash("Nombre de usuario ya en uso.", "error")
                return render_template('editar_perfil.html', usuario=usuario, user_id=user_id)

        usuario.nombre_usuario = nuevo_usuario
        usuario.nombre = request.form.get('nombre') or None
        usuario.apellidos = request.form.get('apellidos') or None
        usuario.ubicacion = request.form.get('ubicacion') or None
        usuario.genero = request.form.get('genero') or None
        usuario.presentacion = request.form.get('presentacion') or None

        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename != '':
                if not allowed_file(file.filename):
                    flash("Tipo de archivo no permitido. Usa JPG, PNG o GIF.", "error")
                    return render_template('editar_perfil.html', usuario=usuario, user_id=user_id)

                file.seek(0, os.SEEK_END)
                size = file.tell()
                file.seek(0)
                if size > MAX_FILE_SIZE:
                    flash("La imagen es demasiado grande (máx. 2 MB).", "error")
                    return render_template('editar_perfil.html', usuario=usuario, user_id=user_id)

                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"user_{usuario.id}_{uuid.uuid4().hex[:8]}.{ext}"
                filepath = os.path.join(static_fotos_dir, filename)
                file.save(filepath)

                if usuario.foto and usuario.foto.startswith('user_'):
                    old_path = os.path.join(static_fotos_dir, usuario.foto)
                    if os.path.exists(old_path):
                        os.remove(old_path)

                usuario.foto = filename

        try:
            db.session.commit()
            flash("Perfil actualizado correctamente.", "success")
            return redirect(url_for('mi_perfil', user_id=user_id))
        except Exception as e:
            db.session.rollback()
            flash("Error al guardar los cambios.", "error")

    return render_template('editar_perfil.html', usuario=usuario, user_id=user_id)

@app.route('/eliminar_cuenta', methods=['GET', 'POST'])
@requiere_sesion
def eliminar_cuenta():
    """Eliminar MI cuenta"""
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        flash("Debes iniciar sesión.", "error")
        return redirect(url_for('login'))
    
    usuario = db.session.get(Usuario, user_id)
    if not usuario:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        confirmacion = request.form.get('confirmar')
        if confirmacion == 'si':
            # Eliminar todas las relaciones
            Favorita.query.filter_by(usuario_id=user_id).delete()
            Degustacion.query.filter_by(usuario_id=user_id).delete()
            Amistad.query.filter((Amistad.usuario_id == user_id) | (Amistad.amigo_id == user_id)).delete()
            UsuarioGalardon.query.filter_by(usuario_id=user_id).delete()
            ComentarioDegustacion.query.filter_by(usuario_id=user_id).delete()
            
            # Eliminar foto si existe
            if usuario.foto and usuario.foto.startswith('user_'):
                old_path = os.path.join(static_fotos_dir, usuario.foto)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            db.session.delete(usuario)
            db.session.commit()
            session.pop('user_id', None)
            session.pop('user_id_temp', None)
            flash("Tu cuenta ha sido eliminada permanentemente.", "success")
            return redirect(url_for('registro'))
        else:
            flash("Debes confirmar la eliminación de tu cuenta.", "error")
    
    return render_template('eliminar_cuenta.html', usuario=usuario, user_id=user_id)

# --- TOP DEGUSTACIONES ---

@app.route('/top_degustaciones')
@requiere_sesion
def top_degustaciones():
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        flash("Debes iniciar sesión para ver esta página.", "error")
        return redirect(url_for('login'))
    
    # Obtener parámetros de filtro
    estilo = request.args.get('estilo', '')
    pais = request.args.get('pais', '')
    
    # Consulta base: cervezas con al menos una degustación puntuada
    query = db.session.query(
        Cerveza,
        db.func.avg(Degustacion.puntuacion).label('puntuacion_promedio'),
        db.func.count(Degustacion.id).label('num_valoraciones'),
        db.func.max(Degustacion.fecha).label('ultima_valoracion')
    ).join(Degustacion, Degustacion.cerveza_id == Cerveza.id)
    
    # Filtrar solo degustaciones con puntuación
    query = query.filter(Degustacion.puntuacion.isnot(None))
    
    # Aplicar filtros
    if estilo:
        query = query.filter(Cerveza.estilo == estilo)
    if pais:
        query = query.filter(Cerveza.pais_procedencia == pais)
    
    # Agrupar por cerveza y ordenar
    query = query.group_by(Cerveza.id)
    query = query.order_by(db.desc('puntuacion_promedio'), db.desc('num_valoraciones'))
    
    # Limitar a top 50
    top_cervezas = query.limit(50).all()
    
    # Obtener lista de estilos únicos para el filtro
    estilos = db.session.query(Cerveza.estilo).distinct().order_by(Cerveza.estilo).all()
    estilos = [e[0] for e in estilos]
    
    # Obtener lista de países únicos para el filtro
    paises = db.session.query(Cerveza.pais_procedencia).distinct().order_by(Cerveza.pais_procedencia).all()
    paises = [p[0] for p in paises]
    
    # Preparar datos para template
    cervezas_data = []
    for cerveza, promedio, num_val, ultima_fecha in top_cervezas:
        fecha_str = ultima_fecha.strftime('%d/%m/%Y') if ultima_fecha else 'N/A'
        
        cervezas_data.append({
            'id': cerveza.id,
            'nombre': cerveza.nombre,
            'estilo': cerveza.estilo,
            'pais': cerveza.pais_procedencia,
            'alcohol': cerveza.porcentaje_alcohol,
            'ibu': cerveza.ibu,
            'color': cerveza.color,
            'puntuacion_promedio': round(promedio, 2) if promedio else 0,
            'num_valoraciones': num_val,
            'ultima_valoracion': fecha_str
        })
    
    return render_template(
        'top_degustaciones.html',
        cervezas=cervezas_data,
        estilos=estilos,
        paises=paises,
        estilo_filtro=estilo,
        pais_filtro=pais,
        usuario_actual_id=user_id,
        user_id=user_id
    )

@app.route('/api/cerveza/<int:id>/detalle')
@requiere_sesion
def cerveza_detalle(id):
    cerveza = Cerveza.query.get(id)
    if not cerveza:
        return jsonify({"success": False, "message": "Cerveza no encontrada"}), 404
    
    stats = db.session.query(
        db.func.avg(Degustacion.puntuacion).label('promedio'),
        db.func.count(Degustacion.id).label('total'),
        db.func.min(Degustacion.fecha).label('primera')
    ).filter(
        Degustacion.cerveza_id == id,
        Degustacion.puntuacion.isnot(None)
    ).first()
    
    ultima_deg = Degustacion.query.filter_by(cerveza_id=id).order_by(Degustacion.fecha.desc()).first()
    
    data = {
        'id': cerveza.id,
        'nombre': cerveza.nombre,
        'estilo': cerveza.estilo,
        'pais': cerveza.pais_procedencia,
        'alcohol': cerveza.porcentaje_alcohol,
        'ibu': cerveza.ibu,
        'color': cerveza.color,
        'puntuacion_promedio': float(stats.promedio) if stats.promedio else None,
        'total_valoraciones': stats.total if stats.total else 0,
        'primera_degustacion': stats.primera.strftime('%d/%m/%Y') if stats.primera else None,
        'comentario_reciente': ultima_deg.comentario if ultima_deg and ultima_deg.comentario else None
    }
    
    return jsonify({"success": True, "cerveza": data})

# --- SISTEMA DE AMISTADES ---

@app.route('/buscar_usuarios')
@requiere_sesion
def buscar_usuarios():
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        return jsonify({"usuarios": []}), 401
    
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify({"usuarios": []})
    
    usuario_actual_id = user_id
    
    usuarios = Usuario.query.filter(
        Usuario.id != usuario_actual_id,
        (Usuario.nombre_usuario.ilike(f"%{q}%")) |
        (Usuario.correo.ilike(f"%{q}%"))
    ).limit(10).all()
    
    usuarios_data = []
    for usuario in usuarios:
        amistad = Amistad.query.filter(
            ((Amistad.usuario_id == usuario_actual_id) & (Amistad.amigo_id == usuario.id)) |
            ((Amistad.usuario_id == usuario.id) & (Amistad.amigo_id == usuario_actual_id))
        ).first()
        
        estado = None
        if amistad:
            if amistad.estado == 'aceptado':
                estado = 'amigos'
            elif amistad.estado == 'pendiente':
                if amistad.usuario_id == usuario_actual_id:
                    estado = 'solicitud_enviada'
                else:
                    estado = 'solicitud_recibida'
            elif amistad.estado == 'rechazado':
                estado = 'rechazado'
        
        usuarios_data.append({
            'id': usuario.id,
            'nombre_usuario': usuario.nombre_usuario,
            'foto': usuario.foto,
            'ubicacion': usuario.ubicacion,
            'estado_amistad': estado
        })
    
    return jsonify({"usuarios": usuarios_data})

@app.route('/enviar_solicitud_amistad', methods=['POST'])
@requiere_sesion
def enviar_solicitud_amistad():
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Datos no válidos"}), 400
    
    amigo_id = data.get('amigo_id')
    
    if not amigo_id:
        return jsonify({"success": False, "message": "ID de amigo no proporcionado"}), 400
    
    usuario_id = user_id
    
    if usuario_id == amigo_id:
        return jsonify({"success": False, "message": "No puedes enviarte solicitud a ti mismo"}), 400
    
    amistad_existente = Amistad.query.filter(
        ((Amistad.usuario_id == usuario_id) & (Amistad.amigo_id == amigo_id)) |
        ((Amistad.usuario_id == amigo_id) & (Amistad.amigo_id == usuario_id))
    ).first()
    
    if amistad_existente:
        if amistad_existente.estado == 'pendiente':
            return jsonify({"success": False, "message": "Ya hay una solicitud pendiente"}), 400
        elif amistad_existente.estado == 'aceptado':
            return jsonify({"success": False, "message": "Ya sois amigos"}), 400
        elif amistad_existente.estado == 'rechazado':
            amistad_existente.estado = 'pendiente'
            amistad_existente.fecha_solicitud = datetime.now(timezone.utc)
            db.session.commit()
            return jsonify({"success": True, "message": "Solicitud enviada"})
    
    nueva_amistad = Amistad(
        usuario_id=usuario_id,
        amigo_id=amigo_id,
        estado='pendiente'
    )
    
    db.session.add(nueva_amistad)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Solicitud enviada"})

@app.route('/solicitudes_amistad')
@requiere_sesion
def solicitudes_amistad():
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        return jsonify({"recibidas": [], "enviadas": []}), 401
    
    print(f"📩 Cargando solicitudes para usuario ID: {user_id}")
    
    try:
        # Solicitudes recibidas (otros te enviaron)
        solicitudes_recibidas = db.session.query(Amistad, Usuario).join(
            Usuario, Amistad.usuario_id == Usuario.id
        ).filter(
            Amistad.amigo_id == user_id,
            Amistad.estado == 'pendiente'
        ).all()
        
        # Solicitudes enviadas (tú enviaste)
        solicitudes_enviadas = db.session.query(Amistad, Usuario).join(
            Usuario, Amistad.amigo_id == Usuario.id
        ).filter(
            Amistad.usuario_id == user_id,
            Amistad.estado == 'pendiente'
        ).all()
        
        recibidas_data = []
        for amistad, usuario in solicitudes_recibidas:
            recibidas_data.append({
                'id': amistad.id,
                'usuario': {
                    'id': usuario.id,
                    'nombre_usuario': usuario.nombre_usuario,
                    'foto': usuario.foto,
                    'ubicacion': usuario.ubicacion
                },
                'fecha_solicitud': amistad.fecha_solicitud.strftime('%d/%m/%Y %H:%M'),
                'tipo': 'recibida'
            })
        
        enviadas_data = []
        for amistad, usuario in solicitudes_enviadas:
            enviadas_data.append({
                'id': amistad.id,
                'usuario': {
                    'id': usuario.id,
                    'nombre_usuario': usuario.nombre_usuario,
                    'foto': usuario.foto,
                    'ubicacion': usuario.ubicacion
                },
                'fecha_solicitud': amistad.fecha_solicitud.strftime('%d/%m/%Y %H:%M'),
                'tipo': 'enviada'
            })
        
        print(f"✅ Solicitudes cargadas - Recibidas: {len(recibidas_data)}, Enviadas: {len(enviadas_data)}")
        
        return jsonify({
            "recibidas": recibidas_data,
            "enviadas": enviadas_data
        })
        
    except Exception as e:
        print(f"❌ Error en solicitudes_amistad: {str(e)}")
        return jsonify({"recibidas": [], "enviadas": []}), 500

@app.route('/gestionar_solicitud', methods=['POST'])
@requiere_sesion
def gestionar_solicitud():
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    data = request.get_json()
    solicitud_id = data.get('solicitud_id')
    accion = data.get('accion')
    
    if not solicitud_id or not accion:
        return jsonify({"success": False, "message": "Datos incompletos"}), 400
    
    amistad = Amistad.query.get(solicitud_id)
    if not amistad:
        return jsonify({"success": False, "message": "Solicitud no encontrada"}), 404
    
    if accion == 'aceptar' or accion == 'rechazar':
        if amistad.amigo_id != user_id:
            return jsonify({"success": False, "message": "No autorizado"}), 403
    elif accion == 'cancelar':
        if amistad.usuario_id != user_id:
            return jsonify({"success": False, "message": "No autorizado"}), 403
    
    if accion == 'aceptar':
        amistad.estado = 'aceptado'
        mensaje = "Solicitud aceptada"
    elif accion == 'rechazar':
        db.session.delete(amistad)
        db.session.commit()
        mensaje = "Solicitud rechazada"
    elif accion == 'cancelar':
        db.session.delete(amistad)
        db.session.commit()
        return jsonify({"success": True, "message": "Solicitud cancelada"})
    
    db.session.commit()
    return jsonify({"success": True, "message": mensaje})

@app.route('/mis_amigos')
@requiere_sesion
def mis_amigos():
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        return jsonify({"amigos": []}), 401
    
    print(f"👥 Cargando amigos para usuario ID: {user_id}")
    
    try:
        # Obtener IDs de amigos (aceptados)
        amigos_ids_query = db.session.query(Amistad.amigo_id).filter_by(
            usuario_id=user_id, estado='aceptado'
        ).union(
            db.session.query(Amistad.usuario_id).filter_by(
                amigo_id=user_id, estado='aceptado'
            )
        ).all()
        
        amigos_ids = [r[0] for r in amigos_ids_query]
        
        if not amigos_ids:
            print("ℹ️ No se encontraron amigos")
            return jsonify({"amigos": []})
        
        print(f"📊 IDs de amigos encontrados: {amigos_ids}")
        
        # Obtener información de los amigos
        amigos = Usuario.query.filter(Usuario.id.in_(amigos_ids)).all()
        
        amigos_data = []
        for amigo in amigos:
            # Obtener última degustación
            ultima_deg = Degustacion.query.filter_by(
                usuario_id=amigo.id
            ).order_by(Degustacion.fecha.desc()).first()
            
            actividad = None
            if ultima_deg:
                cerveza = Cerveza.query.get(ultima_deg.cerveza_id)
                if cerveza:
                    actividad = {
                        'cerveza_nombre': cerveza.nombre,
                        'cerveza_estilo': cerveza.estilo,
                        'puntuacion': ultima_deg.puntuacion,
                        'fecha': ultima_deg.fecha.strftime('%d/%m/%Y %H:%M'),
                        'comentario': ultima_deg.comentario
                    }
            
            amigos_data.append({
                'id': amigo.id,
                'nombre_usuario': amigo.nombre_usuario,
                'foto': amigo.foto,
                'ubicacion': amigo.ubicacion,
                'presentacion': amigo.presentacion,
                'actividad_reciente': actividad
            })
        
        print(f"✅ {len(amigos_data)} amigos cargados exitosamente")
        
        return jsonify({"amigos": amigos_data})
        
    except Exception as e:
        print(f"❌ Error en mis_amigos: {str(e)}")
        return jsonify({"amigos": []}), 500

@app.route('/actividades_amigos')
@requiere_sesion
def actividades_amigos():
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        return jsonify({"actividades": []}), 401
    
    print(f"📝 Cargando actividades para usuario ID: {user_id}")
    
    try:
        # Obtener IDs de amigos
        amigos_ids_query = db.session.query(Amistad.amigo_id).filter_by(
            usuario_id=user_id, estado='aceptado'
        ).union(
            db.session.query(Amistad.usuario_id).filter_by(
                amigo_id=user_id, estado='aceptado'
            )
        ).all()
        
        amigos_ids = [r[0] for r in amigos_ids_query]
        
        if not amigos_ids:
            print("ℹ️ No se encontraron amigos para actividades")
            return jsonify({"actividades": [], "total": 0, "mostrando": 0})
        
        print(f"📊 IDs de amigos para actividades: {amigos_ids}")
        
        # Obtener TODAS las actividades de amigos
        actividades = db.session.query(
            Degustacion, Usuario, Cerveza
        ).join(
            Usuario, Degustacion.usuario_id == Usuario.id
        ).join(
            Cerveza, Degustacion.cerveza_id == Cerveza.id
        ).filter(
            Degustacion.usuario_id.in_(amigos_ids)
        ).order_by(
            Degustacion.fecha.desc()
        ).all()
        
        actividades_data = []
        for deg, usuario, cerveza in actividades:
            # Obtener comentarios recientes
            comentarios_db = db.session.query(ComentarioDegustacion, Usuario).join(
                Usuario, ComentarioDegustacion.usuario_id == Usuario.id
            ).filter(
                ComentarioDegustacion.degustacion_id == deg.id
            ).order_by(ComentarioDegustacion.fecha.desc()).limit(3).all()
            
            comentarios = []
            for comentario, usuario_comentario in comentarios_db:
                comentarios.append({
                    'id': comentario.id,
                    'usuario_id': comentario.usuario_id,
                    'usuario_nombre': usuario_comentario.nombre_usuario,
                    'texto': comentario.texto,
                    'fecha': comentario.fecha.strftime('%d/%m/%Y %H:%M')
                })
            
            actividades_data.append({
                'id': deg.id,
                'usuario': {
                    'id': usuario.id,
                    'nombre_usuario': usuario.nombre_usuario,
                    'foto': usuario.foto
                },
                'cerveza': {
                    'id': cerveza.id,
                    'nombre': cerveza.nombre,
                    'estilo': cerveza.estilo,
                    'pais': cerveza.pais_procedencia
                },
                'puntuacion': deg.puntuacion,
                'comentario': deg.comentario,
                'fecha': deg.fecha.strftime('%d/%m/%Y %H:%M'),
                'local': deg.local.nombre if deg.local else None,
                'comentarios': comentarios
            })
        
        print(f"✅ {len(actividades_data)} actividades cargadas exitosamente")
        
        return jsonify({
            "actividades": actividades_data,
            "total": len(actividades_data),
            "mostrando": min(5, len(actividades_data))  # Por defecto mostrar 5
        })
        
    except Exception as e:
        print(f"❌ Error en actividades_amigos: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"actividades": [], "total": 0, "mostrando": 0}), 500


@app.route('/comentar_degustacion', methods=['POST'])
@requiere_sesion
def comentar_degustacion():
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    data = request.get_json()
    degustacion_id = data.get('degustacion_id')
    texto = data.get('texto', '').strip()
    
    if not degustacion_id:
        return jsonify({"success": False, "message": "Degustación no especificada"}), 400
    
    if not texto or len(texto) < 1:
        return jsonify({"success": False, "message": "El comentario no puede estar vacío"}), 400
    
    degustacion = Degustacion.query.get(degustacion_id)
    if not degustacion:
        return jsonify({"success": False, "message": "Degustación no encontrada"}), 404
    
    nuevo_comentario = ComentarioDegustacion(
        degustacion_id=degustacion_id,
        usuario_id=user_id,
        texto=texto
    )
    
    db.session.add(nuevo_comentario)
    db.session.commit()
    
    usuario_comentario = Usuario.query.get(user_id)
    
    return jsonify({
        "success": True,
        "message": "Comentario añadido",
        "comentario": {
            'id': nuevo_comentario.id,
            'usuario_id': nuevo_comentario.usuario_id,
            'usuario_nombre': usuario_comentario.nombre_usuario if usuario_comentario else 'Usuario',
            'texto': nuevo_comentario.texto,
            'fecha': nuevo_comentario.fecha.strftime('%d/%m/%Y %H:%M')
        }
    })

@app.route('/amigos')
@requiere_sesion
def amigos():
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        flash("Debes iniciar sesión para ver esta página.", "error")
        return redirect(url_for('login'))
    
    usuario = db.session.get(Usuario, user_id)
    
    if not usuario:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for('login'))
    
    print(f"👤 Cargando página de amigos para: {usuario.nombre_usuario} (ID: {usuario.id})")
    
    return render_template('amigos.html', usuario=usuario, user_id=user_id)

@app.route('/ver_perfil/<int:id>')
@requiere_sesion
def ver_perfil_usuario(id):
    """Ver perfil de otro usuario - En misma ventana"""
    user_id = session.get('user_id_temp') or session.get('user_id')
    
    if not user_id:
        flash("Debes iniciar sesión.", "error")
        return redirect(url_for('login'))
    
    usuario = db.session.get(Usuario, id)
    
    if not usuario:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for('inicio'))
    
    # Si es el mismo usuario, redirigir a su propio perfil
    if id == user_id:
        return redirect(url_for('mi_perfil'))
    
    # Contar degustaciones del usuario
    degustaciones_count = Degustacion.query.filter_by(usuario_id=id).count()
    
    # Obtener última degustación
    ultima_degustacion = Degustacion.query.filter_by(
        usuario_id=id
    ).order_by(Degustacion.fecha.desc()).first()
    
    # Verificar estado de amistad con el usuario actual
    es_amigo = False
    solicitud_pendiente = None
    
    amistad = Amistad.query.filter(
        ((Amistad.usuario_id == user_id) & (Amistad.amigo_id == id)) |
        ((Amistad.usuario_id == id) & (Amistad.amigo_id == user_id))
    ).first()
    
    if amistad:
        if amistad.estado == 'aceptado':
            es_amigo = True
        elif amistad.estado == 'pendiente':
            solicitud_pendiente = amistad
    
    return render_template(
        'ver_perfil.html',
        usuario=usuario,
        user_id=user_id,
        degustaciones_count=degustaciones_count,
        ultima_degustacion=ultima_degustacion,
        es_amigo=es_amigo,
        solicitud_pendiente=solicitud_pendiente,
        usuario_actual_id=user_id
    )

@app.route('/logout')
@requiere_sesion
def logout():
    session.pop('user_id', None)
    session.pop('user_id_temp', None)
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for('login'))

# ————— INICIALIZACIÓN —————
with app.app_context():
    db.create_all()
    seed_cervezas()

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