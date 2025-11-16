import pytest
from datetime import date
from app import es_mayor_edad, allowed_file
from werkzeug.security import generate_password_hash, check_password_hash

class TestAutenticacion:
    """Pruebas para funciones de autenticacion y seguridad"""
    
    def test_es_mayor_edad_casos(self):
        """Test funcion es_mayor_edad con diferentes casos"""
        # Mayor de edad (nacido en 2000)
        assert es_mayor_edad(date(2000, 1, 1)) == True
        
        # Menor de edad (nacido en 2010)
        assert es_mayor_edad(date(2010, 1, 1)) == False
        
        # Justo 18 años hoy (depende de la fecha actual)
        from datetime import datetime
        hoy = datetime.now().date()
        justo_18 = date(hoy.year - 18, hoy.month, hoy.day)
        assert es_mayor_edad(justo_18) == True
        
        # Un dia antes de cumplir 18
        un_dia_antes = date(hoy.year - 18, hoy.month, hoy.day + 1)
        assert es_mayor_edad(un_dia_antes) == False
    
    def test_allowed_file(self):
        """Test validacion de archivos permitidos"""
        # Extensiones permitidas
        assert allowed_file("foto.jpg") == True
        assert allowed_file("imagen.png") == True
        assert allowed_file("perfil.jpeg") == True
        assert allowed_file("avatar.gif") == True
        
        # Extensiones NO permitidas
        assert allowed_file("documento.pdf") == False
        assert allowed_file("script.js") == False
        assert allowed_file("archivo.txt") == False
        
        # Casos edge
        assert allowed_file("sin_extension") == False
        assert allowed_file(".") == False
        assert allowed_file("") == False
    
    def test_hash_password(self):
        """Test que las contraseñas se hashean correctamente"""
        password = "mi_contrasena_secreta_123"
        
        # Generar hash
        hash_result = generate_password_hash(password)
        
        # Verificar que el hash funciona
        assert check_password_hash(hash_result, password) == True
        assert check_password_hash(hash_result, "otra_contrasena") == False
        assert check_password_hash(hash_result, "") == False
        
        # Verificar que el hash no es la contraseña en texto plano
        assert hash_result != password
        assert "mi_contrasena_secreta_123" not in hash_result
    
    def test_fecha_nacimiento_formato(self):
        """Test manejo de diferentes formatos de fecha"""
        # Esta prueba es para verificar que el formulario maneja formatos de fecha
        # Por ahora es un placeholder
        pass