#!/usr/bin/env python3
"""
Тест производительности для Telegram бота
Симулирует одновременные запросы от 18 пользователей
"""

import asyncio
import time
from database import DatabaseManager
import config

class PerformanceTest:
    def __init__(self):
        self.db_manager = DatabaseManager()
        
    async def setup(self):
        """Инициализация тестовой среды"""
        await self.db_manager.init_database()
        
        # Создаем тестовое событие
        test_date = "2024-01-01"
        self.event_id = await self.db_manager.create_event(test_date, 12345)
        print(f"Created test event with ID: {self.event_id}")
        
    async def simulate_user_join(self, user_id: int):
        """Симуляция записи пользователя"""
        start_time = time.time()
        
        success, position = await self.db_manager.add_participant(
            event_id=self.event_id,
            user_id=user_id,
            username=f"user{user_id}",
            first_name=f"User",
            last_name=f"{user_id}"
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        return {
            'user_id': user_id,
            'success': success,
            'position': position,
            'duration': duration
        }
    
    async def run_concurrent_test(self, num_users: int = 18):
        """Запуск теста с конкурентными запросами"""
        print(f"\nStarting concurrent test with {num_users} users...")
        
        start_time = time.time()
        
        # Создаем задачи для всех пользователей
        tasks = []
        for i in range(1, num_users + 1):
            task = self.simulate_user_join(i)
            tasks.append(task)
        
        # Выполняем все задачи одновременно
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        return results, total_duration
    
    async def analyze_results(self, results, total_duration):
        """Анализ результатов тестирования"""
        print(f"\n=== РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ===")
        print(f"Общее время выполнения: {total_duration:.3f} секунд")
        print(f"Количество запросов: {len(results)}")
        print(f"Средняя скорость: {len(results) / total_duration:.1f} запросов/сек")
        
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        print(f"\nУспешных записей: {len(successful)}")
        print(f"Неудачных записей: {len(failed)}")
        
        if successful:
            avg_duration = sum(r['duration'] for r in successful) / len(successful)
            max_duration = max(r['duration'] for r in successful)
            min_duration = min(r['duration'] for r in successful)
            
            print(f"\nВремя обработки одного запроса:")
            print(f"  Среднее: {avg_duration:.3f} сек")
            print(f"  Максимальное: {max_duration:.3f} сек")
            print(f"  Минимальное: {min_duration:.3f} сек")
        
        # Проверяем финальное состояние базы данных
        participants = await self.db_manager.get_participants(self.event_id)
        count = await self.db_manager.get_participant_count(self.event_id)
        
        print(f"\nФинальное состояние:")
        print(f"  Участников в БД: {count}")
        print(f"  Ожидалось: {min(len(results), config.MAX_PARTICIPANTS)}")
        
        # Проверяем на дублирование
        unique_users = set(p[0] for p in participants)  # user_id
        print(f"  Уникальных пользователей: {len(unique_users)}")
        
        if len(unique_users) != count:
            print("  ⚠️  ОБНАРУЖЕНО ДУБЛИРОВАНИЕ!")
        else:
            print("  ✅ Дублирования не обнаружено")
            
        # Проверяем корректность позиций
        positions = [p[4] for p in participants]  # position
        expected_positions = list(range(1, len(participants) + 1))
        
        if sorted(positions) == expected_positions:
            print("  ✅ Позиции корректны")
        else:
            print("  ⚠️  НЕКОРРЕКТНЫЕ ПОЗИЦИИ!")
            print(f"      Ожидалось: {expected_positions}")
            print(f"      Получено: {sorted(positions)}")
    
    async def cleanup(self):
        """Очистка тестовых данных"""
        # В реальном тесте здесь можно удалить тестовые данные
        pass

async def main():
    """Основная функция тестирования"""
    test = PerformanceTest()
    
    try:
        await test.setup()
        
        # Тест 1: Стандартная нагрузка (18 пользователей)
        print("=" * 50)
        print("ТЕСТ 1: 18 одновременных запросов")
        print("=" * 50)
        
        results, duration = await test.run_concurrent_test(18)
        await test.analyze_results(results, duration)
        
        # Тест 2: Превышение лимита (25 пользователей)
        print("\n" + "=" * 50)
        print("ТЕСТ 2: 25 одновременных запросов (превышение лимита)")
        print("=" * 50)
        
        # Сначала очищаем предыдущий тест
        await test.setup()
        
        results, duration = await test.run_concurrent_test(25)
        await test.analyze_results(results, duration)
        
        await test.cleanup()
        
    except Exception as e:
        print(f"Ошибка тестирования: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 