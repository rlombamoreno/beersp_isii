# tests/__init__.py
"""
Paquete de pruebas para BeerSp - Configuración centralizada
"""

import os
import tempfile
import pytest
from datetime import datetime, date

# Configuración de entorno de pruebas
os.environ['TESTING'] = 'True'

# Fixtures comunes que pueden ser usadas en múltiples archivos de prueba
@pytest.fixture
def usuario_datos_prueba():
    """Datos de ejemplo para crear usuarios de prueba"""
    return {
        'nombre_usuario': 'usuarioprueba',
        'correo': 'test@example.com',
        'contraseña': 'password123',
        'fecha_nacimiento': date(1990, 1, 1)
    }

@pytest.fixture
def cerveza_datos_prueba():
    """Datos de ejemplo para crear cervezas de prueba"""
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