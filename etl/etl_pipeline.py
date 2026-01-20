import pandas as pd
import os
from sqlalchemy import create_engine, text
import time

# --- CONFIGURACIÓN ---
DB_USER = os.getenv('DB_USER', 'admin_datos')
DB_PASS = os.getenv('DB_PASS', 'cali_segura_2025')
DB_HOST = os.getenv('DB_HOST', 'localhost') # 'db' si corre en docker
DB_NAME = os.getenv('DB_NAME', 'catalogo_cali')
INPUT_FILE = '/app/data/input/matriz_servicios_consolidada.xlsx'

# String de conexión
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

# Mapeos (Simulados, idealmente vendrían de la BD)
MAP_DOMINIO = {
    'DATIC': 1, 
    'Secretaría de Cultura': 2, 
    'Secretaría de Vivienda Social y Hábitat': 3, 
    'Secretaría del Deporte y la Recreación': 4
}

def clean_text(text):
    if pd.isna(text) or str(text).lower() in ['nan', 'no registra', 'sin definir']:
        return None
    return str(text).strip()

def run_etl():
    print("⏳ Esperando conexión a base de datos...")
    time.sleep(5) 
    
    try:
        engine = create_engine(DATABASE_URL)
        conn = engine.connect()
        print("✅ Conexión exitosa a PostgreSQL")
    except Exception as e:
        print(f"❌ Error conectando a BD: {e}")
        return

    print(f"🚀 Iniciando procesamiento de: {INPUT_FILE}")
    
    try:
        df = pd.read_excel(INPUT_FILE, sheet_name='Hoja1')
    except FileNotFoundError:
        print(f"❌ No se encontró el archivo en {INPUT_FILE}. Verifica que la carpeta 'data/input' esté montada.")
        return

    # --- TRANSFORMACIÓN ---
    
    # 1. Servicios
    df['codigo_servicio'] = df.apply(lambda x: f"SERV-{str(x['N°']).zfill(3)}", axis=1)
    
    fact_data = []
    rel_req_data = []
    dim_req_unique = set()

    for idx, row in df.iterrows():
        # Preparamos Fact Service
        fact_data.append({
            'codigo_servicio': row.apply(lambda x: f"SERV-{str(x['N°']).zfill(3)}", axis=1) if 'codigo_servicio' not in df else row['codigo_servicio'],
            'id_dominio': MAP_DOMINIO.get(row['Organismo'], 1), # Default DATIC
            'id_estado': 3, # Activo
            'nombre_servicio': row['Nombre del Servicio'],
            'descripcion': clean_text(row['Descripción del Servicio']),
            'proposito': clean_text(row['Propósito del producto']),
            'dirigido_a': clean_text(row['A quién va dirigido']),
            'tiempo_respuesta': clean_text(row['Tiempo de Obtención']),
            'fundamento_legal': clean_text(row['Fundamento Legal o Procedimental']),
            'informacion_costo': clean_text(row['Información sobre Costos']),
            'volumen_mensual_promedio': pd.to_numeric(row['Promedio de solicitudes que se generan por mes'], errors='coerce') or 0
        })

        # Preparamos Requisitos
        raw_reqs = str(row.get('Requisitos (Normalizado)', ''))
        if clean_text(raw_reqs):
            codes = [x.strip() for x in raw_reqs.replace(',', ';').split(';') if x.strip()]
            for code in codes:
                # Datos para la tabla intermedia
                rel_req_data.append({
                    'codigo_servicio_temp': row['codigo_servicio'], # Usaremos esto para buscar el ID luego
                    'id_requisito': code,
                    'es_obligatorio': True
                })
                dim_req_unique.add(code)

    df_fact = pd.DataFrame(fact_data)
    df_dim_req = pd.DataFrame([{'id_requisito': r, 'nombre_requisito': f'Requisito {r}', 'tipo_soporte': 'Digital'} for r in dim_req_unique])

    # --- CARGA (LOAD) ---
    
    # Nota: Usamos 'append' pero en producción idealmente validamos existencia (Upsert)
    print("💾 Cargando DIM_REQUISITO...")
    try:
        # Insertar ignorando duplicados (requiere soporte específico o limpieza previa)
        # Para el piloto, usamos to_sql con if_exists='append' y manejo de errores simple
        for _, r in df_dim_req.iterrows():
            try:
                pd.DataFrame([r]).to_sql('dim_requisito', engine, schema='catalogo', if_exists='append', index=False)
            except:
                pass # Ya existe
    except Exception as e:
        print(f"⚠️ Alerta en carga requisitos: {e}")

    print("💾 Cargando FACT_SERVICIO...")
    try:
        # Limpiamos tabla para evitar duplicados en re-runs del piloto
        conn.execute(text("TRUNCATE TABLE catalogo.rel_servicio_requisito, catalogo.fact_servicio CASCADE"))
        conn.commit()
        
        df_fact.to_sql('fact_servicio', engine, schema='catalogo', if_exists='append', index=False)
        print("   -> Servicios cargados.")
    except Exception as e:
        print(f"❌ Error cargando servicios: {e}")

    print("💾 Cargando RELACIONES...")
    # Necesitamos recuperar los IDs autogenerados de fact_servicio
    df_services_db = pd.read_sql("SELECT id_servicio, codigo_servicio FROM catalogo.fact_servicio", engine)
    
    # Cruzamos el ID real de base de datos con nuestros datos de requisitos
    df_rel_req = pd.DataFrame(rel_req_data)
    df_merged = pd.merge(df_rel_req, df_services_db, left_on='codigo_servicio_temp', right_on='codigo_servicio', how='inner')
    
    final_rel = df_merged[['id_servicio', 'id_requisito', 'es_obligatorio']]
    
    try:
        final_rel.to_sql('rel_servicio_requisito', engine, schema='catalogo', if_exists='append', index=False)
        print("   -> Relaciones cargadas.")
    except Exception as e:
        print(f"❌ Error cargando relaciones: {e}")

    conn.close()
    print("✅ ¡PROCESO FINALIZADO CON ÉXITO!")

if __name__ == "__main__":
    run_etl()