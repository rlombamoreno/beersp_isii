# tests/conftest.py
import pytest
import os
import sys
import tempfile
from datetime import date
import random
import string
from werkzeug.security import generate_password_hash

# Asegúrate de que la raíz del proyecto esté en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app, db, Usuario, Cerveza

# --- Fixtures y Funciones Auxiliares para Tests ---

def generar_email_unico():
    """Generar un email único para cada test."""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_{random_str}@example.com"

def generar_usuario_unico():
    """Generar un nombre de usuario único para cada test."""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"testuser_{random_str}"

@pytest.fixture(scope='session')
def app_instance():
    """Proporciona una instancia de la aplicación Flask configurada para pruebas."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    # Usar base de datos temporal para la sesión completa
    db_fd, db_path = tempfile.mkstemp()
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SECRET_KEY'] = 'test-secret-key-for-testing'

    with app.app_context():
        yield app
        # Limpiar la base de datos al finalizar la sesión
        os.close(db_fd)
        os.unlink(db_path)

@pytest.fixture(scope='session')
def client(app_instance):
    """Proporciona un cliente de prueba para hacer solicitudes HTTP."""
    with app_instance.test_client() as client:
        yield client

@pytest.fixture(scope='session')
def setup_database(app_instance):
    """Configura la base de datos para la sesión de pruebas."""
    with app_instance.app_context():
        db.create_all()
        # Cargar cervezas de ejemplo (similares a las tuyas)
        cervezas_data = [
            ("Mahou Cinco Estrellas", "Lager", "España", 5.5, 22, "Dorado"),
            ("IPA Test", "IPA", "España", 6.8, 65, "Ámbar"),
            ("Estrella Galicia", "Lager", "España", 5.5, 18, "Dorado"),
            ("Alhambra Reserva 1925", "Lager", "España", 6.4, 22, "Dorado"),
            ("Daura Damm", "Lager sin gluten", "España", 5.4, 20, "Dorado"),
            ("San Miguel 0,0", "Lager", "España", 0.0, 18, "Dorado"),
            ("Voll Damm", "Lager", "España", 5.4, 18, "Dorado"),
            ("Moritz", "Lager", "España", 5.5, 18, "Dorado"),
            ("Cruzcampo", "Lager", "España", 5.4, 18, "Dorado"),
            ("Ambar", "Lager", "España", 5.4, 18, "Dorado"),
            ("Galeton", "Barleywine", "España", 10.5, 40, "Marrón rojizo"),
            ("Zaragoza IPA", "West Coast IPA", "España", 6.8, 70, "Dorado turbio"),
            ("Lupulus H-75", "Double IPA", "España", 7.5, 85, "Ámbar intenso"),
        ]
        for nombre, estilo, pais, abv, ibu, color in cervezas_data:
            db.session.add(Cerveza(nombre=nombre, estilo=estilo, pais_procedencia=pais, porcentaje_alcohol=abv, ibu=ibu, color=color))
        db.session.commit()
        yield db # Proporciona la instancia de db
        db.drop_all()

@pytest.fixture
def usuario_prueba(client, setup_database):
    """Fixture para crear un usuario único de prueba."""
    with client.application.app_context():
        usuario = Usuario(
            nombre_usuario=generar_usuario_unico(),
            correo=generar_email_unico(),
            contraseña_hash=generate_password_hash("password123"),
            fecha_nacimiento=date(1990, 1, 1),
            verificado=True
        )
        db.session.add(usuario)
        db.session.commit()
        # Refrescar el objeto para asegurar que esté vinculado a la sesión actual
        # y no haya problemas con relaciones lazy loading si se usan más adelante
        db.session.refresh(usuario)
        return usuario

@pytest.fixture
def auth_client(client, usuario_prueba):
    """Cliente con usuario autenticado."""
    # El fixture `usuario_prueba` ya asegura que el objeto esté en la sesión actual
    # cuando `auth_client` lo use.
    with client.session_transaction() as session:
        session['user_id'] = usuario_prueba.id
    return client

# --- Datos de Prueba ---
@pytest.fixture
def usuario_datos_prueba():
    return {
        'nombre_usuario': 'usuarioprueba',
        'correo': 'test@example.com',
        'contraseña': 'password123',
        'fecha_nacimiento': date(1990, 1, 1)
    }

@pytest.fixture
def cerveza_datos_prueba():
    return {
        'nombre': 'Cerveza Test',
        'estilo': 'IPA',
        'pais_procedencia': 'España',
        'porcentaje_alcohol': 6.5,
        'ibu': 45,
        'color': 'Ámbar'
    }

# Constantes para pruebas
USUARIO_MAYOR_EDAD = date(2000, 1, 1)
USUARIO_MENOR_EDAD = date(2010, 1, 1)
