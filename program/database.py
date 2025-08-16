from sqlalchemy import create_engine, Column, Integer, String, BLOB, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from config import PASSWORD_LENGTH
import resource

Base = declarative_base()

class Tables:
    class Singly(Base):
        """Таблица заданий и решений"""
        __tablename__ = 'singly_assigment'

        id = Column(Integer, primary_key=True, autoincrement=True)  # первичный ключ
        sender_id = Column(String)         # telegram_id отправителя задания
        recipient_id = Column(String)      # telegram_id получателя задания
        task_filename = Column(String)     # имя файла задания
        task_file = Column(BLOB)           # файл задания
        solution_filename = Column(String) # имя файла решения
        solution_file = Column(BLOB)       # файл решения

    class Users(Base):
        """Таблица зарегестрированных пользователей"""
        __tablename__ = "users"

        telegram_id = Column(String, primary_key=True)  # первичный ключ — telegram_id пользователя
        username = Column(String, nullable=True, unique=True)      # @username пользователя
        password = Column(String(PASSWORD_LENGTH), nullable=False) # пароль пользователя
        name = Column(String, nullable=False)                      # имя пользователя
        surname = Column(String, nullable=False)                   # фамилия пользователя
        role = Column(String, nullable=False)                      # роль пользователя
        my_students = Column(String, nullable=True)                # список прикреплённых учеников
        city = Column(String, nullable=True)                       # город пользователя
        school = Column(Integer, nullable=True)                    # школа пользователя
        grade = Column(String, nullable=True)                      # класс пользователя
        application = Column(String, nullable=True)                # заявки на прикрепление
        my_teachers = Column(String, nullable=True)                # список учителей ученика

relatative_path_database = f"../{resource.resource['database']}"
engine = create_engine(f"sqlite:///{relatative_path_database}")
Base.metadata.create_all(engine)


class Client:
    """Читает/изменяет поля пользователя из БД"""
    CHANGEABLE_ATTRIBUTES = ["name", "surname", "password", "role"]

    def __init__(self, telegram_ID: str):
        self._telegram_id = telegram_ID
        self.username = self._reader("username")
        self.password = self._reader("password")
        self.name = self._reader("name")
        self.surname = self._reader("surname")
        self.role = self._reader("role")

        self.my_students = None
        self.my_teachers = None
        self.application = None
        self.city = None
        self.school = None
        self.grade = None

        if self.role == "учитель":
            self.my_students = self._reader("my_students")

        if self.role == "ученик":
            self.my_teachers = self._reader("my_teachers")
            self.application = self._reader("application")
            self.city = self._reader("city")
            self.school = self._reader("school")
            self.grade = self._reader("grade")

    def _reader(self, column: str):
        search = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._telegram_id, column)
        return search       

    def _redactor(self, column: str, value):
        Manager.update_record(Tables.Users, Tables.Users.telegram_id == self._telegram_id, column, value)

    def __setattr__(self, name: str, value) -> None:
        if name in self.CHANGEABLE_ATTRIBUTES:
            self._redactor(name, value)
        else:
            raise AttributeError(f"attribute {name} is not changeable")

        super().__setattr__(name, value)
        

class Manager:
    session = sessionmaker(bind=engine)

    @staticmethod
    def write(record):
        session = None
        try:
            session = Manager.session()
            session.add(record)
            session.commit()
            return True
        except SQLAlchemyError as e:
            if session and session.is_active:
                session.rollback()
            return False
        except Exception as e:
            if session and session.is_active:
                session.rollback()
            return False
        finally:
            if session:
                session.close()

    @staticmethod
    def update_record(table, filter_column: str, filter_value, update_column: str, new_value):
        session = None
        try:
            session = Manager.session()
            record = session.query(table).filter(getattr(table, filter_column) == filter_value).first()

            if record:
                setattr(record, update_column, new_value)
                session.commit()
                return True
            else:
                return False
        except SQLAlchemyError as e:
            if session and session.is_active:
                session.rollback()
            return False
        finally:
            if session:
                session.close()

    @staticmethod
    def get_cell(table, row_filter, column_name: str):
        try:
            with Manager.session() as session:
                row = session.query(table).filter(row_filter).first()
                if row and hasattr(row, column_name):
                    return getattr(row, column_name)
                return None
        except SQLAlchemyError as e:
            return None

    @staticmethod
    def record_to_dict(record):
        return {column.name: getattr(record, column.name) for column in record.__table__.columns}

    @staticmethod
    def search_records(table, condition, session=None):
        use_external_session = True if session else False 
        try:
            if not use_external_session:  
                session = Manager.session()
            
            records = session.query(table).filter(condition).all()
            return [Manager.record_to_dict(record) for record in records]
        
        except SQLAlchemyError as e:
            return None
        
        finally:
            if session and not use_external_session:
                session.close()

    @staticmethod
    def delete_record(table, column_name: str, value) -> bool:
        try:
            with Manager.session() as session:
                column = getattr(table, column_name)
                record_to_delete = session.query(table).filter(column == value).first()
                
                if record_to_delete:
                    session.delete(record_to_delete)
                    session.commit()
                    return True
                else:
                    return False
        except SQLAlchemyError as e:
            return False
        except Exception as e:
            return False

    @staticmethod
    def get_column(column):
        try:
            with Manager.session() as session:
                return [i[0] for i in session.query(column).all() if i[0] is not None]
        except SQLAlchemyError as e:
            return []