from __future__ import annotations

import json
import random
import socket
import ssl
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import paho.mqtt.client as mqtt
from locust import User, events, task

MQTT_HOST = "nsu-metrics.ru"
MQTT_PORT = 8883
MQTT_USERNAME = "avs"
MQTT_PASSWORD = "avs"
MQTT_QOS = 1
MQTT_KEEPALIVE = 180
MQTT_CONNECT_TIMEOUT_SEC = 15
MQTT_PUBLISH_TIMEOUT_SEC = 10
MQTT_CLIENT_PREFIX = "avs-locust"

TLS_INSECURE = False
CO2_RANGE = (450, 1800)
TEMPERATURE_RANGE = (17, 30)
HUMIDITY_RANGE = (25, 75)
BASE_INTERVAL_MIN_SEC = 55.0
BASE_INTERVAL_MAX_SEC = 65.0
INTERVAL_JITTER_SEC = 7.0
STARTUP_CONNECT_SPREAD_SEC = 60.0
CONNECT_RETRY_BASE_SEC = 1.5
CONNECT_RETRY_MAX_SEC = 15.0
CONNECT_RETRY_JITTER_SEC = 0.8

EXPECTED_SENSORS = 940


@dataclass(frozen=True)
class Sensor:
    sensor_id: str
    index: int
    room_number: str
    building_name: str


def _mapping_path() -> Path:
    return Path("ingest-go/mapping_eng.txt")


def _load_sensors() -> list[Sensor]:
    sensors: list[Sensor] = []
    path = _mapping_path()
    with path.open("r", encoding="utf-8") as mapping_file:
        for lineno, raw_line in enumerate(mapping_file, start=1):
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split("|")
            if len(parts) != 3:
                raise ValueError(
                    f"{path}:{lineno} expected sensor_<n>|room|building, got: {line!r}"
                )

            sensor_id, room_number, building_name = (p.strip() for p in parts)
            if not sensor_id.startswith("sensor_"):
                raise ValueError(f"{path}:{lineno} invalid sensor id: {sensor_id!r}")

            try:
                index = int(sensor_id.split("_", 1)[1])
            except (ValueError, IndexError) as exc:
                raise ValueError(f"{path}:{lineno} invalid sensor index in {sensor_id!r}") from exc

            sensors.append(
                Sensor(
                    sensor_id=sensor_id,
                    index=index,
                    room_number=room_number,
                    building_name=building_name,
                )
            )

    if len(sensors) != EXPECTED_SENSORS:
        raise ValueError(f"{path} has {len(sensors)} sensors, expected {EXPECTED_SENSORS}")

    return sensors


SENSORS = _load_sensors()
SENSOR_ASSIGN_LOCK = threading.Lock()
NEXT_SENSOR_INDEX = 0


def _assign_sensor() -> Sensor:
    global NEXT_SENSOR_INDEX
    with SENSOR_ASSIGN_LOCK:
        sensor = SENSORS[NEXT_SENSOR_INDEX % len(SENSORS)]
        NEXT_SENSOR_INDEX += 1
        return sensor


class MqttSensorClient:
    def __init__(self, environment, sensor: Sensor) -> None:
        self.environment = environment
        self.sensor = sensor
        self._connected = threading.Event()
        self._connect_rc: Optional[int] = None
        self.is_connected = False

        client_id = f"{MQTT_CLIENT_PREFIX}-{sensor.sensor_id}-{uuid.uuid4().hex[:6]}"
        try:
            self._client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=client_id,
                clean_session=True,
            )
        except AttributeError:
            self._client = mqtt.Client(client_id=client_id, clean_session=True)

        self._client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        tls_context = ssl.create_default_context()
        if TLS_INSECURE:
            tls_context.check_hostname = False
            tls_context.verify_mode = ssl.CERT_NONE
        self._client.tls_set_context(tls_context)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    def connect(self) -> None:
        started = time.perf_counter()
        self._connected.clear()
        self._connect_rc = None
        self.is_connected = False
        try:
            self._client.connect(MQTT_HOST, MQTT_PORT, keepalive=MQTT_KEEPALIVE)
        except (OSError, socket.error) as exc:
            self._fire_request("connect", started, 0, exc)
            return

        self._client.loop_start()

        if not self._connected.wait(MQTT_CONNECT_TIMEOUT_SEC):
            exc = TimeoutError(
                f"connect timeout after {MQTT_CONNECT_TIMEOUT_SEC}s for {self.sensor.sensor_id}"
            )
            self._fire_request("connect", started, 0, exc)
            self.disconnect()
            return

        if self._connect_rc not in (0, mqtt.MQTT_ERR_SUCCESS):
            exc = ConnectionError(f"connect failed rc={self._connect_rc}")
            self._fire_request("connect", started, 0, exc)
            self.disconnect()
            return

        self.is_connected = True
        self._fire_request("connect", started, 0, None)

    def disconnect(self) -> None:
        try:
            self._client.loop_stop()
        finally:
            try:
                self._client.disconnect()
            except Exception:
                pass
        self.is_connected = False
        self._connected.clear()

    def publish_data(self) -> None:
        if not self.is_connected:
            return

        topic = f"sensors/{self.sensor.index}/data"
        payload = {
            "sensorId": self.sensor.sensor_id,
            "buildingName": self.sensor.building_name,
            "roomNumber": self.sensor.room_number,
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "co2": random.randint(*CO2_RANGE),
            "temperature": random.randint(*TEMPERATURE_RANGE),
            "humidity": random.randint(*HUMIDITY_RANGE),
        }
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

        started = time.perf_counter()
        try:
            info = self._client.publish(topic, payload_bytes, qos=MQTT_QOS)
        except Exception as exc:
            self.is_connected = False
            self._fire_request("publish", started, len(payload_bytes), exc, name=topic)
            return

        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            exc = RuntimeError(f"publish failed rc={info.rc}")
            self.is_connected = False
            self._fire_request("publish", started, len(payload_bytes), exc, name=topic)
            return

        try:
            info.wait_for_publish(timeout=MQTT_PUBLISH_TIMEOUT_SEC)
        except Exception as exc:
            self._fire_request("publish", started, len(payload_bytes), exc, name=topic)
            return

        if not info.is_published():
            exc = TimeoutError(f"PUBACK timeout after {MQTT_PUBLISH_TIMEOUT_SEC}s")
            self._fire_request("publish", started, len(payload_bytes), exc, name=topic)
            return

        self._fire_request("publish", started, len(payload_bytes), None, name=topic)

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        self._connect_rc = getattr(reason_code, "value", reason_code)
        self._connected.set()

    def _on_disconnect(self, client, userdata, *args, **kwargs):
        self._connected.clear()
        self.is_connected = False

    def _fire_request(
        self,
        kind: str,
        start: float,
        response_length: int,
        exception: Optional[BaseException],
        name: Optional[str] = None,
    ) -> None:
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.environment.events.request.fire(
            request_type=f"MQTT-{kind.upper()}",
            name=name or kind,
            response_time=elapsed_ms,
            response_length=response_length,
            exception=exception,
            context={"sensor_id": self.sensor.sensor_id},
        )


class SensorUser(User):
    def wait_time(self) -> float:
        jitter = random.uniform(-INTERVAL_JITTER_SEC, INTERVAL_JITTER_SEC)
        return max(0.1, self.base_interval_sec + jitter)

    def __init__(self, environment):
        super().__init__(environment)
        self.sensor = _assign_sensor()
        self.base_interval_sec = random.uniform(BASE_INTERVAL_MIN_SEC, BASE_INTERVAL_MAX_SEC)
        self.mqtt_client = MqttSensorClient(environment, self.sensor)
        self._next_reconnect_at = 0.0
        self._reconnect_failures = 0

    def _schedule_next_reconnect(self, attempt: int = 0) -> None:
        delay = min(
            CONNECT_RETRY_MAX_SEC,
            CONNECT_RETRY_BASE_SEC * (2 ** max(0, attempt)),
        ) + random.uniform(0.0, CONNECT_RETRY_JITTER_SEC)
        self._next_reconnect_at = time.monotonic() + delay

    def on_start(self) -> None:
        time.sleep(random.uniform(0.0, STARTUP_CONNECT_SPREAD_SEC))
        self.mqtt_client.connect()
        if not self.mqtt_client.is_connected:
            self._reconnect_failures = 1
            self._schedule_next_reconnect(attempt=self._reconnect_failures)
        else:
            self._reconnect_failures = 0

    def on_stop(self) -> None:
        self.mqtt_client.disconnect()

    @task
    def publish_sensor_data(self) -> None:
        if not self.mqtt_client.is_connected:
            if time.monotonic() >= self._next_reconnect_at:
                self.mqtt_client.connect()
                if not self.mqtt_client.is_connected:
                    self._reconnect_failures += 1
                    self._schedule_next_reconnect(attempt=self._reconnect_failures)
                else:
                    self._reconnect_failures = 0
            return
        self.mqtt_client.publish_data()


@events.init.add_listener
def _on_init(environment, **_kwargs):
    if len(SENSORS) != EXPECTED_SENSORS:
        raise RuntimeError(
            f"Need exactly {EXPECTED_SENSORS} sensors, got {len(SENSORS)} from mapping_eng.txt"
        )
