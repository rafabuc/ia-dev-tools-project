# generate_test_ids.py
"""
Generate test UUIDs for testing the API.
"""

import uuid

print("=" * 60)
print("TEST UUIDs PARA LA API")
print("=" * 60)
print()

# Generar algunos UUIDs de prueba
test_ids = [str(uuid.uuid4()) for _ in range(5)]

print("UUIDs de prueba generados:")
for i, test_id in enumerate(test_ids, 1):
    print(f"{i}. {test_id}")

print()
print("Comandos curl de ejemplo:")
print("-" * 40)

# Comandos curl de ejemplo
test_id = test_ids[0]
curl_command = f'''
# 1. Crear un incidente nuevo
curl -X POST "http://localhost:8000/api/workflows/incidents" \\
  -H "Content-Type: application/json" \\
  -d \'{{"title": "API Service Down", "description": "500 errors", "severity": "critical"}}\'

# 2. Usar el incident_id generado para trigger workflow
# Reemplaza {test_id} con el ID real del paso 1
curl -X POST "http://localhost:8000/api/workflows/incident/{test_id}" \\
  -H "Content-Type: application/json" \\
  -d \'{{"title": "API Service Down", "description": "500 errors", "severity": "critical", "log_file_path": "/logs/api.log"}}\'
'''

print(curl_command)