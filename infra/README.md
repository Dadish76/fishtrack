
# FishTrack — Ansible Infrastructure

## Назначение

Базовая инфраструктура FishTrack управляется через Ansible.

Реализованы роли:

- common — системные пакеты и конфигурация узла
- docker — Docker Engine и Docker Compose
- users — пользователь deployer и права доступа
- ssh — безопасные настройки SSH
- firewall — настройки UFW
- registry — локальный Docker Registry

## Окружения

| Окружение | Хост | IP |
|---|---|---|
| demo | db-server | 192.168.56.20 |
| staging | app-server | 192.168.56.10 |

На текущем этапе playbook site.yml применяется только к группе demo.

Окружение staging описано в inventory, но не изменяется этим playbook.

## Подготовка Ansible Controller

```bash
python3 -m venv ~/.venvs/fishtrack-ansible
source ~/.venvs/fishtrack-ansible/bin/activate

python -m pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
```

## Применение конфигурации demo

Из каталога infra:

```bash
ansible-playbook site.yml --syntax-check
ansible-lint site.yml
ansible-playbook site.yml --ask-become-pass
```

Для текущего demo используется локальное подключение:

```yaml
ansible_connection: local
```

## Проверка

Проверка локального Registry:

```bash
curl -i http://127.0.0.1:5000/v2/
```

Проверка Docker:

```bash
sudo docker ps
```

Проверка firewall:

```bash
sudo ufw status numbered
```

Повторный запуск playbook должен завершиться с changed=0.

## Проверка configuration drift

Изменить управляемый конфигурационный файл:

```bash
sudo sed -i \
  's/^node_label=.*/node_label=BROKEN_CONFIG/' \
  /etc/fishtrack-node.conf
```

Восстановить конфигурацию:

```bash
ansible-playbook site.yml --ask-become-pass --diff
```

После выполнения значение node_label должно снова быть db-server-lab7.

## Ограничения текущей реализации

- Локальное выполнение Ansible проверено на существующей VM db-server.
- Bootstrap полностью чистой машины необходимо проверить отдельно.
- PostgreSQL на db-server пока сохранён, так как зависимость app-server ещё не исключена.
- Registry привязан только к 127.0.0.1:5000 и не предназначен для прямого удалённого доступа.
- Развёртывание FishTrack, Vault и инфраструктурный CI/CD pipeline добавляются отдельно.
