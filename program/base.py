import database
import core
import keyboards

class User:
    RUN_BOT_COMMADS = ["/start"]
    SHOW_MAIN_MENU = ["/меню", "/главная", "/menu", "/main", "/home"]

    # Базовый класс больше не используется в упрощённой архитектуре,
    # оставлен для совместимости с частями кода (теория, FileSender и т.п.).
    def __init__(self, ID: str, bind_bot = None):
        self.info = database.Client(ID)
        self._ID = ID
        self._telegramBot = bind_bot

    def get_ID(self) -> str:
        return self._ID

    def out(self, text: str, markup=None):
        self._telegramBot.send_message(self._ID, text=text, reply_markup=markup)

    def update_last_request(self, request: str):
        """Синхронизирует последний ввод как на агрегаторе, так и на роли."""
        self._current_request = request
        # Пробуем синхронизировать ввод и на вложенном экземпляре роли
        try:
            setattr(self.instance, "_current_request", request)
        except Exception:
            pass
        # Если у роли есть собственный обработчик, делегируем ему
        try:
            self.instance.update_last_request(request)
        except Exception:
            pass

    def command_executor(self):
        """Выполняет отложенную команду роли, если она есть."""
        instance_exec = getattr(self.instance.__class__, "command_executor", None)
        base_exec = getattr(User, "command_executor")
        if callable(instance_exec) and instance_exec is not base_exec:
            return self.instance.command_executor()
        func = getattr(self.instance, "_current_command", None)
        if callable(func):
            return func()

    # Публичный способ проверки наличия отложенной команды
    def has_pending_command(self) -> bool:
        return bool(getattr(self.instance, "_current_command", None))

    @property
    def current_command(self):
        return self._current_command

    @current_command.setter
    def current_command(self, func):
        self._current_command = func


class Registered(User):
    """Базовый класс для роли зарегистрированного пользователя.

    Загружает профиль пользователя, обновляет `ref` и предоставляет процесс
    удаления профиля с подтверждением паролем.
    """
    class DeleteProfile(core.Process):
        """Многошаговый процесс удаления профиля с валидацией пароля."""
        def __init__(self, ID, cancelable: bool = True):
            super().__init__(ID, cancelable)
            self._chain = [self.ask_for_password, self.password_entry_verification]
            self._max_i = len(self._chain) - 1

        def ask_for_password(self):
            """Запрашивает пароль у пользователя."""
            self.out("Введите ваш пароль для удаления профиля")

        def password_entry_verification(self):
            """Проверяет введённый пароль и удаляет профиль при успешном вводе."""
            if self._current_request == self._info.password:
                try:
                    deleted = database.Manager.delete_record(database.Tables.Users, "telegram_id", self._info.get_ID())
                    if deleted:
                        self.out("Профиль удалён", keyboards.Guest.main)
                    else:
                        self.out("Не удалось удалить профиль. Попробуйте позже")
                        self.stop()
                except Exception:
                    self.out("Произошла ошибка при удалении профиля")
                    self.stop()
            else:
                self.out("Неверный пароль, повторите попытку")
                raise core.UserInputError("password entry error")

    def __init__(self, ID: str = "", telegramBot=None):
        super().__init__(ID, telegramBot)
        self.delete_profile_process = self.DeleteProfile(ID)

    def delete_account(self):
        """Запускает удаление профиля с поддержкой отмены (слово «отмена»)."""
        self._current_command = self._cancelable_delete
        # Немедленно показать первый шаг (запрос пароля), чтобы пользователь видел, что процесс начался
        try:
            self._current_command()
        except Exception:
            pass

    @staticmethod
    def _noop(*_, **__):
        return None

    def _cancelable_delete(self):
        """Шаг удаления профиля: выполняет процесс и корректно завершает его."""
        try:
            # отмена обрабатывается внутри Process.update_last_request
            self.delete_profile_process.update_last_request(self._current_request)
            self.delete_profile_process.execute()
            if not getattr(self.delete_profile_process, "_is_active", False):
                self._current_command = None
                try:
                    self.delete_profile_process = self.DeleteProfile(self._ID)
                except Exception:
                    pass
            return True
        except Exception:
            return False

    # Реализация универсальных хуков для зарегистрированных ролей
    def has_active_process(self) -> bool:
        try:
            return bool(getattr(self.delete_profile_process, "_is_active", False))
        except Exception:
            return False

    def handle_active_process(self) -> bool:
        try:
            return bool(self._cancelable_delete())
        except Exception:
            return False
