import colorama
import json
import os
colorama.init()

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

resource = {}

with open("resource.json", "r", encoding="utf-8") as file:
    resource = json.load(file)

if resource == {}:
    print(colorama.Fore.RED + "Ошибка: файл resourse.json пуст")
    exit()


relatives_paths = get_values_from_json(resource)
error = False

for path in relatives_paths:
    exit_folder = f"../{path}"
    if not os.path.exists(exit_folder):
        print(f"{colorama.Fore.RED}File path not found:  {exit_folder}")
        error = True
print(colorama.Fore.WHITE)

if error:
    raise FileNotFoundError
