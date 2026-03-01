# How-To Guide Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create `docs/HOW-TO.md` — a task-based Ukrainian user guide for non-technical AuditMagic users.

**Architecture:** Single Markdown file with 13 task-based sections. Screenshot images live in `docs/img/` and are referenced inline. Sections not yet having screenshots use `<!-- screenshot: docs/img/NAME.png -->` placeholders. No code changes required.

**Tech Stack:** Markdown, Ukrainian language, GitHub-compatible image embedding.

---

### Task 1: Create directory structure and skeleton file

**Files:**
- Create: `docs/img/.gitkeep`
- Create: `docs/HOW-TO.md`

**Step 1: Create the `docs/img/` directory with a gitkeep**

```bash
mkdir -p docs/img
touch docs/img/.gitkeep
```

**Step 2: Create the skeleton `docs/HOW-TO.md` with all 13 headings**

Create `docs/HOW-TO.md` with this content:

```markdown
# AuditMagic — Інструкція користувача

> Версія документу: 1.0

## Зміст

1. [Що таке AuditMagic](#1-що-таке-auditmagic)
2. [Перший запуск](#2-перший-запуск)
3. [Як додати локацію](#3-як-додати-локацію)
4. [Як додати товар](#4-як-додати-товар)
5. [Як знайти товар](#5-як-знайти-товар)
6. [Як змінити кількість](#6-як-змінити-кількість)
7. [Як додати або видалити серійний номер](#7-як-додати-або-видалити-серійний-номер)
8. [Як перемістити товар між локаціями](#8-як-перемістити-товар-між-локаціями)
9. [Як переглянути історію транзакцій](#9-як-переглянути-історію-транзакцій)
10. [Як відредагувати або видалити товар](#10-як-відредагувати-або-видалити-товар)
11. [Як експортувати в Excel](#11-як-експортувати-в-excel)
12. [Оновлення програми](#12-оновлення-програми)
13. [Зміна теми оформлення](#13-зміна-теми-оформлення)

---

## 1. Що таке AuditMagic

<!-- CONTENT -->

---

## 2. Перший запуск

<!-- CONTENT -->

---

## 3. Як додати локацію

<!-- CONTENT -->

---

## 4. Як додати товар

<!-- CONTENT -->

---

## 5. Як знайти товар

<!-- CONTENT -->

---

## 6. Як змінити кількість

<!-- CONTENT -->

---

## 7. Як додати або видалити серійний номер

<!-- CONTENT -->

---

## 8. Як перемістити товар між локаціями

<!-- CONTENT -->

---

## 9. Як переглянути історію транзакцій

<!-- CONTENT -->

---

## 10. Як відредагувати або видалити товар

<!-- CONTENT -->

---

## 11. Як експортувати в Excel

<!-- CONTENT -->

---

## 12. Оновлення програми

<!-- CONTENT -->

---

## 13. Зміна теми оформлення

<!-- CONTENT -->
```

**Step 3: Commit**

```bash
git add docs/img/.gitkeep docs/HOW-TO.md
git commit -m "docs: add how-to guide skeleton and img directory"
```

---

### Task 2: Write sections 1–3 (intro, first launch, locations)

**Files:**
- Modify: `docs/HOW-TO.md` — replace `<!-- CONTENT -->` in sections 1, 2, 3

**Step 1: Replace section 1 content**

Replace the `<!-- CONTENT -->` under `## 1. Що таке AuditMagic` with:

```markdown
AuditMagic — це програма для обліку інвентарю. Вона дозволяє:

- відстежувати, **що** у вас є і **де** це знаходиться;
- вести облік за кількістю або за серійними номерами;
- переміщати товари між локаціями;
- переглядати повну історію змін;
- експортувати дані в Excel.

<!-- screenshot: docs/img/main-window.png -->
```

**Step 2: Replace section 2 content**

Replace the `<!-- CONTENT -->` under `## 2. Перший запуск` with:

```markdown
При першому запуску програма попросить вас створити **локацію** — місце зберігання (наприклад, «Склад», «Офіс», «Кімната 101»).

1. Введіть назву локації у поле.
2. Натисніть **Зберегти**.

> ⚠️ Без локації програма не запуститься. Принаймні одна локація має існувати завжди.

<!-- screenshot: docs/img/first-launch.png -->
```

**Step 3: Replace section 3 content**

Replace the `<!-- CONTENT -->` under `## 3. Як додати локацію` with:

```markdown
Локації — це місця зберігання товарів (кімнати, склади, будівлі тощо).

**Відкрити управління локаціями:**
Натисніть кнопку **Керувати** поруч із випадним списком локацій угорі вікна.

**Додати нову локацію:**
1. Натисніть **Додати**.
2. Введіть назву (до 100 символів).
3. Натисніть **Зберегти**.

**Перейменувати локацію:**
1. Оберіть локацію зі списку.
2. Натисніть **Перейменувати**.
3. Введіть нову назву та натисніть **Зберегти**.

**Видалити локацію:**
1. Оберіть локацію зі списку.
2. Натисніть **Видалити**.

> ⚠️ Не можна видалити локацію, якщо в ній є товари. Спочатку перемістіть або видаліть всі товари.
> ⚠️ Не можна видалити останню локацію.
```

**Step 4: Commit**

```bash
git add docs/HOW-TO.md
git commit -m "docs: write how-to sections 1-3 (intro, first launch, locations)"
```

---

### Task 3: Write sections 4–6 (add item, search, quantity)

**Files:**
- Modify: `docs/HOW-TO.md` — replace `<!-- CONTENT -->` in sections 4, 5, 6

**Step 1: Replace section 4 content**

Replace under `## 4. Як додати товар`:

```markdown
Натисніть кнопку **Додати товар** у головному вікні.

Заповніть форму:

| Поле | Опис |
|------|------|
| **Тип** | Назва категорії товару (наприклад, «Ноутбук») |
| **Підтип** | Уточнення (наприклад, «ThinkPad X1») — необов'язково |
| **Серіалізований** | Увімкніть, якщо кожна одиниця має унікальний серійний номер |
| **Кількість** | Кількість одиниць (тільки для несеріалізованих товарів) |
| **Серійний номер** | Унікальний номер одиниці (тільки для серіалізованих) |
| **Локація** | Місце зберігання |
| **Примітки** | Додаткова інформація — необов'язково |

Натисніть **Зберегти**.

> ℹ️ **Серіалізований чи ні?**
> - Обирайте **серіалізований**, якщо потрібно відстежувати кожну одиницю окремо (техніка, обладнання з серійниками).
> - Обирайте **несеріалізований**, якщо важлива лише кількість (канцтовари, витратні матеріали).

<!-- screenshot: docs/img/add-item.png -->
```

**Step 2: Replace section 5 content**

Replace under `## 5. Як знайти товар`:

```markdown
**Пошук за назвою:**
Введіть текст у поле пошуку вгорі головного вікна. Список оновлюється автоматично.

**Фільтр за локацією:**
Оберіть локацію з випадного списку вгорі. Щоб переглянути всі локації одразу — оберіть **Всі локації**.

**Пошук у всіх локаціях:**
Поставте галочку **Шукати у всіх локаціях** поруч із пошуковим полем.

<!-- screenshot: docs/img/search.png -->
```

**Step 3: Replace section 6 content**

Replace under `## 6. Як змінити кількість`:

```markdown
Цей розділ стосується лише **несеріалізованих** товарів.

**Додати кількість:**
1. Клацніть правою кнопкою миші на товарі → **Додати кількість**.
   *(або двічі клацніть → кнопка **Додати**)*
2. Введіть кількість для додавання.
3. Натисніть **Підтвердити**.

**Зменшити кількість:**
1. Клацніть правою кнопкою миші на товарі → **Зменшити кількість**.
2. Введіть кількість для зменшення.
3. Натисніть **Підтвердити**.

> ⚠️ Кількість не може бути від'ємною. Якщо потрібно видалити товар повністю — використовуйте **Видалити**.
```

**Step 4: Commit**

```bash
git add docs/HOW-TO.md
git commit -m "docs: write how-to sections 4-6 (add item, search, quantity)"
```

---

### Task 4: Write sections 7–9 (serial numbers, transfer, transactions)

**Files:**
- Modify: `docs/HOW-TO.md` — replace `<!-- CONTENT -->` in sections 7, 8, 9

**Step 1: Replace section 7 content**

Replace under `## 7. Як додати або видалити серійний номер`:

```markdown
Цей розділ стосується лише **серіалізованих** товарів.

**Додати новий серійний номер (нову одиницю):**
1. Клацніть правою кнопкою миші на товарі → **Додати кількість**.
2. Введіть серійний номер нової одиниці.
3. Додайте примітку (необов'язково).
4. Натисніть **Зберегти**.

**Видалити серійний номер (одиницю):**
1. Клацніть правою кнопкою миші на товарі → **Зменшити кількість**.
2. Поставте галочки напроти серійних номерів, які потрібно видалити.
3. Введіть причину видалення.
4. Натисніть **Підтвердити**.

> ⚠️ Щоб видалити **всі** одиниці серіалізованого типу — використовуйте **Видалити** через контекстне меню.
```

**Step 2: Replace section 8 content**

Replace under `## 8. Як перемістити товар між локаціями`:

```markdown
1. Клацніть правою кнопкою миші на товарі → **Перемістити**.
2. Оберіть **локацію призначення** зі списку.
3. Для несеріалізованих: введіть **кількість** для переміщення.
4. Для серіалізованих: поставте галочки напроти **серійних номерів**, які переміщуєте.
5. Додайте примітку (необов'язково).
6. Натисніть **Перемістити**.

> ℹ️ Переміщення фіксується в історії транзакцій з зазначенням локацій «Звідки» та «Куди».

<!-- screenshot: docs/img/transfer.png -->
```

**Step 3: Replace section 9 content**

Replace under `## 9. Як переглянути історію транзакцій`:

```markdown
**Транзакції конкретного товару:**
1. Клацніть правою кнопкою миші на товарі → **Транзакції**.
2. За потреби відфільтруйте за **датою** (поля «Від» та «До»).

**Всі транзакції (всіх товарів):**
1. У меню оберіть **Перегляд → Всі транзакції** (або відповідну кнопку).
2. Відфільтруйте за **локацією** та/або **датою**.

Таблиця транзакцій містить:
- Дату та час
- Тип операції (Додано / Видалено / Редаговано / Переміщено)
- Назву товару
- Кількість до та після
- Серійний номер (якщо є)
- Локації «Звідки» та «Куди» (для переміщень)
- Примітку

<!-- screenshot: docs/img/transactions.png -->
```

**Step 4: Commit**

```bash
git add docs/HOW-TO.md
git commit -m "docs: write how-to sections 7-9 (serial numbers, transfer, transactions)"
```

---

### Task 5: Write sections 10–13 (edit/delete, export, updates, theme)

**Files:**
- Modify: `docs/HOW-TO.md` — replace `<!-- CONTENT -->` in sections 10, 11, 12, 13

**Step 1: Replace section 10 content**

Replace under `## 10. Як відредагувати або видалити товар`:

```markdown
**Редагувати товар:**
1. Клацніть правою кнопкою миші на товарі → **Редагувати**.
   *(або двічі клацніть на товарі)*
2. Змініть потрібні поля.
3. Введіть **причину зміни** (обов'язкове поле).
4. Натисніть **Зберегти**.

> ℹ️ Тип серіалізації (серіалізований/несеріалізований) не можна змінити після того, як товар уже було додано.

**Видалити товар:**
1. Клацніть правою кнопкою миші на товарі → **Видалити**.
2. Підтвердіть видалення.

> ⚠️ Видалення незворотне. Записи в історії транзакцій зберігаються навіть після видалення товару.
```

**Step 2: Replace section 11 content**

Replace under `## 11. Як експортувати в Excel`:

```markdown
1. Натисніть кнопку **Експорт** або оберіть **Файл → Експортувати**.
2. У вікні параметрів оберіть, що включити до звіту:
   - Поточний інвентар
   - Історію транзакцій
   - Фільтр за локацією або датою
3. Натисніть **Експортувати**.
4. Оберіть папку та назву файлу.

Результат — файл `.xlsx`, який можна відкрити в Excel або Google Sheets.

<!-- screenshot: docs/img/export.png -->
```

**Step 3: Replace section 12 content**

Replace under `## 12. Оновлення програми`:

```markdown
При кожному запуску AuditMagic автоматично перевіряє наявність нової версії.

Якщо оновлення доступне — з'явиться вікно з повідомленням:
- Натисніть **Завантажити** — відкриється сторінка для завантаження нової версії.
- Натисніть **Пропустити** — програма продовжить роботу без оновлення.

> ℹ️ Ваші дані зберігаються локально і не видаляються при оновленні програми.
```

**Step 4: Replace section 13 content**

Replace under `## 13. Зміна теми оформлення`:

```markdown
AuditMagic підтримує світлу та темну теми.

1. У рядку меню оберіть **🎨 Тема**.
2. Оберіть **Світла** або **Темна**.

Тема зберігається автоматично і застосовується при наступному запуску.
```

**Step 5: Commit**

```bash
git add docs/HOW-TO.md
git commit -m "docs: write how-to sections 10-13 (edit/delete, export, updates, theme)"
```

---

### Task 6: Final polish — link README to HOW-TO

**Files:**
- Modify: `README.md`

**Step 1: Update README.md**

Replace the empty README with:

```markdown
# AuditMagic

Програма для обліку інвентарю з підтримкою локацій, серійних номерів та експорту в Excel.

📖 **[Інструкція користувача](docs/HOW-TO.md)**
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: link how-to guide from README"
```

---

### Task 7: Add screenshots (user-supplied)

**Files:**
- Add: `docs/img/main-window.png`
- Add: `docs/img/first-launch.png`
- Add: `docs/img/add-item.png`
- Add: `docs/img/search.png`
- Add: `docs/img/transfer.png`
- Add: `docs/img/transactions.png`
- Add: `docs/img/export.png`

**Step 1: User takes screenshots and saves them to `docs/img/`**

Screenshots needed (see design doc for details):

| File | What to capture |
|------|----------------|
| `docs/img/main-window.png` | Main window with items in the list |
| `docs/img/first-launch.png` | First-launch location dialog |
| `docs/img/add-item.png` | Add Item dialog |
| `docs/img/search.png` | Search bar + location selector area |
| `docs/img/transfer.png` | Transfer dialog |
| `docs/img/transactions.png` | All Transactions dialog |
| `docs/img/export.png` | Export Options dialog |

**Step 2: Remove placeholder comments**

After each image is added, replace its `<!-- screenshot: docs/img/NAME.png -->` comment with:

```markdown
![Description](img/NAME.png)
```

For example, replace `<!-- screenshot: docs/img/main-window.png -->` with:

```markdown
![Головне вікно AuditMagic](img/main-window.png)
```

**Step 3: Commit**

```bash
git add docs/img/
git add docs/HOW-TO.md
git commit -m "docs: add screenshots to how-to guide"
```
