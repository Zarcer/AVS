# device-go

Микросервис для управления ESP32-устройствами через MQTT.  
Принимает HTTP-запросы на отправку команд (перезагрузка, получение данных с датчиков, OTA-обновление и др.), публикует их в MQTT и логирует ответы устройств.

---

## Требования

- Go 1.21 или выше
- MQTT-брокер (например, Mosquitto)

---

## Быстрый старт

1. Клонируйте репозиторий:

```bash
git clone <url>
cd device-go
```

2. Скопируйте файл `.env.example` в `.env` и при необходимости отредактируйте:

```bash
cp .env.example .env
```

3. Установите зависимости:

```bash
go mod tidy
```

4. Запустите сервис:

```bash
go run cmd/device-go/main.go
```

---

## Конфигурация

Настройки задаются через переменные окружения или файл `.env`.

| Переменная      | Описание                          | Значение по умолчанию      |
|----------------|----------------------------------|-----------------------------|
| HTTP_PORT      | Порт HTTP-сервера                | 8080                        |
| MQTT_BROKER    | Адрес MQTT-брокера               | tcp://localhost:1883        |
| MQTT_USERNAME  | Имя пользователя MQTT (если есть)| ""                          |
| MQTT_PASSWORD  | Пароль MQTT (если есть)          | ""                          |
| LOG_LEVEL      | Уровень логирования              | info                        |

---

## API эндпоинты

| Метод | Путь                | Описание                          |
|-------|---------------------|-----------------------------------|
| POST  | `/api/commands`     | Отправить команду устройству      |
| GET   | `/api/commands/list`| Получить список поддерживаемых команд |
| GET   | `/health`           | Проверка здоровья сервиса         |

---

## POST `/api/commands`

Отправляет команду устройству.

### Тело запроса (JSON)

```json
{
  "device_id": "esp32-001",
  "command": "reboot",
  "parameters": {
    "delay": 5
  }
}
```

### Успешный ответ (202 Accepted)

```json
{
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "sent"
}
```

---

## GET `/api/commands/list`

Возвращает массив строк с названиями поддерживаемых команд:

```json
[
  "reboot",
  "get_sensors",
  "get_battery",
  "ota_update",
  "ota_rollback",
  "get_version",
  "set_location",
  "enable_fall_detection",
  "get_orientation"
]
```

---

## Примеры использования

### Получить список команд

```bash
curl http://localhost:8080/api/commands/list
```

### Отправить команду перезагрузки

```bash
curl -X POST http://localhost:8080/api/commands \
  -H "Content-Type: application/json" \
  -d '{"device_id":"esp32-001","command":"reboot","parameters":{"delay":5}}'
```

### Запросить показания датчиков

```bash
curl -X POST http://localhost:8080/api/commands \
  -H "Content-Type: application/json" \
  -d '{"device_id":"esp32-001","command":"get_sensors","parameters":{}}'
```

### Проверить работоспособность

```bash
curl http://localhost:8080/health
```

---

## Структура проекта

```
device-go/
├── cmd/
│   └── device-go/        # точка входа
├── config/               # загрузка конфигурации
├── http/                 # HTTP-обработчики и сервер
├── models/               # структуры данных
├── mqtt/                 # MQTT-клиент и обработчик ответов
├── .env.example          # пример переменных окружения
├── Dockerfile
├── go.mod
└── README.md
```