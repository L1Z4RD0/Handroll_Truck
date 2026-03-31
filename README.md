Sistema de Detección y Control de Camiones
Este proyecto utiliza YOLOv8 para el seguimiento de vehículos en tiempo real y registra los eventos de entrada/salida en una base de datos PostgreSQL.

Requisitos Previos
Antes de empezar, asegúrate de tener instalado:

Python 3.10+

PostgreSQL 16 

Iriun Webcam: Instalado tanto en tu PC como en tu celular para usarlo como cámara inalámbrica.

Instalación para el Equipo
1. Clonar y preparar el entorno
Una vez que clones el repositorio, el entorno virtual (venv) no estará presente. Debes crearlo e instalar las dependencias:

Bash
# Crear entorno virtual
python -m venv venv_camiones

# Activarlo (Windows)
venv_camiones\Scripts\activate

# Instalar librerías necesarias
pip install -r requirements.txt

2. Configuración de Variables de Entorno (.env)
Como el archivo .env no se sube a GitHub por seguridad, cada uno debe crear su propio archivo .env en la carpeta raíz con este formato:


DB_HOST=localhost
DB_NAME=deteccion_camiones
DB_USER=postgres
DB_PASSWORD=tu_contraseña_aqui
CAMARA_INDEX=1

Nota sobre la Cámara: Si usas un PC de escritorio sin webcam integrada, prueba cambiar CAMARA_INDEX a 0. Si usas notebook con Iriun, usa 1.

3. Configuración de la Base de Datos (PostgreSQL)
Antes de correr el programa, debes preparar el entorno de datos localmente.

Entrar a PostgreSQL:

Bash
psql -U postgres
(Te pedirá la contraseña que configuraste al instalar Postgres).

Crear la base de datos:
Dentro de la consola de postgres (postgres=#), ejecuta:

SQL
CREATE DATABASE deteccion_camiones;
Conectarse a la base de datos:

SQL
\c deteccion_camiones
Cargar el esquema y datos iniciales:
Para crear las tablas y registrar la cámara base, sal de psql con \q y ejecuta este comando desde la carpeta del proyecto:

Bash
psql -U postgres -d deteccion_camiones -f schema.sql
 

Uso de Iriun Webcam
Abre la app en tu celular.

Abre la app en tu PC.

Asegúrate de que ambos estén en la misma red Wi-Fi.

El programa detectará la entrada de video automáticamente según el índice que configuraste en tu .env.

Umbrales de bytetrack.yaml

track_high_thresh	Umbral de confianza alto	Subirlo: Filtra detecciones dudosas (menos ruido). Bajarlo: Rastrea vehículos más lejanos o borrosos.

track_low_thresh	Umbral de confianza bajo	Ayuda a recuperar el rastro si el vehículo pasa por una zona oscura o con sombra donde la IA "duda".

new_track_thresh	Umbral para nuevo ID	Confianza mínima que debe tener una detección para que el sistema le asigne un Track ID nuevo.

track_buffer	Memoria de rastreo	Cantidad de frames que el sistema "espera" a un vehículo que desapareció (ej. tras un poste) antes de borrar su ID.

match_thresh	Umbral de coincidencia	Qué tan parecida debe ser la posición actual a la anterior (IoU) para decir que es el mismo vehículo.

fuse_scoreFusión de puntajeSi está en True, combina la confianza de la IA con la lógica de movimiento para estabilizar detecciones débiles.


