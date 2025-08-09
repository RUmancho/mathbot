"""Базовые классы и вспомогательные сущности для пользователей."""

from database import Manager, Tables
import core


def find_my_role(ID: str):
    return Manager.get_cell(Tables.Users, Tables.Users.telegram_id == ID, "role")


class User:
    RUN_BOT_COMMADS = ["/start"]
    SHOW_MAIN_MENU = ["/меню", "/главная", "/menu", "/main", "/home"]

    def __init__(self, ID: str, bind_bot = None):
        self.info = core.UserRecognizer(ID)
        self._ID = ID
        self._telegramBot = bind_bot
        self._current_request = None
        self._current_command = None
        self._role_changed = False
        self.instance = None

    def set_role(self, user_class, ID: str):
        needs_new_instance = (
            self.instance is None
            or not isinstance(self.instance, user_class)
            or self.instance.get_ID() != ID
        )
        if needs_new_instance:
            self.instance = user_class(ID, self._telegramBot)
            self._role_changed = True
        else:
            self.instance._telegramBot = self._telegramBot
            self.instance.set_ID(ID)
            self._role_changed = False
        return self.instance

    def get_user(self):
        return self.instance

    def reset_role_change_flag(self):
        self._role_changed = False

    def get_ID(self) -> str:
        return self._ID

    def set_ID(self, ID: str):
        if type(ID) != str:
            raise TypeError("ID is not str")
        self._ID = ID

    def text_out(self, text: str, markup=None):
        self._telegramBot.send_message(self._ID, text=text, reply_markup=markup)

    def unsupported_command_warning(self):
        self.text_out("Неизвестная команда")

    def update_last_request(self, request: str):
        self._current_request = request
        try:
            self.instance.update_last_request(request)
        except Exception:
            pass

    def command_executor(self):
        instance_exec = getattr(self.instance.__class__, "command_executor", None)
        base_exec = getattr(User, "command_executor")
        if callable(instance_exec) and instance_exec is not base_exec:
            return self.instance.command_executor()
        func = getattr(self.instance, "_current_command", None)
        if callable(func):
            return func()

    @property
    def current_command(self):
        return self._current_command

    @current_command.setter
    def current_command(self, func):
        self._current_command = func


class Registered(User):
    class DeleteProfile(core.Process):
        def __init__(self, ID, cancelable: bool = True):
            super().__init__(ID, cancelable)
            self._chain = [self.ask_for_password, self.password_entry_verification]

        def ask_for_password(self):
            self._bot.send_message(self._me.get_ID(), "Введите ваш пароль для удаления профиля")

        def password_entry_verification(self):
            if self._current_request == self._me.password:
                self._bot.send_message(self._me.get_ID(), "Профиль удалён")
                Manager.delete_record(Tables.Users, "telegram_id", self._me.get_ID())
            else:
                self._bot.send_message(self._me.get_ID(), "Неверный пароль, повторите попытку")
                raise core.UserInputError("password entry error")

    def __init__(self, ID: str = "", telegramBot=None):
        super().__init__(ID, telegramBot)
        self.name = None
        self.surname = None
        self.password = None
        self.role = None
        self.recognize_user()
        try:
            Manager.update_record(Tables.Users, "telegram_id", self._ID, "ref", f"tg://user?id={self._ID}")
        except Exception:
            pass
        self.delete_profile_process = self.DeleteProfile(ID)

    def delete_account(self):
        """Запускает удаление профиля с поддержкой отмены."""
        self._current_command = self._cancelable_delete

    @staticmethod
    def _noop(*_, **__):
        return None

    @core.cancelable
    def _cancelable_delete(self):
        """Шаг выполнения удаления профиля с корректным завершением процесса."""
        try:
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

    def recognize_user(self):
        self.name = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._ID, "name")
        self.surname = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._ID, "surname")
        self.password = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._ID, "password")
        self.role = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._ID, "role")

    def _reader_my_data(self, column: str):
        return Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._ID, column)


