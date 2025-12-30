# check_connections.py
import os
import sys
import redis
import psycopg2
from sqlalchemy import create_engine

print("=" * 60)
print("VERIFICANDO CONEXIONES DOCKER COMPOSE")
print("=" * 60)

# PostgreSQL
try:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="user",
        password="pass",
        database="devops_copilot"
    )
    conn.close()
    print("✅ PostgreSQL: Conectado")
except Exception as e:
    print(f"❌ PostgreSQL: Error - {e}")

# Redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=1)
    r.ping()
    print("✅ Redis: Conectado")
except Exception as e:
    print(f"❌ Redis: Error - {e}")

print("=" * 60)