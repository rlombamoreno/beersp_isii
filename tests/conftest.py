import pytest
import os
import sys
import tempfile
from datetime import date
import random
import string

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app, db, Usuario, Cerveza, Degustacion, Amistad, Galardon, UsuarioGalardon
from werkzeug.security import generate_password_hash

def generar_email_unico():
    """Generar un email único para cada test"""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_{random_str}@example.com"

def generar_usuario_unico():
    """Generar un nombre de usuario único para cada test"""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"testuser_{random_str}"

@pytest.fixture(scope='function')
def client():
    """Fixture para cliente de pruebas con base de datos temporal"""
    # Configurar base de datos temporal
    db_fd, db_path = tempfile.mkstemp()
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SECRET_KEY'] = 'test-secret-key-for-testing'
    
    # Establecer contexto de aplicación
    app_context = app.app_context()
    app_context.push()
    
    # Crear tablas
    db.create_all()
    
    # Crear datos básicos de prueba (SOLO cervezas, no usuarios)
    crear_cervezas_prueba()
    
    with app.test_client() as client:
        yield client
    
    # Limpieza
    db.session.remove()
    db.drop_all()
    app_context.pop()
    
    os.close(db_fd)
    os.unlink(db_path)

def crear_cervezas_prueba():
    """Crear solo cervezas de prueba (sin usuarios)"""
    try:
        # Crear cervezas de prueba
        cerveza1 = Cerveza(
            nombre="Mahou Cinco Estrellas",
            estilo="Lager", 
            pais_procedencia="España",
            porcentaje_alcohol=5.5,
            ibu=22,
            color="Dorado"
        )
        
        cerveza2 = Cerveza(
            nombre="IPA Test",
            estilo="IPA",
            pais_procedencia="España", 
            porcentaje_alcohol=6.8,
            ibu=65,
            color="Ámbar"
        )
        
        db.session.add(cerveza1)
        db.session.add(cerveza2)
        db.session.commit()
        print("Cervezas de prueba creadas correctamente")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creando cervezas de prueba: {e}")
        raise

@pytest.fixture
def usuario_prueba(client):
    """Fixture para crear un usuario único de prueba"""
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
        return usuario

@pytest.fixture
def auth_client(client, usuario_prueba):
    """Cliente con usuario autenticado"""
    with client.session_transaction() as session:
        session['user_id'] = usuario_prueba.id
    return client