import colorama
import json
import os
colorama.init()

class FilePath:
    def __init__(self, path: str):
        self.path = path

        if "\\" in self.path:
            self.path = self.path.replace("\\", "/")

    def back(self):
        self.path = os.path.dirname(self.path)
        return self.path
    
    def enter(self, directory: str):
        self.path += f"/{directory}"
        return self.path

    def __str__(self):
        return self.path

    def __repr__(self):
        return self.path

run_file_directory = FilePath(os.getcwd())
root_folder = run_file_directory.back()

resource = {}

with open("resource.json", "r", encoding="utf-8") as file:
    resource = json.load(file)

if resource == {}:
    print(colorama.Fore.RED + "Ошибка: файл resourse.json пуст")
    exit()

def file_availability(relative_path: str) -> bool:
    """ Проверяет существование файла по относительному пути."""
    full_path = f"{root_folder}/{relative_path}"
    return os.path.isfile(full_path)

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


relatives_paths = get_values_from_json(resource)
error = False

for path in relatives_paths:
    if not file_availability(path):
        print(f"{colorama.Fore.RED}File path not found:  {path}")
        error = True
print(colorama.Fore.WHITE)

if error:
    raise FileNotFoundError
