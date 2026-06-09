import psycopg2
conn = psycopg2.connect('postgresql://postgres.aifsfrslffnzfufodqwx:47OLPjn1vxbkbL6k@aws-1-us-west-2.pooler.supabase.com:5432/postgres')
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'compras';")
for row in cur.fetchall(): print(row)
