import psycopg

conn_str = 'postgresql://postgres.yudvrdhhqwokdptjxeem:inventario.bd@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require'

with psycopg.connect(conn_str) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
        tables = [t[0] for t in cur.fetchall()]
        print(f'TOTAL DE TABLAS EN SUPABASE: {len(tables)}\n')
        for t in tables:
            cur.execute(f'SELECT COUNT(*) FROM "{t}";')
            count = cur.fetchone()[0]
            print(f'  [OK] {t}: {count} registro(s)')
