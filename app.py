import os
import webbrowser
import threading
import time
import uuid
from datetime import datetime, timedelta,timezone
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 2 * 1024 * 1024

load_dotenv()

# Asegurar que la carpeta 'instance' exista
basedir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(basedir, 'instance')
static_fotos_dir = os.path.join(basedir, 'static', 'fotos')


os.makedirs('instance', exist_ok=True)
os.makedirs('static/fotos', exist_ok=True)

app = Flask(__name__)
app.config['SERVER_NAME'] = 'localhost:5000'
app.config['SECRET_KEY'] = 'una_clave_secreta_muy_segura'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_dir, "beersp.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración de correo
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = ("BeerSp 🍻", os.getenv('MAIL_USERNAME'))

db = SQLAlchemy(app)
mail = Mail(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# -------------------------
# Modelos
# -------------------------

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
    estado = db.Column(db.String(20), default='pendiente')  # 'pendiente', 'aceptado', 'rechazado'
    fecha_solicitud = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint('usuario_id', 'amigo_id', name='_amistad_uc'),)

class Cerveza(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    estilo = db.Column(db.String(50), nullable=False)  # IPA, Lager, etc.
    pais_procedencia = db.Column(db.String(50), nullable=False)
    porcentaje_alcohol = db.Column(db.Float, nullable=False)
    ibu = db.Column(db.Integer)
    color = db.Column(db.String(50))

class Degustacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    cerveza_id = db.Column(db.Integer, db.ForeignKey('cerveza.id'), nullable=False)
    puntuacion = db.Column(db.Float)  # 0 a 5, puede ser NULL
    fecha = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    comentario = db.Column(db.Text)
    # Local, "me gusta", etc. → se pueden añadir después

class Galardon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.Text)

class UsuarioGalardon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    galardon_id = db.Column(db.Integer, db.ForeignKey('galardon.id'), nullable=False)
    nivel = db.Column(db.Integer, default=1)
    fecha_obtenido = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint('usuario_id', 'galardon_id', name='_usuario_galardon_uc'),)

# -------------------------
# Funciones auxiliares
# -------------------------

def enviar_correo_verificacion(correo, nombre_usuario):
    token = serializer.dumps(correo, salt='verificacion-email')
    enlace = url_for('verificar_email', token=token, _external=True)
    msg = Message(
        subject="¡Verifica tu cuenta en BeerSp!",
        recipients=[correo],
        body=f"Hola {nombre_usuario},\n\n"
             f"Por favor, haz clic en el siguiente enlace para verificar tu cuenta:\n{enlace}\n\n"
             "Gracias por unirte a BeerSp."
    )
    mail.send(msg)

def es_mayor_edad(fecha_nac):
    hoy = datetime.now(timezone.utc).date()
    edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
    return edad >= 18

# -------------------------
# Autoabrir navegador
# -------------------------

def abrir_navegador():
    time.sleep(1.5)  # Espera a que Flask arranque
    webbrowser.open_new("http://127.0.0.1:5000/")

# -------------------------
# Rutas
# -------------------------

@app.route('/')
def index():
    return redirect(url_for('registro'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre_usuario = request.form['nombre_usuario']
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        contraseña2 = request.form['contraseña2']
        fecha_nac_str = request.form['fecha_nacimiento']

        if contraseña != contraseña2:
            flash("Las contraseñas no coinciden.", "error")
            return render_template('registro.html')

        try:
            fecha_nac = datetime.strptime(fecha_nac_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Fecha de nacimiento inválida.", "error")
            return render_template('registro.html')

        if not es_mayor_edad(fecha_nac):
            flash("Debes ser mayor de 18 años para registrarte.", "error")
            return render_template('registro.html')

        if Usuario.query.filter_by(nombre_usuario=nombre_usuario).first():
            flash("Nombre de usuario ya existe.", "error")
            return render_template('registro.html')

        if Usuario.query.filter_by(correo=correo).first():
            flash("Correo ya registrado.", "error")
            return render_template('registro.html')

        nuevo_usuario = Usuario(
            nombre_usuario=nombre_usuario,
            correo=correo,
            contraseña_hash=generate_password_hash(contraseña),
            fecha_nacimiento=fecha_nac,
            verificado=False
        )
        db.session.add(nuevo_usuario)
        db.session.commit()

        try:
            enviar_correo_verificacion(correo, nombre_usuario)
            flash("¡Registro exitoso! Revisa tu correo para verificar tu cuenta.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al enviar el correo: {str(e)}", "error")
            return render_template('registro.html')

        return redirect(url_for('login'))

    return render_template('registro.html')

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
            flash(f"¡Bienvenido, {usuario.nombre_usuario}!", "success")
            return redirect(url_for('inicio', id=usuario.id))

    return render_template('login.html')


@app.route('/olvide_contrasena', methods=['GET', 'POST'])
def olvide_contrasena():
    if request.method == 'POST':
        correo = request.form['correo']
        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario:
            # Generar token de restablecimiento
            token = serializer.dumps(correo, salt='restablecer-contrasena')
            enlace = url_for('restablecer_contrasena', token=token, _external=True)
            # Enviar correo
            msg = Message(
                subject="Restablece tu contraseña en BeerSp",
                recipients=[correo],
                body=f"Hola {usuario.nombre_usuario},\n\n"
                     f"Hemos recibido una solicitud para restablecer tu contraseña.\n"
                     f"Haz clic en el siguiente enlace (válido 1 hora):\n{enlace}\n\n"
                     "Si no fuiste tú, ignora este mensaje."
            )
            mail.send(msg)
        # Siempre mostramos el mismo mensaje (seguridad: no revelar si el correo existe)
        flash("Si tu correo está registrado, recibirás un enlace para restablecer tu contraseña.", "success")
        return redirect(url_for('login'))
    return render_template('olvide_contrasena.html')


@app.route('/restablecer/<token>', methods=['GET', 'POST'])
def restablecer_contrasena(token):
    try:
        correo = serializer.loads(token, salt='restablecer-contrasena', max_age=3600)  # 1 hora
    except:
        flash("El enlace es inválido o ha expirado.", "error")
        return redirect(url_for('olvide_contrasena'))

    if request.method == 'POST':
        contraseña_nueva = request.form['contraseña_nueva']
        contraseña_confirm = request.form['contraseña_confirm']
        if contraseña_nueva != contraseña_confirm:
            flash("Las contraseñas no coinciden.", "error")
            return render_template('restablecer.html', token=token)
        # Actualizar contraseña
        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario:
            usuario.contraseña_hash = generate_password_hash(contraseña_nueva)
            db.session.commit()
            flash("Tu contraseña ha sido actualizada. Ya puedes iniciar sesión.", "success")
            return redirect(url_for('login'))
    return render_template('restablecer.html', token=token)


@app.route('/inicio/<int:id>')
def inicio(id):
    usuario = Usuario.query.get_or_404(id)

    # Estadísticas reales
    degustaciones = Degustacion.query.filter_by(usuario_id=id).count()
    locales_nuevos = 0  # se puede ampliar más tarde

    # Solicitudes de amistad pendientes donde el usuario es el destinatario
    solicitudes_amistad = Amistad.query.filter_by(amigo_id=id, estado='pendiente').count()

    # Amigos aceptados (bidireccional)
    amigos_ids_1 = db.session.query(Amistad.amigo_id).filter_by(usuario_id=id, estado='aceptado')
    amigos_ids_2 = db.session.query(Amistad.usuario_id).filter_by(amigo_id=id, estado='aceptado')
    amigos_ids = {r[0] for r in amigos_ids_1.union(amigos_ids_2)}

    # Actividad de amigos (última degustación de cada amigo)
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

    # Tus cervezas favoritas (puntuación >= 4)
    cervezas_favoritas = []
    degustaciones_altas = Degustacion.query.filter(
        Degustacion.usuario_id == id,
        Degustacion.puntuacion >= 4.0
    ).order_by(Degustacion.puntuacion.desc()).limit(3).all()

    for d in degustaciones_altas:
        c = Cerveza.query.get(d.cerveza_id)
        if c:
            cervezas_favoritas.append({
                'nombre': c.nombre,
                'estilo': c.estilo,
                'puntuacion': d.puntuacion
            })

    # Tus últimos galardones
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
            'locales_nuevos': locales_nuevos,
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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
           

@app.route('/perfil/<int:id>/editar', methods=['GET', 'POST'])
def editar_perfil(id):
    usuario = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        # Validar nombre de usuario
        nuevo_usuario = request.form['nombre_usuario'].strip()
        if nuevo_usuario != usuario.nombre_usuario:
            if Usuario.query.filter_by(nombre_usuario=nuevo_usuario).first():
                flash("Nombre de usuario ya en uso.", "error")
                return render_template('editar_perfil.html', usuario=usuario)

        # Actualizar campos de texto
        usuario.nombre_usuario = nuevo_usuario
        usuario.nombre = request.form.get('nombre') or None
        usuario.apellidos = request.form.get('apellidos') or None
        usuario.ubicacion = request.form.get('ubicacion') or None
        usuario.genero = request.form.get('genero') or None
        usuario.presentacion = request.form.get('presentacion') or None

        # Subir foto (si se ha enviado)
        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename != '':
                if not allowed_file(file.filename):
                    flash("Tipo de archivo no permitido. Usa JPG, PNG o GIF.", "error")
                    return render_template('editar_perfil.html', usuario=usuario)
                if len(file.read()) > MAX_FILE_SIZE:
                    flash("La imagen es demasiado grande (máx. 2 MB).", "error")
                    return render_template('editar_perfil.html', usuario=usuario)
                file.seek(0)  # Reiniciar puntero tras leer

                # Generar nombre único
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"user_{usuario.id}_{uuid.uuid4().hex[:8]}.{ext}"
                ffilepath = os.path.join(static_fotos_dir, filename)
                file.save(ffilepath)

                # Borrar foto anterior si existe y no es la por defecto
                if usuario.foto and usuario.foto.startswith('user_'):
                    old_path = os.path.join('static/fotos', usuario.foto)
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
        # Confirmación: el formulario debe incluir un campo oculto o checkbox
        confirmacion = request.form.get('confirmar')
        if confirmacion == 'si':
            # Eliminar al usuario y sus datos relacionados
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
# -------------------------
# Inicialización
# -------------------------

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Autoabrir navegador en modo local
    threading.Thread(target=abrir_navegador, daemon=True).start()
    app.run(host='127.0.0.1', port=5000, debug=False)