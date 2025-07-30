from database import *
import colorama
import telebot
import config
colorama.init()

class Resource:
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


class Sender:
    def __init__(self, key, out):
        self.key = key
        self.out = out

    def __str__(self):
        return self.out
    
    def __repr__(self):
        return self.out


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


class Collector:
    def __init__(self, questionnaire: dict[Sender, callable]):
        self.questionnaire = questionnaire
        self.last_question = ""
        self.clear()

    def __iter__(self):
        return self

    def __next__(self):
        try:
            self.last_question = self.data_input()
            return self.last_question
        except Exception as e:
            print(f"Ошибка в __next__: {e}")
            raise StopIteration

    def data_input(self):
        try:
            print(f"data_input: null={self.null}, start={self.start}, finish={self.finish}")
            if not self.null and self.start < self.finish:
                question = self.questions[self.start]
                print(f"Возвращаем вопрос: {question.out}")
                return question
            print("Условия не выполнены, вызываем StopIteration")
            raise StopIteration
        except Exception as e:
            print(f"Ошибка в data_input: {e}")
            raise StopIteration

    def reply(self, entry: str):
        try:
            self.entry = entry
            print(f"reply: start={self.start}, finish={self.finish}")
            if self.start < self.finish:
                question = self.questions[self.start]
                validator = self.questionnaire[question]
                
                if validator is None or validator(entry):
                    self.response[question.key] = entry
                    self.start += 1
                    print(f"Вопрос обработан, новый start={self.start}")
                    if self.start == self.finish:
                        self.null = True
                        print("Все вопросы обработаны, устанавливаем null = True")
                    return True
                return False
            self.null = True
            return True
        except Exception as e:
            print(f"Ошибка в reply: {e}")
            return False

    def collection(self):
        try:
            return self.response
        except Exception as e:
            print(f"Ошибка при получении коллекции: {e}")
            return {}

    def clear(self) -> None:
        """Reset the collector state."""
        self.questions = list(self.questionnaire.keys())
        self.finish = len(self.questions)
        self.start = 0
        self.null = False
        self.response = {}
        self.entry = None


class ButtonCollector(Collector):
    bot = None
    
    @staticmethod
    def set_bot(bot_instance):
        """Устанавливает экземпляр бота для всех ButtonCollector"""
        ButtonCollector.bot = bot_instance
    
    @staticmethod
    def out(text, tgId, endKeyboard = None):
        try:
            if ButtonCollector.bot:
                ButtonCollector.bot.send_message(tgId, text, reply_markup = endKeyboard)
        except Exception as e:
            print(f"Ошибка при отправке сообщения: {e}")

    def __init__(self, collect, endMessage: str, endKeyboard = None):
        super().__init__(collect)   
        self.firstMessageSent = False
        self.endMessage = endMessage
        self.endKeyboard = endKeyboard
        self.currentRequest: str = ""
        self.ID: str = ""
        self.registration_finished = False

    def request(self, last: str):
        self.currentRequest = last

    def set_ID(self, ID):
        self.ID = ID

    def run(self):
        try:
            if not self.firstMessageSent:
                self.firstMessageSent = True
                self.__main()
                return
            
            if self.currentRequest:
                self.data_input()
                self.currentRequest = ""
        except Exception as e:
            print(f"Ошибка в run: {e}")

    def data_input(self):
        try:
            if self.firstMessageSent and self.currentRequest:
                if self.reply(self.currentRequest):
                    self.__main()
                else:
                    try:
                        current_question = super().data_input()
                        ButtonCollector.out(f"Некорректный ввод. Попробуйте еще раз.\n{current_question.out}", self.ID)
                    except StopIteration:
                        pass
            
            return self.registration_finished
        except Exception as e:
            return self.registration_finished
    
    def __main(self):
        try:
            if not self.null:
                try:
                    current_question = super().data_input()
                    ButtonCollector.out(current_question.out, self.ID)
                except StopIteration:
                    if self.endMessage:
                        ButtonCollector.out(self.endMessage, self.ID, self.endKeyboard)
                    self.firstMessageSent = False
                    self.registration_finished = True
            else:
                if self.endMessage:
                    ButtonCollector.out(self.endMessage, self.ID, self.endKeyboard)
                self.firstMessageSent = False
                self.registration_finished = True
        except Exception as e:
            print(f"Ошибка в __main: {e}")
    
    def collection(self, clearing: bool = False):
        try:
            if clearing:
                self.clear()
                self.registration_finished = False
            save = super().collection()
            return save
        except Exception as e:
           return {}


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