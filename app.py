import os
import webbrowser
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv

load_dotenv()

# Asegurar que la carpeta 'instance' exista
os.makedirs('instance', exist_ok=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'una_clave_secreta_muy_segura'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "beersp.db")}'
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
    verificado = db.Column(db.Boolean, default=False)

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
    hoy = datetime.now(datetime.timezone.utc).date()
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
            return redirect(url_for('perfil', id=usuario.id))

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


@app.route('/perfil/<int:id>')
def perfil(id):
    usuario = Usuario.query.get_or_404(id)
    return f"<h1>Perfil de {usuario.nombre_usuario}</h1><p>Verificado: {'Sí' if usuario.verificado else 'No'}</p>"

# -------------------------
# Inicialización
# -------------------------

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Autoabrir navegador en modo local
    threading.Thread(target=abrir_navegador, daemon=True).start()
    app.run(host='127.0.0.1', port=5000, debug=False)