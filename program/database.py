from sqlalchemy import create_engine, Column, Integer, String, BLOB
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from config import PASSWORD_LENGTH
import resource

Base = declarative_base()

class Tables:
    class Singly(Base):
        __tablename__ = 'singly_assigment'

        id = Column(Integer, primary_key=True, nullable=False)
        teacher_id = Column(String)
        task_filename = Column(String)
        task_file = Column(BLOB)
        student_id = Column(String)
        solution_filename = Column(String)
        solution_file = Column(BLOB)

    class GroupSolution(Base):
        __tablename__ = "group_solution"

        id = Column(Integer, primary_key=True, nullable=False)
        student_id = Column(String)
        task_filename = Column(String)
        solution_file = Column(BLOB)
        solution_filename = Column(String)
        teacher_id = Column(String)

    class GroupAssignment(Base):
        __tablename__ = "group_assignment"

        id = Column(Integer, primary_key=True, nullable=False)
        teacher_id = Column(String)
        file = Column(BLOB)
        filename = Column(String)
        students_ids = Column(String)
        city = Column(String)
        school = Column(Integer)
        selected_class = Column(String)

    class Users(Base):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True, nullable=False)
        telegram_id = Column(String)
        password = Column(String(PASSWORD_LENGTH))
        name = Column(String)
        surname = Column(String)
        role = Column(String)
        attached_students = Column(String)
        city = Column(String)
        school = Column(Integer)
        student_class = Column(String)
        application = Column(String)
        ref = Column(String)
        my_teachers = Column(String)

relatative_path_database = f"../{resource.resource['database']}"
engine = create_engine(f"sqlite:///{relatative_path_database}")
Base.metadata.create_all(engine)

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