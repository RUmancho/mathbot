import json
import os

def get_values_from_json(json_data):
    """Функция для получения всех значений из JSON-данных"""
    values = []
    
    if isinstance(json_data, dict):
        for value in json_data.values():
            values.extend(get_values_from_json(value))
    elif isinstance(json_data, list):
        for item in json_data:
            values.extend(get_values_from_json(item))
    else:
        values.append(json_data)
    
    return values

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCE_JSON_PATH_PRIMARY = os.path.join(os.path.dirname(__file__), "resource.json")
RESOURCE_JSON_PATH_FALLBACK = os.path.join(PROJECT_ROOT, "src", "resource.json")

resource = {}

# Попытка прочитать из приоритетного пути, затем из резервного (src/resource.json)
json_path_used = None
try:
    path_to_try = RESOURCE_JSON_PATH_PRIMARY if os.path.exists(RESOURCE_JSON_PATH_PRIMARY) else RESOURCE_JSON_PATH_FALLBACK
    json_path_used = path_to_try
    with open(path_to_try, "r", encoding="utf-8") as file:
        resource = json.load(file)
except FileNotFoundError:
    raise
except json.JSONDecodeError as e:
    raise

if resource == {}:
    exit()


relatives_paths = get_values_from_json(resource)
error = False

# Allow missing database file: it will be created by SQLAlchemy on first use
database_rel_path = resource.get("database")

for path in relatives_paths:
    resolved = os.path.normpath(os.path.join(PROJECT_ROOT, path))
    if not os.path.exists(resolved):
        if path == database_rel_path:
            # Database file will be created automatically; skip error
            continue
        error = True

if error:
    raise FileNotFoundError
