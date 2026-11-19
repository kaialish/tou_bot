"""
Удобный скрипт для быстрого запуска сервера ToU Mini App из корня проекта.
Запуск: python run_webapp.py
"""
import sys
from pathlib import Path

# Добавляем корень проекта в путь
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.webapp_server import start_server
import asyncio

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def _main():
        await start_server(host="127.0.0.1", port=8080)
        # Держим процесс активным
        while True:
            await asyncio.sleep(3600)

    try:
        loop.run_until_complete(_main())
    except KeyboardInterrupt:
        print("\nСервер остановлен.")

