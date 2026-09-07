import os
import psycopg
import environ

env = environ.Env()
environ.Env.read_env(os.path.join(os.path.dirname(__file__), '.env'))

conn_str = env('DATABASE_URL', default=None)

if not conn_str:
    print('DATABASE_URL no configurada en .env')
    exit(1)

with psycopg.connect(conn_str) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
        tables = [t[0] for t in cur.fetchall()]
        print(f'TOTAL DE TABLAS EN SUPABASE: {len(tables)}\n')
        for t in tables:
            cur.execute(f'SELECT COUNT(*) FROM "{t}";')
            count = cur.fetchone()[0]
            print(f'  [OK] {t}: {count} registro(s)')
