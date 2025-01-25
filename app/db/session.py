from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
import logging
import time

from app.core.config import settings

# Настройка логирования
logging.basicConfig()
logger = logging.getLogger("sqlalchemy.engine")
logger.setLevel(logging.INFO)

def log_to_file(msg):
    with open("debug.log", "a") as f:
        f.write(f"{msg}\n")

# Логирование SQL запросов
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())
    log_to_file(f"\nExecuting query: {statement}")
    log_to_file(f"Parameters: {parameters}")

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    log_to_file(f"Query complete in {total:.3f} seconds\n")

# Создание движка с подробным логированием
engine = create_engine(
    settings.DATABASE_URL,
    echo=True,  # Включаем вывод SQL
    pool_pre_ping=True  # Проверка соединения перед использованием
)

# Проверяем подключение к БД
try:
    connection = engine.connect()
    log_to_file("\n=== Database connection successful ===\n")
    connection.close()
except Exception as e:
    log_to_file(f"\n=== Database connection failed: {str(e)} ===\n")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)