package config

import (
    "os"
    "strconv"
    "strings"

    "github.com/joho/godotenv"
)

type Config struct {
    HTTPPort     int
    MQTTBroker   string
    MQTTUsername string
    MQTTPassword string
    LogLevel     string
}

func Load() *Config {
    _ = godotenv.Load()
    return &Config{
        HTTPPort:     getEnvAsInt("HTTP_PORT", 8080),
        MQTTBroker:   getEnv("MQTT_BROKER", "tcp://localhost:1883"),
        MQTTUsername: getEnv("MQTT_USERNAME", ""),
        MQTTPassword: getEnv("MQTT_PASSWORD", ""),
        LogLevel:     getEnv("LOG_LEVEL", "info"),
    }
}

func getEnv(key, defaultValue string) string {
    if v := os.Getenv(key); strings.TrimSpace(v) != "" {
        return v
    }
    return defaultValue
}

func getEnvAsInt(key string, defaultValue int) int {
    if v := os.Getenv(key); v != "" {
        if i, err := strconv.Atoi(v); err == nil {
            return i
        }
    }
    return defaultValue
}