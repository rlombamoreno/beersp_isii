import pytest
from app import allowed_file

def test_validacion_archivos_imagen():
    """Test que valida que SOLO se permiten archivos png, jpg, jpeg, gif"""
    
    assert allowed_file("foto.jpg") == True
    assert allowed_file("imagen.jpeg") == True
    assert allowed_file("picture.png") == True
    assert allowed_file("avatar.gif") == True
    
    assert allowed_file("FOTO.JPG") == True
    assert allowed_file("IMAGEN.JPEG") == True
    assert allowed_file("PICTURE.PNG") == True
    assert allowed_file("AVATAR.GIF") == True
    
    assert allowed_file("foto.final.jpg") == True
    assert allowed_file("imagen.backup.png") == True
    
    assert allowed_file("documento.pdf") == False
    assert allowed_file("script.js") == False
    assert allowed_file("archivo.txt") == False
    assert allowed_file("video.mp4") == False
    assert allowed_file("documento.doc") == False
    assert allowed_file("planilla.xlsx") == False
    assert allowed_file("presentacion.ppt") == False
    assert allowed_file("comprimido.zip") == False
    
    assert allowed_file("") == False
    assert allowed_file("archivo.") == False
    assert allowed_file("archivo_sin_extension") == False
    assert allowed_file("...") == False
    assert allowed_file("   ") == False