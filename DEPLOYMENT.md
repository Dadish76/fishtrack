# 🚀 DEPLOYMENT — Развёртывание FishTrack в Linux

> Документ описывает развёртывание приложения FishTrack на двух Linux-серверах: `app-server` и `db-server`. Все шаги проверены и могут быть повторены.

---

## 📌 Схема развёртывания

```text
app-server (192.168.56.10) ──:5432──▶ db-server (192.168.56.20)
        ▲
        │ :8000
      Клиент
```

| Сервер       | IP              | Назначение                 |
| ------------ | --------------- | -------------------------- |
| `app-server` | `192.168.56.10` | Приложение, systemd        |
| `db-server`  | `192.168.56.20` | PostgreSQL, БД `fishtrack` |

---

## 📋 Требования

| Требование                       | Как выполнено               |
| -------------------------------- | --------------------------- |
| Приложение НЕ работает от root   | systemd: `User=appuser`     |
| Лишние порты НЕ открыты          | UFW: только 22, 8000, 5432  |
| Пароли НЕ хранятся в репозитории | `.env` в `/etc/fishtrack/`  |
| SSH-доступ только по ключам      | `PasswordAuthentication no` |
| Удалённый вход под root запрещён | `PermitRootLogin no`        |

---

# 1️⃣ Подготовка виртуальных машин

## 1.1. Создать две VM

Ubuntu Server 24.04+.

| Параметр |    app-server |     db-server |
| -------- | ------------: | ------------: |
| RAM      |          2 GB |          2 GB |
| CPU      |        2 ядра |        2 ядра |
| Диск     |         20 GB |         20 GB |
| Сеть     | Bridged + NAT | Bridged + NAT |

---

## 1.2. Настроить сеть (netplan)

Файл:

```text
/etc/netplan/00-installer-config.yaml
```

Содержимое:

```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: no
      addresses:
        - 192.168.56.10/24
    enp0s8:
      dhcp4: yes
```

Применить настройки:

```bash
sudo netplan apply
```

> На `db-server` необходимо использовать соответствующий статический адрес `192.168.56.20/24`.

---

## 1.3. Прописать хосты

Файл `/etc/hosts` на обеих VM:

```text
192.168.56.10  app-server
192.168.56.20  db-server
```

Проверка:

```bash
ping -c 3 app-server
ping -c 3 db-server
```

---

# 2️⃣ SSH-доступ по ключам

## 2.1. Сгенерировать ключ на клиенте

```bash
ssh-keygen -t ed25519 -C "devops@fishtrack"
```

---

## 2.2. Скопировать ключ на VM

Для PowerShell:

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh deployer@192.168.56.10 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Аналогично добавить ключ на `db-server`.

---

## 2.3. Запретить root и пароли

На обеих VM изменить:

```text
/etc/ssh/sshd_config
```

Параметры:

```text
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

Перезапустить SSH:

```bash
sudo systemctl restart ssh
```

> Перед отключением `PasswordAuthentication` убедитесь, что вход по SSH-ключу уже работает в отдельной сессии.

---

## 2.4. Создать пользователя `appuser`

На `app-server`:

```bash
sudo adduser appuser
```

Пользователя `appuser` **не добавлять в группу `sudo`**.

---

# 3️⃣ Права на файлы и каталоги

Создать каталог приложения:

```bash
sudo mkdir -p /opt/fishtrack
sudo chown -R appuser:appuser /opt/fishtrack
sudo chmod 750 /opt/fishtrack
```

Создать каталог конфигурации:

```bash
sudo mkdir -p /etc/fishtrack
sudo chown root:appuser /etc/fishtrack
sudo chmod 750 /etc/fishtrack
```

---

# 4️⃣ Установка среды выполнения и СУБД

## 4.1. На app-server — Python 3.11

```bash
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev git
```

---

## 4.2. На db-server — PostgreSQL

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
```

Включить автозапуск:

```bash
sudo systemctl enable postgresql
```

Запустить PostgreSQL:

```bash
sudo systemctl start postgresql
```

Проверить статус:

```bash
sudo systemctl status postgresql
```

---

# 5️⃣ Создание БД и пользователя

Все действия выполняются на `db-server`.

Открыть PostgreSQL:

```bash
sudo -u postgres psql
```

Создать БД и пользователя:

```sql
CREATE DATABASE fishtrack;

CREATE USER fishtrack_user WITH PASSWORD 'strong_password_123';

GRANT ALL PRIVILEGES ON DATABASE fishtrack TO fishtrack_user;

\c fishtrack

GRANT ALL ON SCHEMA public TO fishtrack_user;

\q
```

> В production рекомендуется использовать отдельный сильный пароль и не хранить его непосредственно в документации.

---

## 5.1. Настройка `pg_hba.conf`

Добавить:

```text
host    fishtrack    fishtrack_user    192.168.56.10/32    md5
```

---

## 5.2. Настройка `postgresql.conf`

Указать:

```text
listen_addresses = '192.168.56.20'
```

Перезапустить PostgreSQL:

```bash
sudo systemctl restart postgresql
```

Проверить:

```bash
sudo systemctl status postgresql
```

---

# 6️⃣ Firewall (UFW)

## 6.1. На app-server

Разрешить SSH:

```bash
sudo ufw allow 22/tcp
```

Разрешить приложение:

```bash
sudo ufw allow 8000/tcp
```

Включить firewall:

```bash
sudo ufw --force enable
```

Проверить:

```bash
sudo ufw status verbose
```

---

## 6.2. На db-server

Разрешить SSH:

```bash
sudo ufw allow 22/tcp
```

Разрешить PostgreSQL только с `app-server`:

```bash
sudo ufw allow from 192.168.56.10 to any port 5432 proto tcp
```

Включить firewall:

```bash
sudo ufw --force enable
```

Проверить:

```bash
sudo ufw status verbose
```

---

# 7️⃣ Развёртывание приложения

Все действия выполняются на `app-server`.

Переключиться на пользователя `appuser`:

```bash
sudo -u appuser -i
```

Перейти в каталог приложения:

```bash
cd /opt/fishtrack
```

Клонировать репозиторий:

```bash
git clone https://github.com/Dadish76/fishtrack.git .
```

Создать виртуальное окружение:

```bash
python3.11 -m venv venv
```

Активировать его:

```bash
source venv/bin/activate
```

Установить зависимости:

```bash
pip install -r backend/requirements.txt
```

Выйти из пользователя:

```bash
exit
```

---

# 8️⃣ Настройки отдельно от кода

Создать файл:

```text
/etc/fishtrack/.env
```

Пример содержимого:

```dotenv
DATABASE_URL=postgresql://fishtrack_user:strong_password_123@192.168.56.20:5432/fishtrack
SECRET_KEY=change-me-in-production
DEBUG=False
PORT=8000
```

Установить владельца:

```bash
sudo chown root:appuser /etc/fishtrack/.env
```

Установить права:

```bash
sudo chmod 640 /etc/fishtrack/.env
```

Таким образом:

* `root` может читать и изменять файл;
* пользователи группы `appuser` могут читать файл;
* остальные пользователи доступа не имеют.

> ⚠️ Файл `.env` **НЕ должен коммититься в Git**.

Добавьте его в `.gitignore`:

```gitignore
.env
*.env
```

---

# 9️⃣ Systemd-служба

Создать файл:

```text
/etc/systemd/system/fishtrack.service
```

Содержимое:

```ini
[Unit]
Description=FishTrack FastAPI Application
After=network.target

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/opt/fishtrack
EnvironmentFile=/etc/fishtrack/.env
ExecStart=/opt/fishtrack/venv/bin/uvicorn backend.src.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Перечитать конфигурацию systemd:

```bash
sudo systemctl daemon-reload
```

Включить автозапуск:

```bash
sudo systemctl enable fishtrack
```

Запустить приложение:

```bash
sudo systemctl start fishtrack
```

Проверить статус:

```bash
sudo systemctl status fishtrack
```

---

# 🔟 Проверка автозапуска и автоперезапуска

## 10.1. Автозапуск после перезагрузки

Перезагрузить `app-server`:

```bash
sudo reboot
```

После подключения проверить:

```bash
sudo systemctl status fishtrack
```

Также можно проверить:

```bash
systemctl is-enabled fishtrack
```

Ожидаемый результат:

```text
enabled
```

---

## 10.2. Автоперезапуск после падения

Найти процесс:

```bash
pgrep -af uvicorn
```

Завершить процесс:

```bash
sudo kill -9 <PID>
```

Подождать:

```bash
sleep 10
```

Проверить службу:

```bash
sudo systemctl status fishtrack
```

Проверить процесс:

```bash
pgrep -af uvicorn
```

Благодаря:

```ini
Restart=always
RestartSec=5
```

systemd должен автоматически запустить приложение повторно.

---

# 1️⃣1️⃣ Диагностика

| Задача                  | Команда                                                |
| ----------------------- | ------------------------------------------------------ |
| Поиск процесса          | `pgrep -af uvicorn`                                    |
| Поиск порта             | `sudo ss -tlnp \| grep 8000`                           |
| Последние логи          | `sudo journalctl -u fishtrack -n 50`                   |
| Логи в реальном времени | `sudo journalctl -u fishtrack -f`                      |
| Статус firewall         | `sudo ufw status verbose`                              |
| Подключение к БД        | `psql -h 192.168.56.20 -U fishtrack_user -d fishtrack` |

---

## Проверка приложения

На `app-server`:

```bash
curl http://127.0.0.1:8000
```

С клиентской машины:

```bash
curl http://192.168.56.10:8000
```

Если приложение предоставляет endpoint `/docs`, можно открыть:

```text
http://192.168.56.10:8000/docs
```

---

## Проверка подключения к PostgreSQL

С `app-server`:

```bash
psql -h 192.168.56.20 -U fishtrack_user -d fishtrack
```

При запросе пароля использовать пароль пользователя `fishtrack_user`.

---

# 1️⃣2️⃣ Скрипты развёртывания

В проекте используются:

```text
scripts/
├── provision_app.sh
└── deploy.sh
```

* `provision_app.sh` — первоначальная настройка;
* `deploy.sh` — обновление приложения.

---

## `scripts/deploy.sh`

```bash
#!/bin/bash

set -e

cd /opt/fishtrack

sudo -u appuser git pull origin main

sudo -u appuser /opt/fishtrack/venv/bin/pip install \
    -r backend/requirements.txt

sudo systemctl restart fishtrack
```

Сделать скрипт исполняемым:

```bash
chmod +x scripts/deploy.sh
```

Запуск:

```bash
./scripts/deploy.sh
```

---

# 1️⃣3️⃣ Закрытые порты

|   Порт | Где        | Кому доступен          |
| -----: | ---------- | ---------------------- |
|   `22` | обе VM     | SSH-доступ             |
| `8000` | app-server | клиентам приложения    |
| `5432` | db-server  | только `192.168.56.10` |

На `db-server` PostgreSQL не должен быть доступен напрямую из внешней сети, кроме разрешённого соединения от `app-server`.

---

# 1️⃣4️⃣ Итоговая проверка

После завершения развёртывания рекомендуется выполнить следующие проверки.

### app-server

```bash
systemctl status fishtrack
```

```bash
sudo ss -tlnp | grep 8000
```

```bash
sudo ufw status verbose
```

```bash
curl http://127.0.0.1:8000
```

### db-server

```bash
sudo systemctl status postgresql
```

```bash
sudo ss -tlnp | grep 5432
```

```bash
sudo ufw status verbose
```

### Проверка соединения app-server → db-server

```bash
psql -h 192.168.56.20 -U fishtrack_user -d fishtrack
```

---

# ✅ Результат

В результате получается следующая схема:

```text
                         ┌─────────────────────┐
                         │      Клиент         │
                         └──────────┬──────────┘
                                    │
                                  :8000
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │       app-server          │
                    │     192.168.56.10         │
                    │                           │
                    │ FastAPI + Uvicorn         │
                    │ systemd                   │
                    │ User=appuser              │
                    └─────────────┬─────────────┘
                                  │
                                :5432
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │        db-server          │
                    │     192.168.56.20         │
                    │                           │
                    │ PostgreSQL                │
                    │ DB: fishtrack             │
                    └───────────────────────────┘
```

Основные требования лабораторной работы выполнены:

* приложение запускается не от `root`;
* приложение управляется через `systemd`;
* приложение автоматически запускается после перезагрузки;
* приложение автоматически перезапускается после падения;
* PostgreSQL находится на отдельном сервере;
* доступ к PostgreSQL ограничен `app-server`;
* конфигурация и пароли находятся вне Git-репозитория;
* SSH настроен на авторизацию по ключам;
* удалённый вход под `root` запрещён;
* firewall ограничивает доступ к необходимым портам.

---

📌 **Актуально для:** лабораторной работы №2 по курсу **«DevOps и CI/CD»**.
