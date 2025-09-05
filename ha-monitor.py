#!/usr/bin/env python3

import subprocess
from datetime import datetime

import paho.mqtt.client as mqtt

TOPIC_NAME = "homeassistant/status"
broker_ip = "localhost"
broker_port = 1883


class SimpleHAStatusMonitor:
    def __init__(self, broker=broker_ip, port=broker_port):
        self.broker = broker
        self.port = port
        self.current_status = None
        self.previous_status = None

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            result = client.subscribe(TOPIC_NAME)
            if result[0] == 0:
                print(f"Subscribed to {TOPIC_NAME}")
            else:
                print(f"Failed subscribe to {TOPIC_NAME}")
            print("✓ await status for Home Assistant...")
        else:
            print(f"✗ Connection error: {reason_code} - {mqtt.error_string(reason_code)}")

    def on_message(self, client, userdata, msg):
        if msg.topic == TOPIC_NAME:
            new_status = msg.payload.decode().strip().lower()
            timestamp = datetime.now().strftime("%H:%M:%S")

            # Сохраняем предыдущий статус
            self.previous_status = self.current_status
            self.current_status = new_status

            # Всегда выводим статус
            print(f"[{timestamp}] Status: {new_status}")

            # Проверяем переход в online
            if ((not self.previous_status and
                  self.current_status == "online") or
                    (self.previous_status == "offline" and
                     self.current_status == "online")):
                self.wb_engine_start()

    def on_disconnect(self, client, *args):
        print("Connection lost")

    def wb_engine_start(self):
        """
        Стартуем бинарник wb-engine-helper с флагом --start
        :return:
        """
        try:
            print("Try to start wb-engine-helper...")
            res = subprocess.run(["wb-engine-helper", "--start"],
                                 capture_output=True,
                                 text=True, )
            print(res.stdout)

        except subprocess.CalledProcessError as e:
            print(f"Command failed with exit code {e.returncode}")
            print(f"Stderr: {e.stderr.decode()}")

    def start(self):
        # Используем актуальную версию callback API
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_disconnect = self.on_disconnect

        try:
            client.connect(self.broker, self.port, 60)
            client.loop_forever()
        except Exception as e:
            print(f"Error: {e}")


# Запуск мониторинга
if __name__ == "__main__":
    monitor = SimpleHAStatusMonitor()
    monitor.start()
