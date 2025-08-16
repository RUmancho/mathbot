import colorama
colorama.init()

def log(function: callable):
    """Декоратор логирования вызовов функций"""
    def wrapper(*args, **kwargs):
        print(f"{colorama.Fore.GREEN}-------------------------------------------------------------")
        try:
            print(f"call      {function.__name__} ...")
            result = function(*args, **kwargs)
            print(f"success   {function.__name__}")
            return result
        except Exception as e:
            print(f"{colorama.Fore.RED}error   {function.__name__}: {e}")
        finally:
            print(f"{colorama.Fore.GREEN}-------------------------------------------------------------\n\n")
    return wrapper