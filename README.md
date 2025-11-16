# BeerSp - Plataforma Social de Cervezas

##  Estructura del Proyecto

```
beersp/
├── app.py                 # Lógica principal de la aplicación
├── requirements.txt       # Dependencias de Python
├── .env.example           # Plantilla de variables de entorno
├── instance/              # Base de datos SQLite (generada automáticamente)
├── static/fotos/          # Fotos de perfil de usuarios (solo en local)
└── tests/ # Suite de pruebas automatizadas
│   ├── test_models.py
│   ├── test_routes.py
│   ├── test_authentication.py
│   ├── test_form.py
│   └── conftest.py
└── templates/             # Plantillas HTML
    ├── base.html          # Plantilla base
    ├── registro.html      # Registro de usuarios
    ├── login.html         # Inicio de sesión
    ├── inicio.html        # Dashboard principal
    ├── perfil.html        # Perfil de usuario
    └── ...                # Otras plantillas
```

## Instalación Local

1. **Clona el repositorio**:
```bash
git clone https://github.com/tu-usuario/beersp.git
cd beersp
```

2. **Instala dependencias**:
```bash
pip install -r requirements.txt
```

3. **Configura variables de entorno**:
```bash
Crear archivo .env siguiendo el .env.example
```

5. **Ejecuta la aplicación**:
```bash
python app.py
```

La aplicación estará disponible en `http://127.0.0.1:5000`
ADEMÁS LA APLICACIÓN ESTA DESPLEGADA EN render.com EN EL SIGUIENTE ENLACE https://beersp-isii.onrender.com (puede tardar unos minutos si el programa esta en sleep)

**Ejecuión de pruebas**:
```bash
# Ejecutar todas las pruebas
pytest -v

# Ejecutar pruebas específicas
pytest tests/test_models.py -v
pytest tests/test_routes.py -v
```

---
