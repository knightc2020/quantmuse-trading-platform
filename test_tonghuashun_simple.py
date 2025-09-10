#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的同花顺API测试脚本
用于验证连接和基本功能
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_tonghuashun_basic():
    """Basic TongHuaShun connection test"""
    print("=" * 60)
    print("         TongHuaShun iFinD API Basic Test")
    print("=" * 60)
    
    # Check environment variables
    user_id = os.getenv('THS_USER_ID')
    password = os.getenv('THS_PASSWORD')
    
    print(f"Environment Variables Check:")
    print(f"  THS_USER_ID: {'SET' if user_id else 'NOT SET'} ({user_id if user_id else 'N/A'})")
    print(f"  THS_PASSWORD: {'SET' if password else 'NOT SET'} ({'***' if password else 'N/A'})")
    print()
    
    if not user_id or not password:
        print("[ERROR] Environment variables not properly set! Please check .env file")
        return False
    
    # Test importing iFinD module
    try:
        print("Testing iFinD Python module import...")
        import iFinDPy as THS
        print("[SUCCESS] iFinD Python module imported successfully")
    except ImportError as e:
        print(f"[ERROR] iFinD Python module import failed: {e}")
        print("Please ensure:")
        print("1. TongHuaShun iFinD terminal is installed")
        print("2. Python API package is properly installed")
        print("3. Related DLL files are in system path")
        return False
    
    # Test login
    try:
        print(f"\nTesting login (user: {user_id})...")
        result = THS.THS_iFinDLogin(user_id, password)
        
        print(f"Login result code: {result}")
        
        if result == 0:
            print("[SUCCESS] TongHuaShun iFinD login successful")
            login_success = True
        else:
            print(f"[ERROR] TongHuaShun iFinD login failed")
            print(f"Error code: {result}")
            print("Common error codes:")
            print("  -201: Account or password incorrect")
            print("  -202: Account locked")
            print("  -203: Account expired")
            print("  -301: Network connection failed")
            login_success = False
            
    except Exception as e:
        print(f"[ERROR] Login process exception: {e}")
        login_success = False
    
    if not login_success:
        print("\nSuggestions:")
        print("1. Ensure iFinD terminal is running and logged in")
        print("2. Check username and password are correct")
        print("3. Confirm account has API access permissions")
        print("4. Check network connection")
        return False
    
    # Test basic API functions
    print("\nTesting basic API functions...")
    
    # Test 1: Get basic data
    try:
        print("Test 1: Getting stock basic info...")
        result = THS.THS_BasicData('000001.SZ', 'ths_stock_short_name_stock', 'Exchange:SSE,SZSE')
        print(f"Result: {result}")
        
        if result and result[0] == 0:
            print("[SUCCESS] Basic data API call successful")
            if result[1]:
                print(f"Got data: {result[1]}")
        else:
            print(f"[ERROR] Basic data API call failed (error code: {result[0] if result else 'None'})")
            
    except Exception as e:
        print(f"[ERROR] Basic data API exception: {e}")
    
    # Test 2: Get history quotes (simplest call)
    try:
        print("\nTest 2: Getting historical quotes...")
        # Use an earlier date that definitely has data
        result = THS.THS_HistoryQuotes('000001.SZ', 'close', '', '2025-08-01', '2025-08-01')
        print(f"Result code: {result[0] if result else 'None'}")
        
        if result and result[0] == 0:
            print("[SUCCESS] History quotes API call successful")
            if result[1]:
                print(f"Got data points: {len(result[1])}")
                if len(result[1]) > 0:
                    print(f"Sample data: {result[1][0]}")
        else:
            print(f"[ERROR] History quotes API call failed (error code: {result[0] if result else 'None'})")
            
    except Exception as e:
        print(f"[ERROR] History quotes API exception: {e}")
    
    # Logout
    try:
        THS.THS_iFinDLogout()
        print("\n[SUCCESS] Logged out from TongHuaShun iFinD")
    except Exception as e:
        print(f"\n[WARNING] Logout exception: {e}")
    
    print("=" * 60)
    print("Test completed")
    print("=" * 60)
    
    return login_success

if __name__ == "__main__":
    success = test_tonghuashun_basic()
    if success:
        print("\n[SUCCESS] TongHuaShun API basic test passed!")
        print("Now you can use data synchronization features.")
    else:
        print("\n[WARNING] TongHuaShun API test failed, please check according to above suggestions.")