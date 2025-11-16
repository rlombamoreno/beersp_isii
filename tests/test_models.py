import pytest
from datetime import date, datetime
from app import db, Usuario, Cerveza, Degustacion, Amistad, Galardon, UsuarioGalardon
from werkzeug.security import check_password_hash, generate_password_hash
import random
import string

def generar_email_unico():
    """Generar un email único para cada test"""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_{random_str}@example.com"

def generar_usuario_unico():
    """Generar un nombre de usuario único para cada test"""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"testuser_{random_str}"

class TestModelos:
    """Pruebas para los modelos de la base de datos"""
    
    def test_crear_usuario(self, client):
        """Test creacion de usuario basico"""
        with client.application.app_context():
            # Usar datos únicos para evitar conflictos
            usuario = Usuario(
                nombre_usuario="usuario_unico_test",
                correo="unico@test.com",
                contraseña_hash=generate_password_hash("testpass"),
                fecha_nacimiento=date(1995, 5, 15),
                verificado=True
            )
            db.session.add(usuario)
            db.session.commit()
            
            usuario_db = Usuario.query.filter_by(nombre_usuario="usuario_unico_test").first()
            assert usuario_db is not None
            assert usuario_db.correo == "unico@test.com"
            assert usuario_db.verificado == True
            assert check_password_hash(usuario_db.contraseña_hash, "testpass") == True
    
    def test_usuario_campos_opcionales(self, client):
        """Test usuario con campos opcionales"""
        with client.application.app_context():
            usuario = Usuario(
                nombre_usuario="usuario_completo_test",
                correo="completo_test@test.com", 
                contraseña_hash=generate_password_hash("pass"),
                fecha_nacimiento=date(1985, 3, 20),
                verificado=True,
                nombre="Juan",
                apellidos="Perez Garcia",
                ubicacion="Madrid, España",
                genero="masculino",
                presentacion="Amante de las cervezas artesanales"
            )
            db.session.add(usuario)
            db.session.commit()
            
            usuario_db = Usuario.query.filter_by(nombre_usuario="usuario_completo_test").first()
            assert usuario_db.nombre == "Juan"
            assert usuario_db.apellidos == "Perez Garcia"
            assert usuario_db.ubicacion == "Madrid, España"
            assert usuario_db.genero == "masculino"
            assert usuario_db.presentacion == "Amante de las cervezas artesanales"
    
    def test_relacion_degustacion(self, client):
        """Test relacion entre usuario y degustacion"""
        with client.application.app_context():
            # Crear usuario dentro del mismo contexto
            usuario = Usuario(
                nombre_usuario=generar_usuario_unico(),
                correo=generar_email_unico(),
                contraseña_hash=generate_password_hash("pass"),
                fecha_nacimiento=date(1990, 1, 1),
                verificado=True
            )
            db.session.add(usuario)
            db.session.commit()
            
            # Obtener cerveza existente
            cerveza = Cerveza.query.first()
            
            # Crear degustacion
            degustacion = Degustacion(
                usuario_id=usuario.id,
                cerveza_id=cerveza.id,
                puntuacion=4.5,
                comentario="Muy buena cerveza, sabor equilibrado"
            )
            db.session.add(degustacion)
            db.session.commit()
            
            # Verificar relaciones
            assert degustacion.usuario_id == usuario.id
            assert degustacion.cerveza_id == cerveza.id
            
            # Verificar que la degustación existe para este usuario
            degustaciones_usuario = Degustacion.query.filter_by(usuario_id=usuario.id).all()
            assert len(degustaciones_usuario) == 1
            assert degustacion in degustaciones_usuario
    
    def test_amistad_pendiente(self, client):
        """Test creacion de solicitud de amistad"""
        with client.application.app_context():
            # Crear dos usuarios únicos
            usuario1 = Usuario(
                nombre_usuario="usuario1_amistad",
                correo="user1_amistad@test.com",
                contraseña_hash=generate_password_hash("pass"),
                fecha_nacimiento=date(1990, 1, 1)
            )
            usuario2 = Usuario(
                nombre_usuario="usuario2_amistad", 
                correo="user2_amistad@test.com",
                contraseña_hash=generate_password_hash("pass"),
                fecha_nacimiento=date(1991, 2, 2)
            )
            db.session.add_all([usuario1, usuario2])
            db.session.commit()
            
            # Crear solicitud de amistad
            amistad = Amistad(
                usuario_id=usuario1.id,
                amigo_id=usuario2.id,
                estado='pendiente'
            )
            db.session.add(amistad)
            db.session.commit()
            
            # Verificar
            amistad_db = Amistad.query.filter_by(usuario_id=usuario1.id, amigo_id=usuario2.id).first()
            assert amistad_db is not None
            assert amistad_db.estado == 'pendiente'
    
    def test_galardon_usuario(self, client):
        """Test asignacion de galardon a usuario"""
        with client.application.app_context():
            # Crear usuario único
            usuario = Usuario(
                nombre_usuario="usuario_galardon",
                correo="galardon_usuario@test.com",
                contraseña_hash=generate_password_hash("pass"),
                fecha_nacimiento=date(1990, 1, 1)
            )
            
            # Crear galardon
            galardon = Galardon(
                nombre="Catador Profesional Test",
                descripcion="Por probar mas de 50 cervezas diferentes"
            )
            
            db.session.add_all([usuario, galardon])
            db.session.commit()
            
            # Asignar galardon a usuario
            usuario_galardon = UsuarioGalardon(
                usuario_id=usuario.id,
                galardon_id=galardon.id,
                nivel=2
            )
            db.session.add(usuario_galardon)
            db.session.commit()
            
            # Verificar - CORREGIDO: usar join para acceder al nombre del galardón
            ug_db = UsuarioGalardon.query.filter_by(usuario_id=usuario.id).first()
            assert ug_db is not None
            assert ug_db.nivel == 2
            assert ug_db.galardon_id == galardon.id
            
            # Para verificar el nombre, necesitamos hacer un join o consultar el galardón por separado
            galardon_db = db.session.get(Galardon, ug_db.galardon_id)
            assert galardon_db.nombre == "Catador Profesional Test"