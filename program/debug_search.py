#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import database
from database import Manager, Tables
import core

def test_search():
    """Test the search functionality with the example data"""
    print("🔍 Testing search functionality...")
    
    # Test data from user's example
    test_city = "нижний новгород"
    test_school = 123
    test_grade = "10Б"
    
    print(f"📍 Test data:")
    print(f"   City: '{test_city}'")
    print(f"   School: {test_school}")
    print(f"   Grade: '{test_grade}'")
    
    # First, let's see what's actually in the database
    print("\n📊 Checking database contents...")
    try:
        with Manager.session() as session:
            # Check all users with city containing "нижний" or "Нижний"
            city_query = session.query(Tables.Users).filter(
                Tables.Users.city.like('%нижний%')
            )
            city_results = city_query.all()
            
            print(f"   Found {len(city_results)} users with city containing 'нижний':")
            for user in city_results:
                print(f"     - ID: {user.telegram_id}, City: '{user.city}', School: {user.school}, Grade: '{user.grade}', Role: '{user.role}'")
            
            # Check all users with school = 123
            school_query = session.query(Tables.Users).filter(
                Tables.Users.school == 123
            )
            school_results = school_query.all()
            
            print(f"\n   Found {len(school_results)} users with school = 123:")
            for user in school_results:
                print(f"     - ID: {user.telegram_id}, City: '{user.city}', School: {user.school}, Grade: '{user.grade}', Role: '{user.role}'")
            
            # Check all users with grade = "10Б"
            grade_query = session.query(Tables.Users).filter(
                Tables.Users.grade == "10Б"
            )
            grade_results = grade_query.all()
            
            print(f"\n   Found {len(grade_results)} users with grade = '10Б':")
            for user in grade_results:
                print(f"     - ID: {user.telegram_id}, City: '{user.city}', School: {user.school}, Grade: '{user.grade}', Role: '{user.role}'")
            
    except Exception as e:
        print(f"❌ Error querying database: {e}")
        return
    
    # Now test the case-insensitive search
    print("\n🔍 Testing case-insensitive search...")
    filter_dict = {
        "city": test_city,
        "school": test_school,
        "grade": test_grade
    }
    
    print(f"   Search filter: {filter_dict}")
    
    try:
        results = Manager.search_records_case_insensitive(Tables.Users, filter_dict)
        print(f"   Search results: {results}")
        
        if results:
            print(f"   ✅ Found {len(results)} matching records:")
            for record in results:
                print(f"     - {record}")
        else:
            print("   ❌ No records found")
            
    except Exception as e:
        print(f"❌ Error in search: {e}")
    
    # Test individual field searches
    print("\n🔍 Testing individual field searches...")
    
    # Test city search
    try:
        city_filter = {"city": test_city}
        city_results = Manager.search_records_case_insensitive(Tables.Users, city_filter)
        print(f"   City search results: {len(city_results) if city_results else 0} records")
    except Exception as e:
        print(f"❌ City search error: {e}")
    
    # Test school search
    try:
        school_filter = {"school": test_school}
        school_results = Manager.search_records_case_insensitive(Tables.Users, school_filter)
        print(f"   School search results: {len(school_results) if school_results else 0} records")
    except Exception as e:
        print(f"❌ School search error: {e}")
    
    # Test grade search
    try:
        grade_filter = {"grade": test_grade}
        grade_results = Manager.search_records_case_insensitive(Tables.Users, grade_filter)
        print(f"   Grade search results: {len(grade_results) if grade_results else 0} records")
    except Exception as e:
        print(f"❌ Grade search error: {e}")

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

if __name__ == "__main__":
    test_search()
    test_city_validation()
