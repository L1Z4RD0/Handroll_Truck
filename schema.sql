CREATE DATABASE deteccion_camiones;

CREATE TABLE plantas (
    id        SERIAL PRIMARY KEY,
    nombre    VARCHAR(100) NOT NULL,
    ubicacion VARCHAR(200),
    creado_en TIMESTAMP DEFAULT NOW(),
    activa    BOOLEAN DEFAULT TRUE
);

CREATE TABLE camaras (
    id             SERIAL PRIMARY KEY,
    planta_id      INT REFERENCES plantas(id),
    nombre         VARCHAR(100) NOT NULL,
    ubicacion_desc VARCHAR(100),
    linea_a_px     INT,
    linea_b_px     INT,
    activa         BOOLEAN DEFAULT TRUE
);

CREATE TABLE eventos_vehiculos (
    id            BIGSERIAL PRIMARY KEY,
    camara_id     INT REFERENCES camaras(id),
    tipo          VARCHAR(10) CHECK (tipo IN ('entrada','salida')),
    tipo_vehiculo VARCHAR(10) CHECK (tipo_vehiculo IN ('auto','bus','camion')),
    track_id      INT,
    linea_cruzada VARCHAR(1) CHECK (linea_cruzada IN ('A','B')),
    lado_origen   VARCHAR(3) CHECK (lado_origen IN ('izq','der')),
    confianza     FLOAT,
    timestamp     TIMESTAMP DEFAULT NOW()
);

INSERT INTO plantas (nombre, ubicacion) VALUES ('Planta Principal', 'Arica, Chile');
INSERT INTO camaras (planta_id, nombre, ubicacion_desc, linea_a_px, linea_b_px) VALUES (1, 'Camara Acceso Principal', 'Entrada principal planta', 500, 950);