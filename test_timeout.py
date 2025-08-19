#!/usr/bin/env python3

from sodapy import Socrata
import requests
import time
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def test_chicago_timeout():
    """Test Chicago crime API timeout behavior."""
    print("Testing Chicago Crime API timeout behavior...")
    
    # Initialize client with proper timeout
    client = Socrata("data.cityofchicago.org", os.getenv("CHICAGO_DATA_APP_TOKEN"))
    client.session.timeout = 30  # Set 30 second timeout
    
    print(f"Session timeout set to: {client.session.timeout} seconds")
    
    # Test with a simple query first
    dataset_id = "ijzp-q8t2"
    
    # Build a query for last 3 days
    now = datetime.now()
    start_date = (now - timedelta(days=3)).strftime('%Y-%m-%dT00:00:00')
    
    query = f"SELECT date, primary_type, description, block WHERE date >= '{start_date}' ORDER BY date DESC LIMIT 10"
    
    print(f"Testing query: {query}")
    print()
    
    start_time = time.time()
    try:
        results = client.get(dataset_id, query=query)
        query_time = time.time() - start_time
        print(f"✅ Query successful! Completed in {query_time:.2f} seconds")
        print(f"Retrieved {len(results)} records")
        
        if results:
            print("\nFirst record:")
            print(f"  Date: {results[0].get('date', 'N/A')}")
            print(f"  Crime: {results[0].get('primary_type', 'N/A')}")
            print(f"  Location: {results[0].get('block', 'N/A')}")
            
    except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout) as e:
        query_time = time.time() - start_time
        print(f"❌ Timeout occurred after {query_time:.2f} seconds")
        print(f"Timeout type: {type(e).__name__}")
        print(f"Error: {e}")
        
    except Exception as e:
        query_time = time.time() - start_time
        print(f"❌ Other error after {query_time:.2f} seconds")
        print(f"Error type: {type(e).__name__}")
        print(f"Error: {e}")
        
        if "timeout" in str(e).lower():
            print("⚠️  This appears to be a timeout-related error")

if __name__ == "__main__":
    test_chicago_timeout()