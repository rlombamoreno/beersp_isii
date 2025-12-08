import pytest
from datetime import date, datetime
from app import es_mayor_edad, allowed_file # Asegúrate de importar las funciones desde app.py
from werkzeug.security import generate_password_hash, check_password_hash

class TestFuncionesUtiles:
    """Pruebas unitarias para funciones de utilidad."""

    def test_es_mayor_edad_mayor(self):
        """Test que identifica correctamente a un mayor de edad."""
        fecha_mayor = date.today().replace(year=date.today().year - 25)
        assert es_mayor_edad(fecha_mayor) is True

    def test_es_mayor_edad_menor(self):
        """Test que identifica correctamente a un menor de edad."""
        fecha_menor = date.today().replace(year=date.today().year - 10)
        assert es_mayor_edad(fecha_menor) is False

    def test_es_mayor_edad_limite(self):
        """Test que identifica correctamente el límite de 18 años."""
        hoy = date.today()
        limite_fecha = hoy.replace(year=hoy.year - 18)
        # Caso base: cumple 18 hoy
        assert es_mayor_edad(limite_fecha) is True
        # Un día antes de cumplir 18
        un_dia_antes = limite_fecha.replace(day=limite_fecha.day - 1)
        assert es_mayor_edad(un_dia_antes) is True
        # Un día después (menor)
        un_dia_despues = limite_fecha.replace(day=limite_fecha.day + 1)
        assert es_mayor_edad(un_dia_despues) is False


    def test_allowed_file_valido(self):
        """Test que permite archivos de imagen válidos."""
        extensiones_validas = ['jpg', 'jpeg', 'png', 'gif']
        for ext in extensiones_validas:
            assert allowed_file(f"archivo.{ext}") is True
            assert allowed_file(f"ARCHIVO.{ext.upper()}") is True # Mayúsculas

    def test_allowed_file_invalido(self):
        """Test que deniega archivos no permitidos."""
        extensiones_invalidas = ['pdf', 'txt', 'exe', 'js', '']
        for ext in extensiones_invalidas:
            if ext:
                assert allowed_file(f"archivo.{ext}") is False
            else:
                assert allowed_file("archivo") is False # Sin ext
        assert allowed_file("archivo.") is False # Ext vacía


    def test_hash_password_correcto(self):
        """Test que el hash de contraseñas funciona."""
        password = "mi_contrasena_secreta_123"
        hash_result = generate_password_hash(password)
        assert check_password_hash(hash_result, password) is True
        assert check_password_hash(hash_result, "otra_contrasena") is False
        assert hash_result != password