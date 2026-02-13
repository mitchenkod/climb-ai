import logging
import traceback
from sqlmodel import SQLModel, Field

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    # --- Ваши модели ниже ---
    class ExampleModel(SQLModel, table=True):
        id: int = Field(default=None, primary_key=True)
        name: str
    # --- конец моделей ---
except Exception as e:
    logger.error('Ошибка при инициализации моделей SQLModel: %s', e)
    logger.error(traceback.format_exc())
    raise
