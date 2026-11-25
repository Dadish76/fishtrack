# FishTrack — Ansible Infrastructure

## Назначение

Лабораторная работа №7: управление конфигурацией и воспроизводимая инфраструктура.

Ansible автоматизирует настройку Linux-сервера, развёртывание FishTrack,
проверку работоспособности приложения и восстановление управляемой конфигурации.

## Роли Ansible

- common — базовые пакеты и конфигурация Ubuntu.
- docker — Docker Engine и Docker Compose.
- users — пользователь развёртывания, SSH-ключи, каталоги и права.
- ssh — безопасная конфигурация SSH.
- firewall — настройка UFW.
- registry — локальный Docker Registry.
- fishtrack_app — PostgreSQL, FastAPI, Nginx и развёртывание приложения.

Конфигурационные файлы генерируются из шаблонов Jinja2.

## Окружения и параметры

| Окружение | Узел | Адрес | Назначение |
|---|---|---|---|
| demo | db-server | 192.168.56.20 | Ansible-развёртывание FishTrack |
| staging | app-server | 192.168.56.10 | Отдельное staging-окружение |

Inventory находятся в inventories/demo.yml и inventories/staging.yml.
Параметры окружений определяются в group_vars/.
Секреты demo хранятся в зашифрованном vault/demo.yml.

Текущий site.yml настраивает demo и не изменяет staging.
Для demo используется ansible_connection: local.
Приложение demo развёртывается из ветки develop.

## Подготовка Ansible Controller

На Ubuntu установить минимальные инструменты:

    sudo apt-get update
    sudo apt-get install -y git python3 python3-venv python3-pip

После получения репозитория перейти в каталог infra:

    cd infra
    python3 -m venv ~/.venvs/fishtrack-ansible
    source ~/.venvs/fishtrack-ansible/bin/activate
    python -m pip install -r requirements.txt
    ansible-galaxy collection install -r requirements.yml

Версии зависимостей зафиксированы в requirements.txt и requirements.yml.

## Проверка и развёртывание

Проверить синтаксис и lint:

    ansible-playbook -i inventories/demo.yml site.yml --syntax-check
    ansible-lint site.yml

Применить конфигурацию demo:

    ansible-playbook -i inventories/demo.yml site.yml --limit demo --ask-become-pass --ask-vault-pass

Playbook устанавливает Docker и необходимые пакеты, настраивает
пользователей, SSH, UFW, каталоги и Registry, получает исходный код,
собирает Docker-образ и запускает PostgreSQL, два экземпляра FastAPI
и Nginx.

При развёртывании новой версии выполняются миграции и инициализация
администратора. Успешно установленная версия записывается в
.deployed_sha. При неизменном Git SHA одноразовые задачи не повторяются.

## Автоматическая проверка приложения

Ansible проверяет HTTP endpoints:

- /health
- /version
- /docs
- /openapi.json

Ручная проверка на demo:

    sudo docker ps --filter "name=fishtrack-demo"
    curl -i http://127.0.0.1:8082/health
    curl -sS http://127.0.0.1:8082/version

CRUD smoke-тест из корня репозитория:

    python3 scripts/smoke_test.py --base-url http://127.0.0.1:8082 --expected-tag "$(git rev-parse --short=12 HEAD)" --boat-payload-file scripts/smoke_boat.json

Проверяются создание, чтение, сравнение и удаление записи,
а также HTTP 404 после удаления.

Проверенный результат: PASS: FishTrack create -> read -> compare -> delete -> 404.

## Идемпотентность и восстановление состояния

Повторный запуск Ansible без изменения исходных параметров
завершился с changed=0 и failed=0.

Для проверки восстановления конфигурации вручную изменялись
права каталога /opt/fishtrack-demo:

    sudo chmod 0700 /opt/fishtrack-demo

Затем повторно применялся site.yml.

Ansible обнаружил отклонение и восстановил требуемые права:

    750 root:root /opt/fishtrack-demo

Результат: changed=1, failed=0.
После восстановления /health возвращал HTTP 200.

## Сетевая безопасность

- UFW включён; входящие подключения запрещены по умолчанию.
- SSH разрешён из сети 192.168.56.0/24.
- FishTrack Nginx доступен на 127.0.0.1:8082.
- Docker Registry доступен на 127.0.0.1:5000.
- PostgreSQL из Docker Compose не публикует порт хоста.
- Контейнеры FastAPI не публикуют порты хоста.
- Каталог приложения имеет владельца root:root и права 0750.

Отдельный PostgreSQL на хосте db-server слушает 192.168.56.20:5432.
Доступ через UFW разрешён только с 192.168.56.10.
Эта служба не входит в Docker Compose demo; перед изменением
её настроек необходимо проверить зависимости staging.

Команды docker compose config --quiet и sshd -t используются
для проверки корректности конфигурации и не изменяют состояние узла.

## Защита секретов

Секреты demo хранятся в vault/demo.yml, зашифрованном Ansible Vault (AES256).

Рабочие .env-файлы и приватные ключи не должны попадать в Git.
Файлы .env.example и .env.container.example предназначены для примеров
и не должны содержать действующих секретов.

Резервные копии базы данных также не должны добавляться в репозиторий.

## Infrastructure CI и согласование изменений

Инфраструктурный pipeline расположен в:

    .github/workflows/infra-ci.yml

Он проверяет синтаксис Ansible, ansible-lint и формат Vault.

Критические инфраструктурные файлы защищены CODEOWNERS:

    /infra/ @Dadish76 @f1stle

Для ветки develop настроены обязательные Pull Request,
одобрение изменений и проверка Code Owners.

## Проверка на чистой Ubuntu

Первоначальное развёртывание также проверено на отдельной чистой VM.

На тестовой машине выполнены:

1. Установка минимальных инструментов Ansible Controller.
2. Получение репозитория из develop.
3. Установка зависимостей Ansible.
4. Проверка синтаксиса playbook.
5. Первоначальное развёртывание инфраструктуры.
6. Проверка Docker-контейнеров и доступности FishTrack.
7. Повторное применение конфигурации без лишних изменений.

Проверки чистой VM прошли успешно.

## Итог ЛР №7

Подтверждены:

- автоматизированное развёртывание FishTrack;
- разделение demo и staging;
- использование Jinja2 и Ansible Vault;
- подготовка чистой Linux-машины;
- обновление приложения из develop;
- доступность приложения и прохождение CRUD smoke-теста;
- идемпотентность Ansible;
- восстановление вручную изменённой конфигурации;
- ограничения сетевого доступа;
- инфраструктурный CI и обязательное ревью.

Проверенная версия приложения demo: 3f86a240a5fa.

Ограничение: staging описан отдельно и не изменяется demo playbook.
