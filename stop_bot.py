#!/usr/bin/env python3
"""
Скрипт для остановки всех запущенных экземпляров бота
"""

import psutil
import sys
import os

def find_bot_processes():
    """Находит все процессы связанные с ботом"""
    bot_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and any('bot.py' in cmd or 'run.py' in cmd for cmd in cmdline):
                # Пропускаем текущий процесс
                if proc.pid != os.getpid():
                    bot_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return bot_processes

def stop_bot_processes():
    """Останавливает все процессы бота"""
    processes = find_bot_processes()
    
    if not processes:
        print("🟢 Никаких процессов бота не найдено.")
        return
    
    print(f"🔍 Найдено {len(processes)} процессов бота:")
    
    for proc in processes:
        try:
            print(f"  - PID {proc.pid}: {' '.join(proc.cmdline())}")
            proc.terminate()
            print(f"  ✅ Процесс {proc.pid} остановлен")
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"  ❌ Не удалось остановить процесс {proc.pid}: {e}")
    
    print("\n✅ Все процессы бота остановлены!")
    print("Теперь можно запустить: python run.py")

if __name__ == "__main__":
    try:
        stop_bot_processes()
    except KeyboardInterrupt:
        print("\n❌ Операция прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1) 