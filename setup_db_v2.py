import psycopg2
import os

DB_URL = "postgresql://postgres.aifsfrslffnzfufodqwx:47OLPjn1vxbkbL6k@aws-1-us-west-2.pooler.supabase.com:5432/postgres"

def run_setup():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    cur.execute("""
        DROP TABLE IF EXISTS public.detalle_facturas CASCADE;
        DROP TABLE IF EXISTS public.facturas CASCADE;
        
        ALTER TABLE public.compras 
        ADD COLUMN IF NOT EXISTS clave_acceso_sri VARCHAR(255),
        ADD COLUMN IF NOT EXISTS estado_factura VARCHAR(50);
    """)
    conn.commit()
    print("Database updated for new architecture")
    cur.close()
    conn.close()

if __name__ == "__main__":
    run_setup()
