package mqtt

import (
    "encoding/json"
    "log"

    mqtt "github.com/eclipse/paho.mqtt.golang"
    "device-go/models"
)

type Handler struct {
    // Можно добавить канал для отправки ответов обратно в HTTP (если потребуется)
}

func NewHandler() *Handler {
    return &Handler{}
}

// HandleMessage обрабатывает входящие сообщения (топик devices/+/response)
func (h *Handler) HandleMessage(client mqtt.Client, msg mqtt.Message) {
    log.Printf("Received response on topic %s: %s", msg.Topic(), string(msg.Payload()))

    var resp models.MQTTResponse
    if err := json.Unmarshal(msg.Payload(), &resp); err != nil {
        log.Printf("Failed to parse response JSON: %v", err)
        return
    }

    // Логируем содержимое (можно отправить в лог или в канал для веб-сокетов)
    log.Printf("Response: command_id=%s, status=%s, data=%v", resp.CommandID, resp.Status, resp.Data)
}