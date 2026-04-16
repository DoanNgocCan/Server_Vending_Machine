"""
MQTT Publisher Module for Vending Machine Server.

Publishes product update notifications to clients in real-time:
- vending_machine/product/update       : price / stock hot-updates
- vending_machine/product/data_changed : new product created or details modified
"""

import json
import os
import logging
import time
import threading

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

# --- Topics ---
TOPIC_PRODUCT_UPDATE = "vending_machine/product/update"
TOPIC_DATA_CHANGED   = "vending_machine/product/data_changed"

# --- Retry settings ---
_MAX_RETRIES = 3
_RETRY_DELAY = 1  # seconds between retries


class MQTTPublisher:
    """Thread-safe MQTT publisher with graceful error handling."""

    def __init__(self):
        self.host     = os.environ.get("MQTT_BROKER_HOST", "localhost")
        self.port     = int(os.environ.get("MQTT_BROKER_PORT", 1883))
        self.username = os.environ.get("MQTT_USERNAME", "")
        self.password = os.environ.get("MQTT_PASSWORD", "")
        self._client  = None
        self._lock    = threading.Lock()
        self._connected = False
        self._connect()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            logger.info("MQTT publisher connected to broker %s:%s", self.host, self.port)
        else:
            self._connected = False
            logger.warning("MQTT publisher failed to connect, return code: %s", rc)

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        if rc != 0:
            logger.warning("MQTT publisher unexpectedly disconnected (rc=%s). Will retry on next publish.", rc)

    def _connect(self):
        """Attempt to connect to the MQTT broker. Errors are non-fatal."""
        try:
            client = mqtt.Client()
            client.on_connect    = self._on_connect
            client.on_disconnect = self._on_disconnect
            if self.username:
                client.username_pw_set(self.username, self.password)
            client.connect_async(self.host, self.port, keepalive=60)
            client.loop_start()
            self._client = client
        except Exception as exc:
            logger.warning("MQTT broker unavailable, publisher disabled: %s", exc)
            self._client = None

    def _ensure_connected(self):
        """Re-connect if the broker connection was lost."""
        if self._client is None:
            self._connect()
        elif not self._connected:
            try:
                self._client.reconnect()
                time.sleep(0.5)
            except Exception as exc:
                logger.debug("MQTT reconnect attempt failed: %s", exc)

    def _publish(self, topic: str, payload: dict) -> bool:
        """
        Publish *payload* (dict) to *topic* with retry logic.
        Returns True on success, False on failure.
        """
        message = json.dumps(payload, ensure_ascii=False)
        for attempt in range(1, _MAX_RETRIES + 1):
            with self._lock:
                self._ensure_connected()
                if self._client is None or not self._connected:
                    logger.warning(
                        "MQTT not connected (attempt %s/%s), skipping publish to %s",
                        attempt, _MAX_RETRIES, topic,
                    )
                    time.sleep(_RETRY_DELAY)
                    continue
                try:
                    result = self._client.publish(topic, message, qos=1)
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        logger.info("MQTT published to %s: %s", topic, message)
                        return True
                    logger.warning(
                        "MQTT publish returned rc=%s (attempt %s/%s)",
                        result.rc, attempt, _MAX_RETRIES,
                    )
                except Exception as exc:
                    logger.warning(
                        "MQTT publish error on attempt %s/%s: %s",
                        attempt, _MAX_RETRIES, exc,
                    )
            time.sleep(_RETRY_DELAY)
        logger.error("MQTT publish failed after %s attempts for topic %s", _MAX_RETRIES, topic)
        return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def publish_product_update(self, device_id: str, product_id: str, price: float, units_left: int) -> bool:
        """
        Publish a hot-update (price or stock change) for a product.

        Topic : vending_machine/product/update
        Payload: {"device_id": "...", "product_id": "...", "price": 12000, "units_left": 45}
        """
        payload = {
            "device_id": device_id,  # Bây giờ biến này mới có giá trị
            "product_id": product_id,
            "price":      price,
            "units_left": units_left,
        }
        logger.info(f"Publishing product update for '{product_id}' (Target: {device_id})")
        return self._publish(TOPIC_PRODUCT_UPDATE, payload)

    def publish_new_product(self, product_id: str) -> bool:
        """
        Notify clients that a brand-new product was added.

        Topic : vending_machine/product/data_changed
        Payload: {"event": "new_product_added", "product_id": "..."}
        """
        payload = {
            "event":      "new_product_added",
            "product_id": product_id,
        }
        logger.info("Publishing new_product event for '%s'", product_id)
        return self._publish(TOPIC_DATA_CHANGED, payload)

    def publish_product_modified(self, product_id: str) -> bool:
        """
        Notify clients that an existing product's details were changed.

        Topic : vending_machine/product/data_changed
        Payload: {"event": "product_updated", "product_id": "..."}
        """
        payload = {
            "event":      "product_updated",
            "product_id": product_id,
        }
        logger.info("Publishing product_updated event for '%s'", product_id)
        return self._publish(TOPIC_DATA_CHANGED, payload)
    
    def publish_hot_update(self, device_id, old_name, new_name, price, units_left):
        """Bắn tín hiệu thay đổi Tên, Giá, Số lượng cho một máy cụ thể"""
        payload = {
            "device_id": device_id, 
            "old_name": old_name,
            "new_name": new_name,
            "price": price,
            "units_left": units_left
        }
        # Sử dụng biến TOPIC_PRODUCT_UPDATE ("vending_machine/product/update") 
        # và hàm _publish có sẵn để có retry và in log đầy đủ
        logger.info(f"Publishing HOT UPDATE for '{old_name}' -> '{new_name}' (Target: {device_id})")
        return self._publish(TOPIC_PRODUCT_UPDATE, payload)

    def disconnect(self):
        """Cleanly stop the MQTT loop and disconnect."""
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
        self._connected = False


# ---------------------------------------------------------------------------
# Module-level singleton — lazily created so that import never crashes.
# ---------------------------------------------------------------------------
_publisher_instance: MQTTPublisher | None = None
_publisher_lock = threading.Lock()


def get_publisher() -> MQTTPublisher:
    """Return (or create) the global MQTTPublisher singleton."""
    global _publisher_instance
    if _publisher_instance is None:
        with _publisher_lock:
            if _publisher_instance is None:
                _publisher_instance = MQTTPublisher()
    return _publisher_instance
