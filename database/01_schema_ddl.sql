/* ESQUEMA DE BASE DE DATOS - GOBIERNO DE DATOS CALI
   Optimizado para: PostgreSQL 15+ y NocoDB
   Versión: 2.1 (Con integridad referencial estricta)
*/

CREATE SCHEMA IF NOT EXISTS catalogo;
SET search_path TO catalogo, public;

-- ==========================================
-- 1. TABLAS DIMENSIONALES (MAESTROS ÚNICOS)
-- Aquí se define el "Qué" una sola vez.
-- ==========================================

CREATE TABLE dim_dominio (
    id_dominio SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE,        -- Ej: DOM-001
    nombre_dominio VARCHAR(200) NOT NULL,
    sigla VARCHAR(10)
);

CREATE TABLE dim_area (
    id_area SERIAL PRIMARY KEY,
    id_dominio INTEGER REFERENCES dim_dominio(id_dominio),
    nombre_area VARCHAR(200) NOT NULL
);

CREATE TABLE dim_herramienta_tic (
    id_herramienta SERIAL PRIMARY KEY,
    nombre_herramienta VARCHAR(100) NOT NULL,
    url_acceso VARCHAR(500)
);

CREATE TABLE dim_ubicacion (
    id_ubicacion SERIAL PRIMARY KEY,
    nombre_sede VARCHAR(200) NOT NULL, -- Ej: "CAM Torre Alcaldía" (Único)
    direccion VARCHAR(300),
    horario VARCHAR(300)
);

CREATE TABLE dim_requisito (
    id_requisito VARCHAR(20) PRIMARY KEY, -- Ej: R001. Aquí reside la unicidad.
    nombre_requisito VARCHAR(500) NOT NULL,
    tipo_soporte VARCHAR(50) -- Digital, Físico
);

CREATE TABLE dim_estado (
    id_estado SERIAL PRIMARY KEY,
    nombre_estado VARCHAR(50) NOT NULL
);

-- ==========================================
-- 2. TABLA DE HECHOS (SERVICIOS)
-- ==========================================

CREATE TABLE fact_servicio (
    id_servicio SERIAL PRIMARY KEY,
    codigo_servicio VARCHAR(20) UNIQUE NOT NULL, -- Ej: CULT-001
    
    -- Relaciones (Apuntan a los maestros únicos)
    id_dominio INTEGER REFERENCES dim_dominio(id_dominio),
    id_area INTEGER REFERENCES dim_area(id_area),
    id_herramienta_tic INTEGER REFERENCES dim_herramienta_tic(id_herramienta),
    id_estado INTEGER REFERENCES dim_estado(id_estado),
    
    -- Datos propios del servicio
    nombre_servicio VARCHAR(500) NOT NULL,
    descripcion TEXT,
    proposito TEXT,
    dirigido_a TEXT,
    tiempo_respuesta VARCHAR(100),
    fundamento_legal TEXT,
    informacion_costo TEXT,
    
    volumen_mensual_promedio INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 3. TABLAS DE RELACIÓN (CONECTORES)
-- Estas tablas NO guardan texto, solo unen IDs.
-- ==========================================

-- Tabla Puente: Un Servicio tiene N Requisitos
CREATE TABLE rel_servicio_requisito (
    id_rel SERIAL PRIMARY KEY,
    id_servicio INTEGER NOT NULL REFERENCES fact_servicio(id_servicio) ON DELETE CASCADE,
    id_requisito VARCHAR(20) NOT NULL REFERENCES dim_requisito(id_requisito) ON DELETE RESTRICT,
    
    -- Atributos de la relación (¿Es obligatorio PARA ESTE servicio?)
    es_obligatorio BOOLEAN DEFAULT TRUE,
    observacion TEXT,

    -- Restricción Única Compuesta: Evita duplicar el mismo requisito en el mismo servicio
    CONSTRAINT uk_servicio_requisito UNIQUE (id_servicio, id_requisito)
);

-- Tabla Puente: Un Servicio tiene N Ubicaciones
CREATE TABLE rel_servicio_ubicacion (
    id_rel SERIAL PRIMARY KEY,
    id_servicio INTEGER NOT NULL REFERENCES fact_servicio(id_servicio) ON DELETE CASCADE,
    id_ubicacion INTEGER NOT NULL REFERENCES dim_ubicacion(id_ubicacion) ON DELETE RESTRICT,
    
    es_sede_principal BOOLEAN DEFAULT TRUE,

    -- Restricción Única Compuesta: Evita duplicar la misma sede en el mismo servicio
    CONSTRAINT uk_servicio_ubicacion UNIQUE (id_servicio, id_ubicacion)
);

-- Índices
CREATE INDEX idx_servicio_nombre ON fact_servicio(nombre_servicio);