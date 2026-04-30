# FastAPI S3 File Service

REST API для работы с файлами в S3-совместимом хранилище (AWS S3, MinIO, DigitalOcean Spaces, Cloudflare R2 и др.).

---

## Возможности

- Загрузка файлов (приватная и публичная)
- Потоковое скачивание файлов
- Удаление файлов
- Генерация presigned URL для скачивания

---

## Архитектура

```text
Client → FastAPI → boto3 → S3 Storage
```

Backend выступает как proxy и генератор presigned URL.

---

## Авторизация

Каждый запрос требует S3 credentials через заголовки:

| Header            | Описание                         |
| ----------------- | -------------------------------- |
| `x-s3-access-key` | Access Key                       |
| `x-s3-secret-key` | Secret Key                       |
| `x-s3-endpoint`   | S3 endpoint (AWS / MinIO / etc.) |
| `x-s3-bucket`     | Bucket name                      |
| `x-s3-region`     | Region (опционально)             |

---

## Эндпоинты

### POST /files/upload

Загружает файл в S3. При передаче параметра `?public=true` файл загружается с ACL `public-read` и возвращается публичный URL.

**Request**

- `multipart/form-data`
- `file` — загружаемый файл (обязательно)

**Query параметры**

| Параметр | Тип  | По умолчанию | Описание                     |
| -------- | ---- | ------------ | ---------------------------- |
| `public` | bool | `false`      | Сделать файл публично доступным |

**Пример — приватная загрузка**

```bash
curl -X POST "http://localhost:8000/files/upload" \
  -H "x-s3-access-key: ACCESS" \
  -H "x-s3-secret-key: SECRET" \
  -H "x-s3-endpoint: http://localhost:9000" \
  -H "x-s3-bucket: my-bucket" \
  -F "file=@image.png"
```

**Response**

```json
{
  "success": true,
  "bucket": "my-bucket",
  "key": "cjld2cjxh0000qzrmn831i7rn.png"
}
```

**Пример — публичная загрузка**

```bash
curl -X POST "http://localhost:8000/files/upload?public=true" \
  -H "x-s3-access-key: ACCESS" \
  -H "x-s3-secret-key: SECRET" \
  -H "x-s3-endpoint: http://localhost:9000" \
  -H "x-s3-bucket: my-bucket" \
  -F "file=@image.png"
```

**Response**

```json
{
  "success": true,
  "bucket": "my-bucket",
  "key": "cjld2cjxh0000qzrmn831i7rn.png",
  "public_url": "http://localhost:9000/my-bucket/cjld2cjxh0000qzrmn831i7rn.png"
}
```

---

### GET /files/{key}

Стримит файл напрямую из S3. Сохраняет оригинальный `Content-Type`, возвращает заголовок `Content-Disposition: attachment`.

**Пример**

```bash
curl -X GET "http://localhost:8000/files/cjld2cjxh0000qzrmn831i7rn.png" \
  -H "x-s3-access-key: ACCESS" \
  -H "x-s3-secret-key: SECRET" \
  -H "x-s3-endpoint: http://localhost:9000" \
  -H "x-s3-bucket: my-bucket" \
  --output image.png
```

---

### DELETE /files/{key}

Удаляет объект из S3.

**Response**

```json
{
  "success": true,
  "key": "cjld2cjxh0000qzrmn831i7rn.png"
}
```

---

### GET /files/{key}/presign

Генерирует временную ссылку для скачивания файла.

**Query параметры**

| Параметр   | Тип | По умолчанию | Описание                      |
| ---------- | --- | ------------ | ----------------------------- |
| `expires_in` | int | `900`      | Время жизни ссылки в секундах |

**Пример**

```bash
curl -X GET "http://localhost:8000/files/cjld2cjxh0000qzrmn831i7rn.png/presign?expires_in=3600" \
  -H "x-s3-access-key: ACCESS" \
  -H "x-s3-secret-key: SECRET" \
  -H "x-s3-endpoint: http://localhost:9000" \
  -H "x-s3-bucket: my-bucket"
```

**Response**

```json
{
  "success": true,
  "url": "https://s3...signed-url...",
  "expires_in": 3600
}
```

---

### GET /health

Проверка состояния сервиса.

**Response**

```json
{
  "success": true,
  "status": "ok"
}
```

---

## Ошибки

| Код | Описание               |
| --- | ---------------------- |
| 401 | Неверные credentials   |
| 403 | Доступ запрещён        |
| 404 | Файл не найден         |
| 500 | Внутренняя ошибка S3   |

---

## Поддерживаемые провайдеры

AWS S3, MinIO, DigitalOcean Spaces, Cloudflare R2, Wasabi, Backblaze B2 и любой S3-compatible провайдер.

---

## Установка и запуск

```bash
pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

По умолчанию сервис доступен по адресу `http://localhost:8000`.
