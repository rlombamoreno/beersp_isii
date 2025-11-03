# BeerSp 🍻 - Plataforma Social de Cervezas

BeerSp es una plataforma social para amantes de la cerveza donde puedes descubrir, compartir y degustar diferentes variedades de cervezas, conectar con otros entusiastas y llevar un registro de tus experiencias cerveceras.

## Características

- **Perfil de usuario personalizable** con foto, información personal y presentación
- **Sistema de degustaciones** para registrar y puntuar cervezas
- **Sistema de amistades** para conectar con otros usuarios
- **Galardones y logros** por actividades en la plataforma
- **Interfaz responsive** adaptada para móviles y desktop
- **Sistema de verificación por email** y recuperación de contraseña

##  Estado del Proyecto

 **En desarrollo** - Este proyecto está actualmente en fase de desarrollo activo. Algunas funcionalidades pueden estar en proceso de implementación o sujetas a cambios.

##  Tecnologías Utilizadas

- **Backend**: Flask (Python)
- **Base de datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **Frontend**: Bootstrap 5, HTML5, CSS3
- **Email**: Flask-Mail (Gmail/Brevo)
- **Despliegue**: Render

##  Estructura del Proyecto

```
beersp/
├── app.py                 # Lógica principal de la aplicación
├── requirements.txt       # Dependencias de Python
├── .env.example           # Plantilla de variables de entorno
├── instance/              # Base de datos SQLite (generada automáticamente)
├── static/fotos/          # Fotos de perfil de usuarios (solo en local)
└── templates/             # Plantillas HTML
    ├── base.html          # Plantilla base
    ├── registro.html      # Registro de usuarios
    ├── login.html         # Inicio de sesión
    ├── inicio.html        # Dashboard principal
    ├── perfil.html        # Perfil de usuario
    └── ...                # Otras plantillas
```

##  Demo en Vivo

El proyecto está desplegado en **Render** y disponible en:
🔗 **https://beersp-isii.onrender.com/**

## 🚀 Instalación Local

1. **Clona el repositorio**:
```bash
git clone https://github.com/tu-usuario/beersp.git
cd beersp
```

2. **Configura el entorno virtual**:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Instala dependencias**:
```bash
pip install -r requirements.txt
```

4. **Configura variables de entorno**:
```bash
cp .env.example .env
# Edita .env con tus configuraciones
```

5. **Ejecuta la aplicación**:
```bash
python app.py
```

La aplicación estará disponible en `http://127.0.0.1:5000`

---

*BeerSp - Conectando amantes de la cerveza desde 2024* 🍻
