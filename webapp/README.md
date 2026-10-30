# 📱 ToU Telegram Mini App (TMA)

Интерактивное веб-приложение для студентов Торайгыров Университета, открывающееся прямо внутри Telegram.

## 🚀 Как запустить для локальной разработки

### 1. Запуск локального веб-сервера
В корне проекта выполните:
```bash
python src/webapp_server.py
```
Сервер запустится на `http://localhost:8080`.

Вы можете **сразу открыть эту ссылку в Chrome или Edge** — приложение поддерживает режим симулятора с демонстрационными данными (Mock Data), стилизовано под мобильное устройство и работает без Telegram.

---

### 2. Подключение к Telegram (HTTPS туннель)

Telegram требует, чтобы Mini App открывался строго по **HTTPS**. Для локальной разработки используйте бесплатный туннель **Cloudflare Tunnel** (`cloudflared`) или **ngrok**:

#### Вариант A: Cloudflare Tunnel (Рекомендуется, без регистрации)
1. Установите `cloudflared` через терминал:
   ```powershell
   winget install --id Cloudflare.cloudflared
   ```
2. В отдельном терминале запустите туннель к локальному серверу:
   ```bash
   cloudflared tunnel --url http://localhost:8080
   ```
3. Cloudflare выдаст публичный HTTPS-адрес вида:
   `https://random-words.trycloudflare.com`

4. Укажите этот адрес в `.env`:
   ```env
   WEBAPP_URL=https://random-words.trycloudflare.com
   ```

---

### 3. Настройка кнопки в @BotFather

Чтобы кнопка Mini App отображалась у поля ввода в Telegram:
1. Откройте диалог с **@BotFather** в Telegram.
2. Введите `/setmenubutton` ➔ выберите вашего тестового бота.
3. Отправьте адрес туннеля (например: `https://random-words.trycloudflare.com`).
4. Введите название кнопки: `📱 Расписание`.

Готово! Теперь в чате с ботом появится кнопка меню для запуска приложения в один клик.

