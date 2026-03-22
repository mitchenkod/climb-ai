# Climb AI - Система анализа скалодромов

Climb AI - это проект на базе компьютерного зрения и машинного обучения для автоматического анализа скалодромов, распознавания захватов (holds) и генерации оптимальных маршрутов для лазания.

## Характеристика проекта

**Основная задача:** Распознавание захватов на стене скалодрома и построение маршрутов лазания на основе изображений.

**Ключевые возможности:**
- 🎯 Автоматическое обнаружение захватов с использованием YOLO
- 🛣️ Генерация маршрутов лазания через граф достижимости
- 📊 Анализ и визуализация структуры маршрутов
- 🖼️ Предварительная обработка и постобработка изображений
- 💾 Хранение данных в БД с CRUD операциями
- 🌐 REST API для программного доступа
- 📈 Интерактивный веб-интерфейс на Streamlit

**Используемые технологии:**
- **Backend:** FastAPI, SQLModel, SQLAlchemy
- **Vision:** OpenCV, YOLOv8
- **Frontend:** Streamlit
- **Database:** SQLite (по умолчанию)
- **Infrastructure:** Docker, Docker Compose

---

## Архитектура проекта

### Основные модули

#### 1. **backend/** - Backend приложение
- `main.py` - FastAPI приложение и точка входа
- `config.py` - конфигурация приложения
- `database.py` - инициализация БД

#### 2. **backend/api/** - REST API
- `gym.py` - эндпоинты для управления скалодромами
- `wall.py` - эндпоинты для работы со стенами
- `routes.py` - эндпоинты маршрутов

#### 3. **backend/cv/** - Компьютерное зрение
- `detector.py` - детектор захватов (YOLO)
- `preprocess.py` - предварительная обработка изображений
- `postprocess.py` - постобработка результатов детекции

#### 4. **backend/db/** - Слой данных
- `models.py` - SQLModel модели для БД
- `schemas.py` - Pydantic схемы для API
- `crud.py` - CRUD операции
- `database.py` - инициализация и сессии БД

#### 5. **backend/models/** - Доменные модели
- `gym.py` - модель скалодрома
- `wall.py` - модель стены
- `hold.py` - модель захвата
- `route.py` - модель маршрута
- `graph.py`, `movement_graph.py` - графовые структуры
- `plane.py`, `surface.py` - геометрические модели

#### 6. **backend/routing/** - Генерация маршрутов
- `generator.py` - генератор маршрутов
- `graph.py` - построение графа достижимости
- `reachability.py` - анализ достижимости захватов

#### 7. **backend/services/** - Бизнес-логика
- `climbing/graph_builder.py` - построение графа маршрутов
- `climbing/` - клайминг-специфичная логика

#### 8. **backend/visualization/** - Визуализация
- `overlay.py` - наложение результатов детекции на изображения

#### 9. **frontend/** - Streamlit приложение
- `streamlit_app.py` - интерактивный веб-интерфейс
- `static/` - статические файлы (HTML, JS, CSS)

#### 10. **training/** - Обучение моделей
- `train_yolo.py` - обучение YOLOv8
- `eval_yolo.py` - оценка модели
- `data.yaml` - конфигурация данных для обучения

#### 11. **scripts/** - Утилиты
- `dev_bootsrap.py` - инициализация dev окружения
- `batch_predict.py` - пакетная обработка
- `infer_image.py` - инференс на изображениях
- `visualize_holds.py` - визуализация захватов

#### 12. **data/** - Данные
- `raw/` - сырые данные
- `processed/` - обработанные данные
- `labeled/` - размеченные данные для обучения
- `samples/` - примеры для тестирования

#### 13. **models/yolo/** - Обученные модели
- `trained/` - готовые YOLO модели
- `experiments/` - результаты экспериментов

---

## Установка и запуск

### Требования
- Python 3.9+
- Docker и Docker Compose (опционально)
- pip или conda

### Вариант 1: Локальный запуск

#### 1. Клонирование репозитория
```bash
git clone <repository_url>
cd climb-ai
```

#### 2. Создание виртуального окружения (рекомендуется)
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
python -m venv venv
venv\Scripts\activate  # Windows
```

#### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

#### 4. Инициализация dev окружения
```bash
python scripts/dev_bootsrap.py
```

#### 5. Запуск Backend (FastAPI)
```bash
make run
# или
uvicorn backend.main:app --reload
```

Backend будет доступен по адресу: `http://localhost:8000`
API документация: `http://localhost:8000/docs`

#### 6. Запуск Frontend (Streamlit) - в отдельном терминале
```bash
make streamlit
# или
streamlit run frontend/streamlit_app.py
```

Frontend будет доступен по адресу: `http://localhost:8501`

---

### Вариант 2: Docker запуск

#### 1. Сборка образов
```bash
make docker-build
```

#### 2. Запуск контейнеров
```bash
make docker-run
```

Приложение будет доступно:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:8501`

---

## Основные команды

```bash
# Backend (FastAPI)
make run                 # Запуск с hot-reload

# Frontend (Streamlit)
make streamlit          # Запуск веб-интерфейса

# Docker
make docker-build       # Сборка образов
make docker-run         # Запуск контейнеров

# Утилиты
python scripts/dev_bootsrap.py      # Инициализация окружения
python scripts/infer_image.py       # Инференс на одном изображении
python scripts/batch_predict.py     # Пакетная обработка
python scripts/visualize_holds.py   # Визуализация захватов
```

---

## Workflow использования

### 1. Обучение модели детекции (опционально)
```bash
python training/train_yolo.py      # Обучение YOLO
python training/eval_yolo.py       # Оценка точности
```

### 2. Инференс
```bash
# Обработка одного изображения
python scripts/infer_image.py --image path/to/image.jpg

# Пакетная обработка
python scripts/batch_predict.py --input data/raw --output data/processed
```

### 3. Визуализация результатов
```bash
python scripts/visualize_holds.py --image path/to/image.jpg
```

### 4. Работа через API
```bash
# Загрузить скалодром
curl -X POST http://localhost:8000/api/gyms \
  -H "Content-Type: application/json" \
  -d '{"name": "My Gym"}'

# Загрузить изображение стены
curl -X POST http://localhost:8000/api/walls \
  -F "image=@wall.jpg" \
  -F "gym_id=1"
```

### 5. Использование веб-интерфейса
1. Откройте `http://localhost:8501`
2. Загрузите изображение стены скалодрома
3. Система автоматически обнаружит захваты
4. Просмотрите результаты анализа и визуализацию

---

## Структура БД

Проект использует SQLModel с SQLAlchemy ORM:

- **Gym** - скалодром
- **Wall** - стена скалодрома
- **Hold** - захват (зацепка)
- **Route** - маршрут лазания
- **HoldInRoute** - захват в составе маршрута
- **Movement** (ранее GraphNode) - вершина/движение графа достижимости

---

## Тестирование

```bash
# Запуск тестов
pytest tests/

# С отчетом покрытия
pytest tests/ --cov=backend
```

---

## Документация API

При запущенном backend'е API документация доступна в:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Решение проблем

### Backend не запускается
- Убедитесь, что установлены все зависимости: `pip install -r requirements.txt`
- Проверьте, что порт 8000 не занят
- Запустите инициализацию: `python scripts/dev_bootsrap.py`

### Frontend не отображается
- Проверьте, что Streamlit установлен
- Убедитесь, что порт 8501 не занят
- Перезагрузите страницу браузера

### Проблемы с CUDA/GPU
- Если GPU не доступна, модель автоматически перейдет на CPU
- Проверьте установку CUDA: `python -c "import torch; print(torch.cuda.is_available())"`

---

## Лицензия и контакты

Для вопросов и предложений, пожалуйста, обратитесь к авторам проекта.
