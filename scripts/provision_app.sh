#!/bin/bash
set -e

echo "=== Установка зависимостей ==="
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev git postgresql-client

echo "=== Создание каталогов ==="
sudo mkdir -p /opt/fishtrack /etc/fishtrack
sudo chown -R appuser:appuser /opt/fishtrack
sudo chown root:appuser /etc/fishtrack
sudo chmod 750 /opt/fishtrack /etc/fishtrack

echo "=== Настройка UFW ==="
sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp
sudo ufw --force enable

echo "=== Готово ==="
