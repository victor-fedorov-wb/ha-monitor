#!/usr/bin/env python3

import subprocess
import sys, os
import logging
import paho.mqtt.client as mqtt

# Настройки сервисов хранить в /etc/ИМЯ_СЕРВИСА.conf в формате JSON.

TOPIC_NAME = os.getenv("HA_TOPIC_NAME", "homeassistant/status")
BROKER_IP = os.getenv("BROKER_IP", "localhost")
BROKER_PORT = os.getenv("BROKER_PORT", 1883)

# setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


class SimpleHAStatusMonitor:
    """
    Monitor Home Assistant status via MQTT.
    Use actual callback API (v2)
    """

    def __init__(
        self,
        broker=BROKER_IP,
        port=int(BROKER_PORT),
    ):
        logger.debug(f"BROKER_IP {BROKER_IP}")
        logger.debug(f"BROKER_PORT {BROKER_PORT}")
        self.broker = broker
        self.port = port
        self.current_status = None
        self.previous_status = None

    def on_connect(
        self,
        client,
        userdata,
        flags,
        reason_code,
        properties,
    ):
        if reason_code == 0:
            result = client.subscribe(TOPIC_NAME)
            if result[0] == 0:
                logger.info(f"Subscribed to {TOPIC_NAME}")
            else:
                logger.error(f"Failed subscribe to {TOPIC_NAME}")
        else:
            logger.error(
                f"Connection error: {reason_code} - {mqtt.error_string(reason_code)}"
            )

    def on_message(
        self,
        client,
        userdata,
        msg,
    ):
        if msg.topic == TOPIC_NAME:
            new_status = msg.payload.decode().strip().lower()
            # Save prev status
            self.previous_status = self.current_status
            self.current_status = new_status
            logger.info(f"Status: {new_status}")
            # Check status "online"
            if (not self.previous_status and self.current_status == "online") or (
                self.previous_status == "offline" and self.current_status == "online"
            ):
                self.wb_engine_start()

    def on_disconnect(
        self,
        client,
        userdata=None,
        disconnect_flags=None,
        reason_code=None,
        properties=None,
    ):
        logger.error("Connection lost")

    def wb_engine_start(self):
        """
        Start wb-engine-helper --start
        :return:
        """
        try:
            logger.info("Try to start wb-engine-helper...")
            res = subprocess.run(
                ["wb-engine-helper", "--start"],
                capture_output=True,
                text=True,
            )
            logger.warning(res.stdout)

        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed with exit code {e.returncode}")
            logger.error(f"Stderr: {e.stderr.decode()}")

    def start(self):
        # Use actual callback API (v2)
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_disconnect = self.on_disconnect

        try:
            client.connect(self.broker, self.port, 60)
            client.loop_forever()
        except Exception as e:
            logger.error(f"Error: {e}")


# Starting monitoring
if __name__ == "__main__":
    monitor = SimpleHAStatusMonitor()
    monitor.start()
