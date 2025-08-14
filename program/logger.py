import colorama
colorama.init()

def log(function: callable):
    """Декоратор логирования вызовов функций"""
    def wrapper(*args):
        print(f"{colorama.Fore.GREEN}-------------------------------------------------------------")
        try:
            print(f"call      {function.__name__} ...")
            function(*args)
            print(f"success   {function.__name__}")
        except Exception as e:
            print(f"{colorama.Fore.RED}error   {function.__name__}: {e}")
        print(f"{colorama.Fore.GREEN}-------------------------------------------------------------\n\n")
            
    return wrapper