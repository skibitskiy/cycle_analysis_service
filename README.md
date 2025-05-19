# Cycle Analysis Service

Микросервис для анализа менструальных циклов.

## Запуск

1. Перейдите в директорию:
   ```bash
   cd cycle_analysis_service
   ```
2. Активируйте виртуальное окружение:
   ```bash
   source venv/bin/activate
   ```
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Убедитесь, что у вас запущен PostgreSQL и создана база данных (по умолчанию: cycle_analysis).
   
   Пример создания базы:
   ```bash
   createdb cycle_analysis
   ```
5. (Опционально) Установите переменную окружения DATABASE_URL, если хотите использовать другой адрес подключения:
   ```bash
   export DATABASE_URL=postgresql://user:password@localhost:5432/cycle_analysis
   ```
6. Запустите сервер:
   ```bash
   uvicorn main:app --reload
   ```

## Эндпоинты

- `POST /users/` — создать пользователя
- `POST /periods/` — добавить событие (начало менструации)
- `GET /statistics/{user_id}` — получить статистику по циклам пользователя

## Пример структуры данных

### User
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "Имя",
  "last_name": "Фамилия",
  "timezone": "Europe/Moscow",
  "send_emails": true,
  "birth_date": "1990-01-01T00:00:00",
  "luteal_phase_length": 14
}
```

### Period
```json
{
  "id": 1,
  "user_id": 1,
  "timestamp": "2024-07-01T00:00:00",
  "first_day": true
}
``` 