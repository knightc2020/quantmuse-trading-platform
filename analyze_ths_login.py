#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)

def analyze_login_issue():
    """分析同花顺登录问题的可能原因"""
    
    print("=" * 60)
    print("TongHuaShun Login Issue Analysis")
    print("=" * 60)
    
    print("\n1. ERROR CODE ANALYSIS:")
    print("   -201: This typically indicates:")
    print("   - Session conflict (already logged in elsewhere)")
    print("   - License limitation (concurrent user limit)")
    print("   - API quota exceeded")
    print("   - Time-based access restriction")
    
    print("\n2. TESTING DIFFERENT LOGIN SCENARIOS:")
    
    scenarios = [
        ("Basic import test", test_import),
        ("Single login test", test_single_login),
        ("Login-logout cycle", test_login_cycle),
        ("Delayed retry test", test_delayed_retry),
    ]
    
    for desc, test_func in scenarios:
        print(f"\n--- {desc} ---")
        try:
            result = test_func()
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")

def test_import():
    """测试模块导入"""
    try:
        import iFinDPy as THS
        print("  iFinDPy import: SUCCESS")
        return "OK"
    except Exception as e:
        print(f"  iFinDPy import failed: {e}")
        return "FAIL"

def test_single_login():
    """测试单次登录"""
    try:
        import iFinDPy as THS
        
        user_id = os.getenv("THS_USER_ID")
        password = os.getenv("THS_PASSWORD")
        
        if not user_id or not password:
            return "CREDENTIALS_MISSING"
        
        print(f"  Attempting login with user: {user_id}")
        result = THS.THS_iFinDLogin(user_id, password)
        print(f"  Login result code: {result}")
        
        if result == 0:
            print("  Login successful, attempting logout...")
            THS.THS_iFinDLogout()
            return "LOGIN_OK"
        else:
            return f"LOGIN_FAILED_CODE_{result}"
            
    except Exception as e:
        return f"EXCEPTION: {e}"

def test_login_cycle():
    """测试登录-登出循环"""
    try:
        import iFinDPy as THS
        
        user_id = os.getenv("THS_USER_ID")
        password = os.getenv("THS_PASSWORD")
        
        results = []
        for i in range(3):
            print(f"  Cycle {i+1}:")
            
            # Login
            login_result = THS.THS_iFinDLogin(user_id, password)
            print(f"    Login: {login_result}")
            
            if login_result == 0:
                # Quick test
                try:
                    test_data = THS.THS_BasicData('000001.SZ', 'ths_stock_short_name_stock')
                    print(f"    Test API: {test_data}")
                except:
                    print("    Test API: FAILED")
                
                # Logout
                THS.THS_iFinDLogout()
                print("    Logout: Done")
            
            results.append(login_result)
            
            if i < 2:  # Wait between cycles
                print("    Waiting 2 seconds...")
                time.sleep(2)
        
        return f"RESULTS: {results}"
        
    except Exception as e:
        return f"EXCEPTION: {e}"

def test_delayed_retry():
    """测试延迟重试"""
    try:
        import iFinDPy as THS
        
        user_id = os.getenv("THS_USER_ID")
        password = os.getenv("THS_PASSWORD")
        
        delays = [0, 1, 3, 5]  # Different delay times
        results = []
        
        for delay in delays:
            if delay > 0:
                print(f"  Waiting {delay} seconds...")
                time.sleep(delay)
            
            login_result = THS.THS_iFinDLogin(user_id, password)
            print(f"  Login after {delay}s delay: {login_result}")
            results.append((delay, login_result))
            
            if login_result == 0:
                THS.THS_iFinDLogout()
                break
                
        return f"DELAY_TEST: {results}"
        
    except Exception as e:
        return f"EXCEPTION: {e}"

def main():
    """主函数"""
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    analyze_login_issue()
    
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS:")
    print("1. Check if another session is active")
    print("2. Verify API quota/license status")
    print("3. Try login during different time periods")
    print("4. Contact TongHuaShun support for -201 error details")
    print("5. Consider implementing session management")
    print("=" * 60)

if __name__ == "__main__":
    main()