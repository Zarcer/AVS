package main

import (
    "log"
    "os"
    "os/signal"
    "syscall"
    "time"

    nethttp "net/http" 
    "device-go/config"
    "device-go/http"   
    "device-go/mqtt"
)

func main() {
    cfg := config.Load()

    log.Println("Starting Device Service...")
    log.Printf("HTTP Port: %d", cfg.HTTPPort)
    log.Printf("MQTT Broker: %s", cfg.MQTTBroker)

    // MQTT клиент
    mqttHandler := mqtt.NewHandler()
    mqttClient := mqtt.NewClient(cfg, mqttHandler)
    if err := mqttClient.Connect(); err != nil {
        log.Fatalf("Failed to connect to MQTT: %v", err)
    }
    defer mqttClient.Disconnect()

    // HTTP обработчики
    httpHandlers := http.NewHandlers(mqttClient)
    httpServer := http.NewServer(httpHandlers, cfg.HTTPPort)

    // Graceful shutdown
    sigChan := make(chan os.Signal, 1)
    signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

    go func() {
        if err := httpServer.Start(); err != nil && err != nethttp.ErrServerClosed {
            log.Fatalf("HTTP server error: %v", err)
        }
    }()

    log.Println("Service is running. Press Ctrl+C to stop.")
    <-sigChan
    log.Println("Shutting down...")
    time.Sleep(2 * time.Second)
    log.Println("Service stopped")
}