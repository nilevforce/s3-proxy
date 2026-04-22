# 📦 FastAPI S3 File Service

Сервис предоставляет REST API для работы с файлами в S3-совместимом хранилище (AWS S3, MinIO, DigitalOcean Spaces и др.).

---

## 🚀 Возможности

* 📤 Загрузка файлов в S3 (с сохранением Content-Type)
* 📥 Потоковое скачивание файлов (streaming)
* 🗑️ Удаление файлов
* 🔗 Presigned URL для скачивания (с настраиваемым временем жизни)
* 🔐 Поддержка S3-compatible storage (MinIO и др.)

---

## 🧱 Архитектура

```
Client → FastAPI → boto3 → S3 Storage
```

Backend выступает как прокси и генератор presigned URL.

---

## 🔐 Авторизация (Headers)

Каждый запрос требует S3 credentials:

| Header            | Описание                         |
| ----------------- | -------------------------------- |
| `x-s3-access-key` | Access Key                       |
| `x-s3-secret-key` | Secret Key                       |
| `x-s3-endpoint`   | S3 endpoint (AWS / MinIO / etc.) |
| `x-s3-bucket`     | Bucket name                      |
| `x-s3-region`     | (optional) region                |

---

## 📤 Upload File

### `POST /files/upload`

Загружает файл в S3.

### Request

* `multipart/form-data`
* `file` (required)

---

### Пример

```bash
curl -X POST "http://localhost:8000/files/upload" \
  -H "x-s3-access-key: ACCESS" \
  -H "x-s3-secret-key: SECRET" \
  -H "x-s3-endpoint: http://localhost:9000" \
  -H "x-s3-bucket: my-bucket" \
  -F "file=@image.png"
```

### Response

```json
{
  "success": true,
  "bucket": "my-bucket",
  "key": "cjld2cjxh0000qzrmn831i7rn.png"
}
```

---

## 📥 Download File (Streaming)

### `GET /files/{key}`

Стримит файл напрямую из S3.

### Особенности

* сохраняется `Content-Type`
* добавляется `Content-Disposition: attachment`
* браузер скачивает файл с корректным именем

---

### Пример

```bash
curl -X GET "http://localhost:8000/files/cjld2cjxh0000qzrmn831i7rn.png" \
  -H "x-s3-access-key: ACCESS" \
  -H "x-s3-secret-key: SECRET" \
  -H "x-s3-endpoint: http://localhost:9000" \
  -H "x-s3-bucket: my-bucket" \
  --output image.png
```

---

## 🗑️ Delete File

### `DELETE /files/{key}`

Удаляет объект из S3.

### Response

```json
{
  "success": true,
  "key": "cjld2cjxh0000qzrmn831i7rn.png"
}
```

---

## 🔗 Presigned Download URL

### `GET /files/{key}/presign`

Создаёт временную ссылку для скачивания.

### Query параметры

| Параметр   | Тип | По умолчанию | Описание                                 |
| ---------- | --- | ------------ | ---------------------------------------- |
| expires_in | int | 900          | Время жизни ссылки в секундах (15 минут) |

---

### Пример

```bash
curl -X GET "http://localhost:8000/files/cjld2cjxh0000qzrmn831i7rn.png/presign?expires_in=3600" \
  -H "x-s3-access-key: ACCESS" \
  -H "x-s3-secret-key: SECRET" \
  -H "x-s3-endpoint: http://localhost:9000" \
  -H "x-s3-bucket: my-bucket"
```

---

### Response

```json
{
  "success": true,
  "url": "https://s3...signed-url...",
  "expires_in": 3600
}
```

---

## ⚠️ Ошибки

| Code | Meaning             |
| ---- | ------------------- |
| 404  | File not found      |
| 403  | Access denied       |
| 401  | Invalid credentials |
| 500  | Internal S3 error   |
