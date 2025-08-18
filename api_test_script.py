#!/usr/bin/env python3
"""
Simple test script to debug Chicago Data Portal API issues
"""

import os
from dotenv import load_dotenv
from sodapy import Socrata

load_dotenv()

def test_chicago_api():
    """Test Chicago Data Portal API with different configurations."""
    
    print("🔍 Testing Chicago Data Portal API...")
    
    # Test 1: No token (public access)
    print("\n1. Testing without app token...")
    try:
        client = Socrata("data.cityofchicago.org", None)
        
        # Simple query for just 2 records
        results = client.get("ijzp-q8t2", limit=2)
        
        if results:
            print("✅ API works without token!")
            print(f"   Retrieved {len(results)} records")
            print(f"   Sample data: {results[0] if results else 'No data'}")
        else:
            print("⚠️ No data returned (but no error)")
            
    except Exception as e:
        print(f"❌ Failed without token: {e}")
    
    # Test 2: With your token
    chicago_token = os.getenv("CHICAGO_DATA_APP_TOKEN")
    if chicago_token:
        print(f"\n2. Testing with your app token (preview: {chicago_token[:10]}...)...")
        try:
            client = Socrata("data.cityofchicago.org", chicago_token)
            
            # Simple query for just 2 records
            results = client.get("ijzp-q8t2", limit=2)
            
            if results:
                print("✅ API works with your token!")
                print(f"   Retrieved {len(results)} records")
                print(f"   Sample data: {results[0] if results else 'No data'}")
            else:
                print("⚠️ No data returned (but no error)")
                
        except Exception as e:
            print(f"❌ Failed with your token: {e}")
            print("   This suggests the token may be invalid or expired")
    else:
        print("\n2. No app token found in environment")
    
    # Test 3: Alternative dataset (smaller, might work better)
    print(f"\n3. Testing with a different dataset...")
    try:
        client = Socrata("data.cityofchicago.org", None)
        
        # Try with building permits dataset (often more reliable)
        results = client.get("ydr8-5enu", limit=2)
        
        if results:
            print("✅ Alternative dataset works!")
            print(f"   Retrieved {len(results)} records from building permits")
        else:
            print("⚠️ Alternative dataset returned no data")
            
    except Exception as e:
        print(f"❌ Alternative dataset failed: {e}")
    
    # Test 4: Check if it's a date range issue
    print(f"\n4. Testing crime data with older date range...")
    try:
        client = Socrata("data.cityofchicago.org", None)
        
        # Try with a broader date range
        query = "date >= '2023-01-01T00:00:00' ORDER BY date DESC LIMIT 5"
        results = client.get("ijzp-q8t2", query=query)
        
        if results:
            print("✅ Older date range works!")
            print(f"   Retrieved {len(results)} records")
            print(f"   Latest date: {results[0].get('date', 'Unknown') if results else 'No data'}")
        else:
            print("⚠️ Older date range returned no data")
            
    except Exception as e:
        print(f"❌ Older date range failed: {e}")
    
    print(f"\n📋 RECOMMENDATIONS:")
    print(f"   • If test 1 worked: Use the API without a token for now")
    print(f"   • If test 2 failed: Your app token may be invalid - try regenerating it")
    print(f"   • If all tests failed: There may be a network or API issue")
    print(f"   • Check https://data.cityofchicago.org/ to see if the site is accessible")

if __name__ == "__main__":
    test_chicago_api()