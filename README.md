# 🐟 FishTrack

> **Система учета рыболовной фирмы** — управление катерами, командами и рейсами.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-24+-blue?style=flat&logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)](LICENSE)

---

## 📖 О проекте

**FishTrack ALPHA** — это альфа-версия системы для учета рыболовной фирмы.  
Позволяет вести учет катеров, команд и рейсов.

### 🎯 Назначение
- Управление парком катеров
- Ведение учета команд и капитанов
- Фиксация рейсов с датами отправления и возвращения

### 👥 Категории пользователей
| Роль | Возможности |
|------|-------------|
| **Администратор** | Полный CRUD доступ ко всем сущностям |
| **Менеджер** | Создание рейсов и просмотр статистики |
| **Капитан** | Просмотр своих рейсов (в будущем) |

---

## 🛠 Технологический стек

| Компонент | Технология |
|-----------|------------|
| **Backend** | Python 3.11+ / FastAPI |
| **ORM** | SQLAlchemy 2.0 |
| **База данных** | PostgreSQL 15 |
| **Тестирование** | Pytest + pytest-cov |
| **Контейнеризация** | Docker / Docker Compose |
| **Конфигурация** | python-dotenv |

---