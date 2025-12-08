import pytest
from datetime import date # Importar date
from app import db, Usuario
from werkzeug.security import generate_password_hash # Importar generate_password_hash
from tests.conftest import generar_usuario_unico, generar_email_unico # Importar helpers si es necesario, aunque aquí no se usan directamente

class TestRutasPublicas:
    """Pruebas de integración para rutas públicas."""

    def test_registro_usuario_valido(self, client, setup_database):
        """Test que un usuario válido puede registrarse."""
        usuario_data = {
            'nombre_usuario': generar_usuario_unico(),
            'correo': generar_email_unico(),
            'contraseña': 'Password123',
            'contraseña2': 'Password123',
            'fecha_nacimiento': '1990-01-01'
        }
        response = client.post('/registro', data=usuario_data, follow_redirects=True)

        assert response.status_code == 200
        with client.application.app_context():
            usuario = Usuario.query.filter_by(nombre_usuario=usuario_data['nombre_usuario']).first()
            assert usuario is not None
            assert usuario.correo == usuario_data['correo']

    def test_registro_usuario_menor_edad(self, client, setup_database):
        """Test que un menor de edad no puede registrarse."""
        usuario_data = {
            'nombre_usuario': generar_usuario_unico(),
            'correo': generar_email_unico(),
            'contraseña': 'Password123',
            'contraseña2': 'Password123',
            'fecha_nacimiento': '2010-01-01' # Menor de 18
        }
        response = client.post('/registro', data=usuario_data, follow_redirects=True)

        assert response.status_code == 200
        assert b'mayor de 18' in response.data.lower() # Mensaje de error esperado
        with client.application.app_context():
            usuario = Usuario.query.filter_by(nombre_usuario=usuario_data['nombre_usuario']).first()
            assert usuario is None

    def test_registro_contrasenas_no_coinciden(self, client, setup_database):
        """Test que el registro falla si las contraseñas no coinciden."""
        usuario_data = {
            'nombre_usuario': generar_usuario_unico(),
            'correo': generar_email_unico(),
            'contraseña': 'Password123',
            'contraseña2': 'Password456', # Distinta
            'fecha_nacimiento': '1990-01-01'
        }
        response = client.post('/registro', data=usuario_data)

        assert response.status_code == 200
        assert b'no coinciden' in response.data.lower() # Mensaje de error esperado

    def test_login_exitoso(self, client, setup_database):
        """Test que un usuario registrado y verificado puede iniciar sesión."""
        with client.application.app_context():
            usuario = Usuario(
                nombre_usuario="login_test_user",
                correo="login_test@example.com",
                contraseña_hash=generate_password_hash("mipassword"), # Importado arriba
                fecha_nacimiento=date(1990, 1, 1), # Importado arriba
                verificado=True
            )
            db.session.add(usuario)
            db.session.commit()

        response = client.post('/login', data={
            'nombre_usuario': 'login_test_user',
            'contraseña': 'mipassword'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'inicio' in response.data.lower() # Se espera que redirija a la página de inicio

    def test_login_usuario_no_verificado(self, client, setup_database):
        """Test que un usuario no verificado no puede iniciar sesión."""
        with client.application.app_context():
            usuario = Usuario(
                nombre_usuario="no_verif_test_user",
                correo="no_verif_test@example.com",
                contraseña_hash=generate_password_hash("password"), # Importado arriba
                fecha_nacimiento=date(1990, 1, 1), # Importado arriba
                verificado=False # No verificado
            )
            db.session.add(usuario)
            db.session.commit()

        response = client.post('/login', data={
            'nombre_usuario': 'no_verif_test_user',
            'contraseña': 'password'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'verifica tu cuenta' in response.data.lower() # Mensaje de error esperado
