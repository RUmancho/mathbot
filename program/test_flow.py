#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестовый скрипт для отладки flow состояния
"""

import core

def test_city_validation():
    """Тестирует валидацию городов"""
    test_cities = [
        "нижний новгород",
        "москва", 
        "санкт-петербург",
        "екатеринбург",
        "новосибирск"
    ]
    
    print("Тестирование валидации городов:")
    for city in test_cities:
        is_valid = core.Validator.city(city)
        print(f"'{city}': {'✅' if is_valid else '❌'} ({is_valid})")
    
    # Тестируем с буквой ё
    city_with_yo = "нижний новгород"
    print(f"\nТестирование с буквой ё:")
    print(f"'{city_with_yo}': {'✅' if core.Validator.city(city_with_yo) else '❌'}")

def test_flow_simulation():
    """Симулирует flow для поиска учеников"""
    print("\n=== Симуляция flow поиска учеников ===")
    
    # Имитируем ACTIVE_FLOWS
    ACTIVE_FLOWS = {}
    chat_id = "12345"
    
    # Шаг 1: Запуск flow
    print("1. Запуск flow...")
    ACTIVE_FLOWS[chat_id] = {"type": "search_student", "step": "ask_city", "data": {}}
    print(f"   Flow создан: {ACTIVE_FLOWS[chat_id]}")
    
    # Шаг 2: Обработка пустого запроса (ask_city)
    print("\n2. Обработка ask_city...")
    flow = ACTIVE_FLOWS.get(chat_id)
    if flow and flow.get("type") == "search_student" and flow.get("step") == "ask_city":
        print("   Задаем вопрос о городе")
        flow["step"] = "verify_city"
        print(f"   Шаг изменен на: {flow['step']}")
        print(f"   Flow после изменения: {flow}")
    
    # Шаг 3: Пользователь отвечает городом
    print("\n3. Пользователь отвечает городом...")
    user_response = "нижний новгород"
    print(f"   Ответ пользователя: '{user_response}'")
    
    # Проверяем текущий flow
    flow = ACTIVE_FLOWS.get(chat_id)
    print(f"   Текущий flow: {flow}")
    
    if flow and flow.get("type") == "search_student" and flow.get("step") == "verify_city":
        print("   Обрабатываем verify_city...")
        if core.Validator.city(user_response):
            print(f"   Город '{user_response}' прошел валидацию")
            flow["data"]["city"] = user_response
            flow["step"] = "ask_school"
            print(f"   Шаг изменен на: {flow['step']}")
            print(f"   Flow после изменения: {flow}")
        else:
            print(f"   Город '{user_response}' НЕ прошел валидацию")
    else:
        print(f"   ❌ ОШИБКА: Неверный flow или шаг!")
        print(f"   Ожидалось: type='search_student', step='verify_city'")
        print(f"   Получено: {flow}")

if __name__ == "__main__":
    test_city_validation()
    test_flow_simulation()
