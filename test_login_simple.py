#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_service.tonghuashun_client import TonghuasunDataClient
import time
import logging

logging.basicConfig(level=logging.WARNING)

def main():
    """简单的登录稳定性测试"""
    
    print("TongHuaShun Login Stability Test")
    print("=" * 50)
    
    results = []
    
    for i in range(5):
        print(f"\nRound {i+1}/5:")
        
        try:
            client = TonghuasunDataClient()
            
            # Test login
            login_ok = client.login()
            print(f"  Login: {'OK' if login_ok else 'FAILED'}")
            
            if login_ok:
                # Test logout  
                client.logout()
                print(f"  Logout: OK")
                results.append(True)
            else:
                results.append(False)
                
        except Exception as e:
            print(f"  Error: {e}")
            results.append(False)
        
        # Wait between attempts
        if i < 4:
            time.sleep(2)
    
    print("\n" + "=" * 50)
    success_rate = sum(results) / len(results) * 100
    print(f"Success Rate: {sum(results)}/{len(results)} ({success_rate:.1f}%)")
    print(f"Results: {results}")
    
    if success_rate >= 80:
        print("Status: STABLE")
        return True
    elif success_rate >= 60:
        print("Status: MODERATE") 
        return True
    else:
        print("Status: UNSTABLE")
        return False

if __name__ == "__main__":
    main()