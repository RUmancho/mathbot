from database import *
import colorama
import telebot
import config
colorama.init()

class UserInputError(Exception):
    """Вызывается при некорректно введённых данных"""


class UserRecognizer:
    def __init__(self, ID: str):
        self._ID = ID
        self.name = self._reader("name")
        self.surname = self._reader("surname")
        self.password = self._reader("password")
        self.role = self._reader("role")

        if self.role == "ученик":
            self.city = self._reader("city")
            self.school = self._reader("school")
            self.class_number = self._reader("school_number")

    def get_ID(self):
        return self._ID

    def _reader(self, column: str):
        search = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._ID, column)
        return search


class Process:
    CANCEL_KEYWORD = "отмена"
    _bot = telebot.TeleBot(config.BOT_TOKEN)

    def __init__(self, ID, cancelable = True):
        self._me = UserRecognizer(ID)
        self._chain = []
        self._max_i = len(self._chain) - 1
        self._i = 0
        self._is_active = False
        self._cancelable = cancelable

        self._current_request = ""

    def update_last_request(self, request):
        self._current_request = request

        if self._cancelable:
            if self._current_request == self.CANCEL_KEYWORD:
                self.stop()

    def stop(self):
        self._i = 0
        self._is_active = False

    def execute(self):
        try:
            # помечаем процесс как активный на время выполнения шага
            self._is_active = True
            self._chain[self._i]()
            if self._i < self._max_i:
                self._i += 1 
            else:
                self.stop()
        except UserInputError as e:
            print(f"Пользователь {self._me.name} неверно ввёл запрошенные данные")


class FileSender:
    IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "webp"]
    DOCUMENT_EXTENSIONS = ["doc", "docx", "pdf", "xlsx", "xls", "ppt", "pptx", "txt"]
    AUDIO_EXTENSIONS = ["mp3", "wav", "ogg", "m4a", "aac", "flac"]
    VIDEO_EXTENSIONS = ["mp4", "avi", "mkv", "mov", "wmv", "flv", "webm"]

    unzipped_text_document = True # позволить боту отправить сразу текст из файла
    bot = telebot.TeleBot(config.BOT_TOKEN)
    chat_id = None

    def __init__(self, keyboard=None, *args):
        self.keyboard = keyboard

        self.file_handlers = {}

        for path in args:
            extension = file_extension(path)
            if extension in self.IMAGE_EXTENSIONS:
                self.file_handlers[path] = self.__push_image
            elif extension in self.DOCUMENT_EXTENSIONS:
                if not self.unzipped_text_document:
                    self.file_handlers[path] = self.__push_document
                else:
                    self.file_handlers[path] = self.__push_unzipped_text_document
            elif extension in self.AUDIO_EXTENSIONS:
                self.file_handlers[path] = self.__push_audio
            elif extension in self.VIDEO_EXTENSIONS:
                self.file_handlers[path] = self.__push_video

    @classmethod
    def set_chat_id(cls, chat_id):
        cls.chat_id = chat_id

    def push(self):
        sent = 0
        required_to_send = len(self.file_handlers.keys())
        for path in self.file_handlers.keys():
            sent += 1
            if sent == required_to_send:
                self.file_handlers[path](path, keyboard = None)
            else:
                self.file_handlers[path](path, keyboard = self.keyboard)

    def __push_image(self, path: str, keyboard = None, caption: str = None):
        with open(path, 'rb') as file:
            self.bot.send_photo(self.chat_id, file, reply_markup = keyboard, caption=caption)

    def __push_document(self, path: str, keyboard = None, caption: str = None):
        with open(path, 'rb') as file:
            self.bot.send_document(self.chat_id, file, reply_markup = keyboard, caption=caption)

    def __push_audio(self, path: str, keyboard = None, caption: str = None):
        with open(path, 'rb') as file:
            self.bot.send_audio(self.chat_id, file, reply_markup = keyboard, caption=caption)

    def __push_video(self, path: str, keyboard = None, caption: str = None):
        with open(path, 'rb') as file:
            self.bot.send_video(self.chat_id, file, reply_markup = keyboard, caption=caption)

    def __push_unzipped_text_document(self, path: str, keyboard = None, caption: str = None):
        with open(path, 'r', encoding='utf-8') as file:
            text = file.read()

            if caption is not None:
                caption = f"\n{caption}\"\n"
            self.bot.send_message(self.chat_id, f"{caption}\n{text}", reply_markup = keyboard)


## Удалён класс Sender — ввод реализуется через core.Process


class Validator:
    RU_ALPHABET = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    RU_CLASS_PARALLEL = "абвг"
    DECIMAL_DIGITS = "0123456789"

    @staticmethod
    def name(string: str, alphabet: str = RU_ALPHABET):
        try:
            string = string.lower()
            for char in string:
                if char not in alphabet:
                    return False
            return True
        except Exception as e:
            print(f"Ошибка при валидации имени: {e}")
            return False
    
    @classmethod
    def surname(cls, string: str, lang: str = RU_ALPHABET):
        return cls.name(string, lang)

    @staticmethod
    def city(string: str, lang: str = RU_ALPHABET):
        try:
            string = string.lower()
            return all(char in lang or char == " " for char in string)
        except Exception as e:
            print(f"Ошибка при валидации города: {e}")
            return False

    @staticmethod
    def class_number(number: str, parallel: str = RU_CLASS_PARALLEL):
        try:
            class_num = int(number[:-1])
            letter = number[-1].lower()
            return 1 <= class_num <= 11 and letter in parallel
        except (ValueError, IndexError) as e:
            print(f"Ошибка при валидации номера класса: {e}")
            return False

    @staticmethod
    def school(number: str):
        try:
            extract = number.split(" ")[-1]
            return int(extract) > 0
        except (ValueError, IndexError) as e:
            print(f"Ошибка при валидации номера школы: {e}")
            return False

    @classmethod
    def create_password(cls, string: str, max_len: int = config.PASSWORD_LENGTH):
        try:
            if len(string) != max_len:
                return False
            return all(numeral in cls.DECIMAL_DIGITS for numeral in string)
        except Exception as e:
            print(f"Ошибка при валидации пароля: {e}")
            return False


class FuncChain:
    def __init__(self, *args):
        try:
            self.logic = args
            self.null()
        except Exception as e:
            print(f"Ошибка при инициализации FuncChain: {e}")

    def next(self):
        try:
            if self.i == len(self.logic):
                self.isActive = False
                self.completion = True

            if self.isActive:
                success = self.logic[self.i]()

                if success:
                    self.i += 1
        except Exception as e:
            print(f"Ошибка в next FuncChain: {e}")
            
    def activate(self):
        try:
            self.null()
            self.isActive = True
        except Exception as e:
            print(f"Ошибка при активации FuncChain: {e}")

    def null(self):
        try:
            self.completion = False
            self.isActive = False
            self.i = 0
        except Exception as e:
            print(f"Ошибка при сбросе FuncChain: {e}")

class Button:
    def __init__(self, *args: callable):
        try:
            self.subsequence = FuncChain(*args)
        except Exception as e:
            print(f"Ошибка при создании Button: {e}")
    
    def exe(self):
        try:
            if not self.subsequence.isActive:
                self.subsequence.activate()

            self.subsequence.next()
        except Exception as e:
            print(f"Ошибка при выполнении Button: {e}")

def cancelable(function: callable):
    """Декоратор, позволяющий отменить текущее действие словом «отмена».

    Поведение:
    - Если последний ввод пользователя равен ключевому слову отмены
      (`Process.CANCEL_KEYWORD` → «отмена»), декоратор пытается корректно
      завершить активный процесс и очищает отложенную команду.
    - Поддерживаются типовые сценарии:
        • регистрация (`current_registration`: ButtonCollector),
        • удаление профиля (`delete_profile_process`: Process),
        • поиск класса у учителя (`searchClass`: ButtonCollector),
        • а также очистка `_current_command`.
    - Пользователю отправляется уведомление «Действие отменено».
    """

    def wrapper(self, *args, **kwargs):
        try:
            last_request = getattr(self, "_current_request", None)
            cancel_word = getattr(Process, "CANCEL_KEYWORD", "отмена")
            if isinstance(last_request, str) and last_request == cancel_word:
                # Пользователь инициировал отмену
                # Специальный хук отмены, если реализован
                if hasattr(self, "cancel_current_action") and callable(self.cancel_current_action):
                    try:
                        self.cancel_current_action()
                    except Exception:
                        pass

                # Попытка отменить типовые процессы
                # 1) Регистрация через ButtonCollector
                reg = getattr(self, "current_registration", None)
                if reg is not None and not getattr(reg, "registration_finished", True):
                    try:
                        reg.clear()
                    except Exception:
                        pass
                    try:
                        setattr(self, "current_registration", None)
                    except Exception:
                        pass

                # 2) Удаление профиля (Process)
                delete_proc = getattr(self, "delete_profile_process", None)
                if isinstance(delete_proc, Process):
                    try:
                        delete_proc.stop()
                    except Exception:
                        pass

                # 3) Поиск класса (ButtonCollector)
                search = getattr(self, "searchClass", None)
                if search is not None and not getattr(search, "registration_finished", True):
                    try:
                        search.clear()
                    except Exception:
                        pass
                    try:
                        setattr(self, "searchClass", [])
                    except Exception:
                        pass

                # Очистка отложенной команды
                if hasattr(self, "_current_command"):
                    try:
                        self._current_command = None
                    except Exception:
                        pass

                # Уведомление пользователя
                try:
                    bot = getattr(self, "_telegramBot", None)
                    chat_id = getattr(self, "_ID", None)
                    if bot and chat_id:
                        bot.send_message(chat_id, "Действие отменено")
                except Exception:
                    pass
                return True

            # Нет команды отмены — выполняем оригинальную функцию
            return function(self, *args, **kwargs)
        except Exception:
            # В случае ошибки не блокируем дальнейшее выполнение
            return function(self, *args, **kwargs)

    return wrapper

def log(function: callable):
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

def extractor(collection: list[dict], key) -> list:
    try:
        extractValues = []

        for dictonary in collection:
            find = dictonary.get(key)
            extractValues.append(find)
        
        return extractValues
    except Exception as e:
        print(f"Ошибка в extractor: {e}")
        return []

def file_extension(path: str) -> str:
    """Определяет расширение файла"""
    return path.split(".")[-1]

def transform_request(request: str):
    """переводит регистр строки в нижний, а также заменяет букву "ё" на "е" """
    request = request.lower().strip()
    if "ё" in request:
        request = request.replace("ё", "е")
    return request