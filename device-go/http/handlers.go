package http

import (
    "encoding/json"
    "net/http"
    "slices"

    "github.com/google/uuid"
    "device-go/models"
    "device-go/mqtt"
)

type Handlers struct {
    mqttClient *mqtt.Client
}

func NewHandlers(mqttClient *mqtt.Client) *Handlers {
    return &Handlers{
        mqttClient: mqttClient,
    }
}

// SendCommand обрабатывает POST /api/commands
func (h *Handlers) SendCommand(w http.ResponseWriter, r *http.Request) {
    var req models.CommandRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, "Invalid request body", http.StatusBadRequest)
        return
    }
    if req.DeviceID == "" || req.Command == "" {
        http.Error(w, "device_id and command are required", http.StatusBadRequest)
        return
    }

    // Проверка, что команда поддерживается
    if !slices.Contains(models.AllCommands(), req.Command) {
        http.Error(w, "unsupported command", http.StatusBadRequest)
        return
    }

    // Генерируем ID команды для отслеживания
    cmdID := uuid.New().String()

    mqttCmd := &models.MQTTCommand{
        CommandID:  cmdID,
        Command:    req.Command,
        Parameters: req.Parameters,
    }

    // Публикуем в MQTT
    if err := h.mqttClient.PublishCommand(req.DeviceID, mqttCmd); err != nil {
        http.Error(w, "Failed to publish command to MQTT", http.StatusInternalServerError)
        return
    }

    resp := models.CommandResponse{
        CommandID: cmdID,
        Status:    "sent",
    }
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusAccepted)
    json.NewEncoder(w).Encode(resp)
}

// ListCommands обрабатывает GET /api/commands/list
func (h *Handlers) ListCommands(w http.ResponseWriter, r *http.Request) {
    commands := models.AllCommands()
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(commands)
}