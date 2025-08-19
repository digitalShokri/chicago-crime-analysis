#!/usr/bin/env python3

from sodapy import Socrata
import requests
import time
import os
from datetime import datetime, timedelta

def test_query_strategies():
    """Test different query strategies to avoid timeouts."""
    print("Testing optimized query strategies for Chicago Crime API...")
    
    client = Socrata("data.cityofchicago.org", os.getenv("CHICAGO_DATA_APP_TOKEN"))
    client.session.timeout = 10  # Match server timeout
    dataset_id = "ijzp-q8t2"
    
    now = datetime.now()
    
    strategies = [
        {
            "name": "Very small limit (5 records)",
            "query": f"SELECT date, primary_type, block LIMIT 5"
        },
        {
            "name": "Last 1 day, small limit",
            "query": f"SELECT date, primary_type, block WHERE date >= '{(now - timedelta(days=1)).strftime('%Y-%m-%dT00:00:00')}' ORDER BY date DESC LIMIT 10"
        },
        {
            "name": "Last 3 days, very small limit",
            "query": f"SELECT date, primary_type, block WHERE date >= '{(now - timedelta(days=3)).strftime('%Y-%m-%dT00:00:00')}' ORDER BY date DESC LIMIT 5"
        },
        {
            "name": "Specific crime type filter",
            "query": f"SELECT date, primary_type, block WHERE primary_type='THEFT' AND date >= '{(now - timedelta(days=1)).strftime('%Y-%m-%dT00:00:00')}' ORDER BY date DESC LIMIT 10"
        },
        {
            "name": "Just count records (fastest)",
            "query": f"SELECT COUNT(*) WHERE date >= '{(now - timedelta(days=3)).strftime('%Y-%m-%dT00:00:00')}'"
        }
    ]
    
    for strategy in strategies:
        print(f"\n🧪 Testing: {strategy['name']}")
        print(f"Query: {strategy['query']}")
        
        start_time = time.time()
        try:
            results = client.get(dataset_id, query=strategy['query'])
            query_time = time.time() - start_time
            print(f"✅ SUCCESS in {query_time:.2f}s - Retrieved {len(results)} records")
            
            if results and len(results) > 0:
                print(f"   Sample: {results[0]}")
                
        except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout) as e:
            query_time = time.time() - start_time
            print(f"❌ TIMEOUT after {query_time:.2f}s - {type(e).__name__}")
            
        except Exception as e:
            query_time = time.time() - start_time  
            print(f"❌ ERROR after {query_time:.2f}s - {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_query_strategies()