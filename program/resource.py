import colorama
import json
import os
colorama.init()

resource = {}

with open("program/resourse.json", "r", encoding="utf-8") as file:
    resource = json.load(file)

if resource == {}:
    print(colorama.Fore.RED + "Ошибка: файл resourse.json пуст")
    exit()

def get_values_from_json(json_data):
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


paths = get_values_from_json(resource)
error = False

for path in paths:
    if not os.path.exists(path):
        print(f"{colorama.Fore.RED}File path not found:  {path}")
        error = True
print(colorama.Fore.WHITE)

if error:
    raise FileNotFoundError
