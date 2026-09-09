
## Таблицы

### Boats (Катера)
| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | INTEGER | PRIMARY KEY | ID катера |
| name | VARCHAR(100) | NOT NULL | Название |
| registration_number | VARCHAR(20) | UNIQUE NOT NULL | Бортовой номер |
| capacity | FLOAT | NOT NULL, > 0 | Вместимость |

### Crews (Команды)
| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | INTEGER | PRIMARY KEY | ID команды |
| captain_name | VARCHAR(100) | NOT NULL | Капитан |
| members_count | INTEGER | NOT NULL, > 0 | Количество |

### Trips (Рейсы)
| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | INTEGER | PRIMARY KEY | ID рейса |
| boat_id | INTEGER | FOREIGN KEY → Boats(id) | Катер |
| crew_id | INTEGER | FOREIGN KEY → Crews(id) | Команда |
| departure_date | DATETIME | NOT NULL | Отправление |
| return_date | DATETIME | > departure_date | Возврат |

## Бизнес-правила
1. `registration_number` — уникален
2. Вместимость катера > 0
3. Дата возврата ≥ даты отправления