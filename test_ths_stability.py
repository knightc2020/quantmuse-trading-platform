#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_service.tonghuashun_client import TonghuasunDataClient
import time
import logging

logging.basicConfig(level=logging.INFO)

def test_client_stability():
    """测试同花顺客户端稳定性"""
    
    print("=" * 60)
    print("TongHuaShun Client Stability Test")
    print("=" * 60)
    
    # Test multiple login/logout cycles
    client = TonghuasunDataClient()
    
    test_results = []
    
    for i in range(5):
        print(f"\n--- Test Round {i+1} ---")
        
        try:
            # Test login
            login_success = client.login()
            print(f"Login attempt {i+1}: {'SUCCESS' if login_success else 'FAILED'}")
            
            if login_success:
                # Test basic API call
                try:
                    # Test getting stock basic info
                    stocks = ['000001.SZ', '000002.SZ']
                    for stock in stocks:
                        result = client.get_basic_data(stock, 'ths_stock_short_name_stock')
                        print(f"  API test {stock}: {'OK' if result else 'FAILED'}")
                        
                        if i == 0:  # Only on first round to avoid too many calls
                            break
                            
                except Exception as e:
                    print(f"  API test failed: {e}")
                
                # Test logout
                client.logout()
                print(f"Logout: SUCCESS")
                
            test_results.append(login_success)
            
        except Exception as e:
            print(f"Round {i+1} exception: {e}")
            test_results.append(False)
        
        # Wait between tests
        if i < 4:
            print("Waiting 3 seconds...")
            time.sleep(3)
    
    print("\n" + "=" * 60)
    print("STABILITY TEST RESULTS:")
    print(f"Success rate: {sum(test_results)}/{len(test_results)} ({sum(test_results)/len(test_results)*100:.1f}%)")
    print(f"Results: {test_results}")
    
    return test_results

def test_data_download():
    """测试实际数据下载"""
    
    print("\n" + "=" * 60)
    print("Data Download Test")
    print("=" * 60)
    
    client = TonghuasunDataClient()
    
    try:
        if not client.login():
            print("Login failed, cannot test data download")
            return False
            
        print("Testing historical data download...")
        
        # Test downloading a small amount of historical data
        test_stocks = ['000001.SZ', '000002.SZ']
        start_date = '2025-09-01'
        end_date = '2025-09-06'
        
        for stock in test_stocks:
            print(f"\nTesting {stock}...")
            try:
                # This is a placeholder - need to implement actual data download method
                result = client.get_history_data(stock, start_date, end_date)
                print(f"  Download result: {'SUCCESS' if result else 'FAILED'}")
                
                if result:
                    print(f"  Data sample: {str(result)[:100]}...")
                
            except Exception as e:
                print(f"  Download error: {e}")
        
        client.logout()
        return True
        
    except Exception as e:
        print(f"Data download test failed: {e}")
        return False

def main():
    """主测试函数"""
    
    # Test 1: Client stability
    stability_results = test_client_stability()
    
    # Test 2: Data download capability
    if any(stability_results):
        download_success = test_data_download()
    else:
        print("\nSkipping data download test - login unstable")
        download_success = False
    
    # Summary
    print("\n" + "=" * 60)
    print("OVERALL SUMMARY:")
    success_rate = sum(stability_results) / len(stability_results) * 100
    print(f"Login stability: {success_rate:.1f}%")
    print(f"Data download: {'TESTED' if download_success else 'NOT_TESTED'}")
    
    if success_rate >= 80:
        print("Status: STABLE - Ready for production use")
    elif success_rate >= 60:
        print("Status: MODERATE - Usable with retry logic")
    else:
        print("Status: UNSTABLE - Needs investigation")
    
    print("=" * 60)

if __name__ == "__main__":
    main()