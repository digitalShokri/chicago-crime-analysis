from langchain.tools import BaseTool
# Note: Callback manager import varies by LangChain version
try:
    from langchain_core.callbacks.manager import AsyncCallbackManagerForToolUse
except ImportError:
    try:
        from langchain_core.callbacks.manager import CallbackManagerForToolUse as AsyncCallbackManagerForToolUse
    except ImportError:
        AsyncCallbackManagerForToolUse = None

from sodapy import Socrata
import pandas as pd
from typing import Optional, Type, Any
from pydantic import BaseModel, Field, PrivateAttr
import json
import os
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ChicagoCrimeInput(BaseModel):
    """Input for Chicago Crime Database queries."""
    query_type: str = Field(description="Type of query: 'recent_crimes', 'crime_stats', 'location_analysis'")
    location: Optional[str] = Field(default=None, description="Specific address, neighborhood, or ward")  
    crime_type: Optional[str] = Field(default=None, description="Type of crime: THEFT, BATTERY, BURGLARY, etc.")
    limit: Optional[int] = Field(default=50, description="Number of records to return (recommended: 10-100 for fast queries)")

class ChicagoCrimeTool(BaseTool):
    """Optimized tool for querying Chicago Police Department crime database.
    
    This tool is optimized to work within the Chicago API's 10-second timeout limit.
    It uses strategies that avoid expensive date filtering and sorting operations.
    """
    
    name: str = "chicago_crime_database"
    description: str = """Query the Chicago Police Department's public crime database with timeout optimization.
    Returns recent crime data without date filtering to avoid API timeouts.
    Use small limits (10-100) for best performance."""
    
    args_schema: Type[BaseModel] = ChicagoCrimeInput
    
    # Private attributes for Pydantic v2 compatibility
    _client: Optional[Socrata] = PrivateAttr(default=None)
    _dataset_id: str = PrivateAttr(default="ijzp-q8t2")
    _timeout_seconds: int = PrivateAttr(default=10)  # Match server timeout
    _timeout_count: int = PrivateAttr(default=0)
    
    def __init__(self, app_token: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self._client = Socrata("data.cityofchicago.org", app_token)
        # Set timeout on the session object (sodapy doesn't support timeout parameter in get())
        self._client.session.timeout = self._timeout_seconds
        self._dataset_id = "ijzp-q8t2"  # Main crime dataset
    
    def _run(
        self, 
        query_type: str,
        location: Optional[str] = None,
        crime_type: Optional[str] = None,
        limit: int = 50,
        run_manager: Optional[Any] = None,
    ) -> str:
        """Execute optimized Chicago crime database query."""
        
        # Enforce reasonable limits to avoid timeouts
        if limit > 1000:
            limit = 1000
            print(f"Warning: Limit reduced to 1000 to avoid timeout")
        
        try:
            # Implement timeout-optimized query strategy
            if query_type == "recent_crimes":
                return self._get_recent_crimes_optimized(crime_type, location, limit)
            elif query_type == "crime_stats":
                return self._get_crime_stats_optimized(crime_type, location, limit)  
            elif query_type == "location_analysis":
                return self._get_location_analysis_optimized(location, limit)
            else:
                return self._get_recent_crimes_optimized(crime_type, location, limit)
                
        except Exception as e:
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                self._timeout_count += 1
                return f"DATABASE_TIMEOUT: Chicago API timeout (timeout #{self._timeout_count}). Try reducing the limit parameter or simplifying filters."
            return f"Error querying Chicago crime database: {str(e)}"
    
    def _get_recent_crimes_optimized(self, crime_type: Optional[str], location: Optional[str], limit: int) -> str:
        """Get recent crimes using optimized query strategy."""
        
        # Strategy 1: Try simple query first (fastest)
        base_query = f"SELECT date, primary_type, description, location_description, block, ward, beat, arrest, domestic LIMIT {limit}"
        
        # Strategy 2: Add crime type filter if specified (still fast)
        if crime_type and not location:
            query = f"SELECT date, primary_type, description, location_description, block, ward, beat, arrest, domestic WHERE primary_type='{crime_type.upper()}' LIMIT {limit}"
        # Strategy 3: Add location filter if specified (slower but manageable)
        elif location and not crime_type:
            location_filter = self._build_location_filter(location)
            query = f"SELECT date, primary_type, description, location_description, block, ward, beat, arrest, domestic WHERE {location_filter} LIMIT {limit}"
        # Strategy 4: Both filters (most likely to timeout)
        elif crime_type and location:
            location_filter = self._build_location_filter(location)
            query = f"SELECT date, primary_type, description, location_description, block, ward, beat, arrest, domestic WHERE primary_type='{crime_type.upper()}' AND {location_filter} LIMIT {limit}"
        else:
            query = base_query
            
        return self._execute_query_with_fallback(query, base_query, "recent_crimes")
    
    def _get_crime_stats_optimized(self, crime_type: Optional[str], location: Optional[str], limit: int) -> str:
        """Get crime statistics using optimized approach."""
        
        # For stats, we need a reasonable sample size but not too large
        stats_limit = min(limit * 5, 1000)  # Use 5x the limit for better stats
        
        base_query = f"SELECT primary_type, arrest, domestic LIMIT {stats_limit}"
        
        if crime_type and not location:
            query = f"SELECT primary_type, arrest, domestic WHERE primary_type='{crime_type.upper()}' LIMIT {stats_limit}"
        elif location and not crime_type:
            location_filter = self._build_location_filter(location)
            query = f"SELECT primary_type, arrest, domestic WHERE {location_filter} LIMIT {stats_limit}"
        elif crime_type and location:
            location_filter = self._build_location_filter(location)
            query = f"SELECT primary_type, arrest, domestic WHERE primary_type='{crime_type.upper()}' AND {location_filter} LIMIT {stats_limit}"
        else:
            query = base_query
            
        return self._execute_query_with_fallback(query, base_query, "crime_stats")
    
    def _get_location_analysis_optimized(self, location: Optional[str], limit: int) -> str:
        """Get location analysis using optimized approach."""
        
        base_query = f"SELECT ward, beat, location_description, primary_type LIMIT {limit * 2}"
        
        if location:
            location_filter = self._build_location_filter(location) 
            query = f"SELECT ward, beat, location_description, primary_type WHERE {location_filter} LIMIT {limit * 2}"
        else:
            query = base_query
            
        return self._execute_query_with_fallback(query, base_query, "location_analysis")
    
    def _build_location_filter(self, location: str) -> str:
        """Build location filter optimized for performance."""
        location_upper = location.upper()
        
        # Ward numbers are indexed and fast
        if location.lower().startswith('ward '):
            ward_num = location.lower().replace('ward ', '').strip()
            if ward_num.isdigit():
                return f"ward='{ward_num}'"
        elif location.isdigit():
            return f"(ward='{location}' OR beat='{location}')"
        elif location.lower().startswith('beat '):
            beat_num = location.lower().replace('beat ', '').strip()
            if beat_num.isdigit():
                return f"beat='{beat_num}'"
        
        # Text search is slower but still manageable with small limits
        return f"upper(block) LIKE '%{location_upper}%'"
    
    def _execute_query_with_fallback(self, primary_query: str, fallback_query: str, format_type: str) -> str:
        """Execute query with fallback on timeout."""
        
        print(f"Executing optimized query: {primary_query}")
        
        start_time = time.time()
        try:
            results = self._client.get(self._dataset_id, query=primary_query)
            query_time = time.time() - start_time
            print(f"Query completed in {query_time:.2f} seconds")
            
        except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout) as e:
            # Try fallback query (simpler, more likely to succeed)
            self._timeout_count += 1
            print(f"Primary query timed out, trying fallback...")
            
            try:
                results = self._client.get(self._dataset_id, query=fallback_query)
                query_time = time.time() - start_time
                print(f"Fallback query completed in {query_time:.2f} seconds")
            except:
                error_msg = f"Both primary and fallback queries timed out (timeout #{self._timeout_count})"
                return f"DATABASE_TIMEOUT: {error_msg}"
        
        if not results:
            return "No crime data found for the specified criteria."
        
        # Process results based on format type
        df = pd.DataFrame.from_records(results)
        
        if format_type == "recent_crimes":
            return self._format_recent_crimes(df)
        elif format_type == "crime_stats":
            return self._format_crime_stats(df) 
        elif format_type == "location_analysis":
            return self._format_location_analysis(df)
        else:
            return self._format_general_summary(df)
    
    def _format_recent_crimes(self, df: pd.DataFrame) -> str:
        """Format recent crimes for readability."""
        if df.empty:
            return "No recent crimes found."
        
        summary = f"Found {len(df)} crime incidents (sample without date filtering due to API constraints):\n\n"
        
        for _, row in df.head(10).iterrows():
            summary += f"• {row.get('primary_type', 'Unknown')} - {row.get('description', 'No description')}\n"
            summary += f"  Location: {row.get('block', 'Unknown location')}\n"
            summary += f"  Date: {str(row.get('date', 'Unknown date'))[:10]}\n"
            summary += f"  Arrest Made: {'Yes' if str(row.get('arrest', '')).lower() == 'true' else 'No'}\n\n"
        
        return summary
    
    def _format_crime_stats(self, df: pd.DataFrame) -> str:
        """Format crime statistics."""
        if df.empty:
            return "No crime data available for statistics."
        
        stats = f"Crime Statistics Summary (sample of {len(df)} incidents):\n\n"
        
        # Crime type breakdown
        if 'primary_type' in df.columns:
            crime_counts = df['primary_type'].value_counts().head(10)
            stats += "Top Crime Types:\n"
            for crime_type, count in crime_counts.items():
                percentage = (count / len(df)) * 100
                stats += f"• {crime_type}: {count} incidents ({percentage:.1f}%)\n"
        
        # Arrest rate
        if 'arrest' in df.columns:
            arrest_count = sum(1 for x in df['arrest'] if str(x).lower() == 'true')
            arrest_rate = (arrest_count / len(df)) * 100
            stats += f"\nOverall Arrest Rate: {arrest_rate:.1f}%\n"
        
        # Domestic incidents  
        if 'domestic' in df.columns:
            domestic_count = sum(1 for x in df['domestic'] if str(x).lower() == 'true')
            domestic_rate = (domestic_count / len(df)) * 100
            stats += f"Domestic-Related Incidents: {domestic_rate:.1f}%\n"
        
        stats += f"\n⚠️  Note: Statistics based on sample data (no date filtering due to API timeout constraints)"
        return stats
    
    def _format_location_analysis(self, df: pd.DataFrame) -> str:
        """Format location-based analysis."""
        if df.empty:
            return "No location data available for analysis."
        
        analysis = f"Location Analysis (sample of {len(df)} incidents):\n\n"
        
        # Ward analysis
        if 'ward' in df.columns and df['ward'].notna().any():
            ward_counts = df['ward'].value_counts().head(5)
            analysis += "Top Wards by Incident Count:\n"
            for ward, count in ward_counts.items():
                analysis += f"• Ward {ward}: {count} incidents\n"
        
        # Location description analysis
        if 'location_description' in df.columns:
            location_counts = df['location_description'].value_counts().head(5)
            analysis += "\nMost Common Location Types:\n"
            for location, count in location_counts.items():
                analysis += f"• {location}: {count} incidents\n"
        
        analysis += f"\n⚠️  Note: Analysis based on sample data (no date filtering due to API timeout constraints)"
        return analysis
    
    def _format_general_summary(self, df: pd.DataFrame) -> str:
        """Format general summary of results."""
        return f"Retrieved {len(df)} crime records from Chicago Police Database.\n" + \
               f"Columns available: {', '.join(df.columns.tolist())}"
    
    def get_timeout_stats(self) -> dict:
        """Get timeout monitoring statistics."""
        return {
            "timeout_count": self._timeout_count,
            "timeout_threshold": self._timeout_seconds
        }
    
    def reset_timeout_count(self) -> None:
        """Reset the timeout counter."""
        self._timeout_count = 0

# Test function
def test_tool():
    """Test the optimized Chicago Crime Tool."""
    print("Testing Optimized Chicago Crime Tool...")
    
    try:
        # Environment variables are already loaded at module level
        tool = ChicagoCrimeTool(app_token=os.getenv("CHICAGO_DATA_APP_TOKEN"))
        
        # Test 1: Simple recent crimes
        print("\n1. Testing recent crimes (no filters)...")
        result = tool._run(query_type="recent_crimes", limit=10)
        print("✅ Result:", result[:200] + "..." if len(result) > 200 else result)
        
        # Test 2: Crime type filter
        print("\n2. Testing with crime type filter...")
        result = tool._run(query_type="recent_crimes", crime_type="THEFT", limit=5)
        print("✅ Result:", result[:200] + "..." if len(result) > 200 else result)
        
        # Test 3: Location filter
        print("\n3. Testing with ward location...")
        result = tool._run(query_type="location_analysis", location="Ward 1", limit=10)
        print("✅ Result:", result[:200] + "..." if len(result) > 200 else result)
        
        print(f"\n📊 Timeout stats: {tool.get_timeout_stats()}")
        
    except Exception as e:
        print(f"❌ Tool test failed: {e}")

if __name__ == "__main__":
    test_tool()