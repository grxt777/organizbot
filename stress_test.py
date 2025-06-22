#!/usr/bin/env python3
"""
Стресс-тест для определения максимальной нагрузки Telegram бота
"""

import asyncio
import time
from database import DatabaseManager
import config

class StressTest:
    def __init__(self):
        self.db_manager = DatabaseManager()
        
    async def setup(self):
        """Инициализация тестовой среды"""
        await self.db_manager.init_database()
        test_date = f"stress-test-{int(time.time())}"
        self.event_id = await self.db_manager.create_event(test_date, 99999)
        return self.event_id
        
    async def simulate_user_join(self, user_id: int):
        """Симуляция записи пользователя"""
        start_time = time.time()
        
        try:
            success, position = await self.db_manager.add_participant(
                event_id=self.event_id,
                user_id=user_id,
                username=f"stress_user{user_id}",
                first_name=f"Stress",
                last_name=f"User{user_id}"
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            return {
                'user_id': user_id,
                'success': success,
                'position': position,
                'duration': duration,
                'error': None
            }
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            return {
                'user_id': user_id,
                'success': False,
                'position': -1,
                'duration': duration,
                'error': str(e)
            }
    
    async def run_stress_test(self, num_users: int):
        """Запуск стресс-теста"""
        print(f"\n🔥 СТРЕСС-ТЕСТ: {num_users} одновременных пользователей")
        print("=" * 60)
        
        start_time = time.time()
        
        # Создаем задачи для всех пользователей
        tasks = [self.simulate_user_join(i) for i in range(1, num_users + 1)]
        
        # Выполняем все задачи одновременно
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        return results, total_duration
    
    async def analyze_stress_results(self, results, total_duration, num_users):
        """Анализ результатов стресс-теста"""
        print(f"\n📊 РЕЗУЛЬТАТЫ СТРЕСС-ТЕСТА ({num_users} пользователей)")
        print("=" * 60)
        print(f"⏱️  Общее время: {total_duration:.3f} сек")
        print(f"🚀 Скорость: {num_users / total_duration:.1f} запросов/сек")
        
        # Фильтруем результаты от исключений
        valid_results = [r for r in results if isinstance(r, dict)]
        exceptions = [r for r in results if not isinstance(r, dict)]
        
        if exceptions:
            print(f"❌ Исключений: {len(exceptions)}")
        
        successful = [r for r in valid_results if r['success']]
        failed = [r for r in valid_results if not r['success']]
        errors = [r for r in valid_results if r['error']]
        
        print(f"✅ Успешных записей: {len(successful)}")
        print(f"❌ Неудачных записей: {len(failed)}")
        print(f"🐛 Ошибок: {len(errors)}")
        
        if successful:
            durations = [r['duration'] for r in successful]
            print(f"\n⚡ Производительность:")
            print(f"   Среднее время: {sum(durations)/len(durations):.3f} сек")
            print(f"   Максимальное: {max(durations):.3f} сек")
            print(f"   Минимальное: {min(durations):.3f} сек")
        
        # Проверяем состояние БД
        participants = await self.db_manager.get_participants(self.event_id)
        count = len(participants)
        
        print(f"\n💾 База данных:")
        print(f"   Записей в БД: {count}")
        print(f"   Ожидалось: {min(len(successful), config.MAX_PARTICIPANTS)}")
        
        # Проверяем целостность данных
        if count <= config.MAX_PARTICIPANTS:
            print("   ✅ Лимит соблюден")
        else:
            print("   ⚠️  ПРЕВЫШЕН ЛИМИТ!")
        
        user_ids = [p[0] for p in participants]
        if len(set(user_ids)) == len(user_ids):
            print("   ✅ Нет дублирования")
        else:
            print("   ❌ ЕСТЬ ДУБЛИРОВАНИЕ!")
        
        return {
            'total_time': total_duration,
            'requests_per_sec': num_users / total_duration,
            'successful': len(successful),
            'failed': len(failed),
            'errors': len(errors),
            'db_records': count
        }

async def main():
    """Основная функция стресс-тестирования"""
    test = StressTest()
    results_summary = []
    
    # Тестируемые нагрузки
    test_loads = [50, 100, 200, 500, 1000]
    
    print("🚀 ЗАПУСК СТРЕСС-ТЕСТИРОВАНИЯ TELEGRAM БОТА")
    print("=" * 60)
    
    for num_users in test_loads:
        try:
            # Новое событие для каждого теста
            await test.setup()
            
            results, duration = await test.run_stress_test(num_users)
            summary = await test.analyze_stress_results(results, duration, num_users)
            
            results_summary.append({
                'users': num_users,
                **summary
            })
            
            # Пауза между тестами
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"❌ Ошибка в тесте с {num_users} пользователей: {e}")
            continue
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("📈 ИТОГОВЫЙ ОТЧЕТ ПРОИЗВОДИТЕЛЬНОСТИ")
    print("=" * 60)
    
    print(f"{'Пользователи':<12} {'Время':<8} {'Запр/сек':<10} {'Успешно':<9} {'Ошибок':<8} {'В БД':<6}")
    print("-" * 60)
    
    max_successful_load = 0
    max_rps = 0
    
    for result in results_summary:
        print(f"{result['users']:<12} {result['total_time']:<8.2f} "
              f"{result['requests_per_sec']:<10.1f} {result['successful']:<9} "
              f"{result['errors']:<8} {result['db_records']:<6}")
        
        if result['errors'] == 0 and result['successful'] > 0:
            max_successful_load = max(max_successful_load, result['users'])
        
        max_rps = max(max_rps, result['requests_per_sec'])
    
    print("\n🏆 ВЫВОДЫ:")
    print(f"   Максимальная нагрузка без ошибок: {max_successful_load} пользователей")
    print(f"   Максимальная скорость: {max_rps:.1f} запросов/сек")
    print(f"   Лимит участников: {config.MAX_PARTICIPANTS}")
    
    if max_successful_load >= 100:
        print("   ✅ Бот отлично справляется с высокой нагрузкой!")
    elif max_successful_load >= 50:
        print("   ✅ Бот хорошо справляется с нагрузкой!")
    else:
        print("   ⚠️  Бот имеет ограничения по нагрузке")

if __name__ == "__main__":
    asyncio.run(main()) 