from langchain.tools import BaseTool
# Note: Callback manager import varies by LangChain version
# For compatibility, we'll make it optional
try:
    from langchain_core.callbacks.manager import AsyncCallbackManagerForToolUse
except ImportError:
    try:
        from langchain_core.callbacks.manager import CallbackManagerForToolUse as AsyncCallbackManagerForToolUse
    except ImportError:
        # Fallback for different LangChain versions
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
    query_type: str = Field(description="Type of query: 'recent_crimes', 'crime_stats', 'location_analysis', 'trend_analysis'")
    location: Optional[str] = Field(default=None, description="Specific address, neighborhood, or ward")
    crime_type: Optional[str] = Field(default=None, description="Type of crime: THEFT, BATTERY, BURGLARY, etc.")
    date_range: Optional[str] = Field(default="last_3_days", description="Time period: last_3_days, last_7_days, last_30_days, last_year, or custom YYYY-MM-DD format")
    limit: Optional[int] = Field(default=100, description="Number of records to return (max 50000)")

class ChicagoCrimeTool(BaseTool):
    """Tool for querying Chicago Police Department crime database."""
    
    name: str = "chicago_crime_database"
    description: str = """Query the Chicago Police Department's public crime database. 
    Can search for recent crimes, analyze crime statistics, examine location-based patterns, 
    and identify trends. Data includes crime type, location, date, and other incident details."""
    
    args_schema: Type[BaseModel] = ChicagoCrimeInput
    
    # Private attributes for Pydantic v2 compatibility
    _client: Optional[Socrata] = PrivateAttr(default=None)
    _dataset_id: str = PrivateAttr(default="ijzp-q8t2")
    _timeout_seconds: int = PrivateAttr(default=30)
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
        date_range: str = "last_3_days",
        limit: int = 100,
        run_manager: Optional[Any] = None,  # Made generic to handle different LangChain versions
    ) -> str:
        """Execute the Chicago crime database query."""
        
        try:
            # Build SoQL query based on parameters
            where_clauses = []
            
            # Date filtering - dynamic dates based on current time
            now = datetime.now()
            if date_range == "last_3_days":
                start_date = (now - timedelta(days=3)).strftime('%Y-%m-%dT00:00:00')
                where_clauses.append(f"date >= '{start_date}'")
            elif date_range == "last_7_days":
                start_date = (now - timedelta(days=7)).strftime('%Y-%m-%dT00:00:00')
                where_clauses.append(f"date >= '{start_date}'")
            elif date_range == "last_30_days":
                start_date = (now - timedelta(days=30)).strftime('%Y-%m-%dT00:00:00')
                where_clauses.append(f"date >= '{start_date}'")
            elif date_range == "last_year":
                start_date = (now - timedelta(days=365)).strftime('%Y-%m-%dT00:00:00')
                where_clauses.append(f"date >= '{start_date}'")
            elif date_range and "-" in date_range:  # Custom date format YYYY-MM-DD
                try:
                    # Validate date format
                    datetime.strptime(date_range, '%Y-%m-%d')
                    where_clauses.append(f"date >= '{date_range}T00:00:00'")
                except ValueError:
                    print(f"Warning: Invalid date format '{date_range}', using last_3_days instead")
                    start_date = (now - timedelta(days=3)).strftime('%Y-%m-%dT00:00:00')
                    where_clauses.append(f"date >= '{start_date}'")
            
            # Crime type filtering
            if crime_type:
                where_clauses.append(f"primary_type='{crime_type.upper()}'")
            
            # Location filtering
            if location:
                location_upper = location.upper()
                
                # Check if location looks like a ward number (e.g., "Ward 1", "1", "43")
                if location.lower().startswith('ward '):
                    ward_num = location.lower().replace('ward ', '').strip()
                    if ward_num.isdigit():
                        where_clauses.append(f"ward='{ward_num}'")
                    else:
                        # If not a valid ward number, search in block text
                        where_clauses.append(f"upper(block) LIKE '%{location_upper}%'")
                        
                # Check if location is just a number (could be ward or beat)
                elif location.isdigit():
                    where_clauses.append(f"(ward='{location}' OR beat='{location}')")
                    
                # Check if location looks like a beat number (e.g., "Beat 1234")
                elif location.lower().startswith('beat '):
                    beat_num = location.lower().replace('beat ', '').strip()
                    if beat_num.isdigit():
                        where_clauses.append(f"beat='{beat_num}'")
                    else:
                        # If not a valid beat number, search in block text
                        where_clauses.append(f"upper(block) LIKE '%{location_upper}%'")
                        
                # For neighborhood names (like "Lincoln Park", "Loop", etc.), search in block text only
                else:
                    where_clauses.append(f"upper(block) LIKE '%{location_upper}%'")
            
            # Build the query
            select_clause = "SELECT date, primary_type, description, location_description, block, ward, beat, latitude, longitude, arrest, domestic"
            where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            order_clause = "ORDER BY date DESC"
            limit_clause = f"LIMIT {min(limit, 50000)}"
            
            # Combine query parts
            query_parts = [select_clause, where_clause, order_clause, limit_clause]
            query = " ".join(filter(None, query_parts))
            
            print(f"Executing query: {query}")  # Debug output
            
            # Execute query with timeout monitoring
            start_time = time.time()
            try:
                # Timeout is set on client.session.timeout in __init__
                results = self._client.get(self._dataset_id, query=query)
                query_time = time.time() - start_time
                print(f"Query completed in {query_time:.2f} seconds")
                
            except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout) as e:
                self._timeout_count += 1
                query_time = time.time() - start_time
                error_msg = f"Chicago API timeout after {query_time:.2f} seconds (timeout #{self._timeout_count}). Skipping LLM processing to avoid incomplete data."
                print(error_msg)
                return f"DATABASE_TIMEOUT: {error_msg}"
            except Exception as e:
                query_time = time.time() - start_time
                if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                    self._timeout_count += 1
                    error_msg = f"Chicago API timeout after {query_time:.2f} seconds (timeout #{self._timeout_count}). Skipping LLM processing."
                    print(error_msg)
                    return f"DATABASE_TIMEOUT: {error_msg}"
                raise e
            
            if not results:
                return "No crime data found for the specified criteria."
            
            # Process results based on query type
            df = pd.DataFrame.from_records(results)
            
            if query_type == "recent_crimes":
                return self._format_recent_crimes(df)
            elif query_type == "crime_stats":
                return self._format_crime_stats(df)
            elif query_type == "location_analysis":
                return self._format_location_analysis(df)
            elif query_type == "trend_analysis":
                return self._format_trend_analysis(df)
            else:
                return self._format_general_summary(df)
                
        except Exception as e:
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                self._timeout_count += 1
                return f"DATABASE_TIMEOUT: Chicago API timeout (timeout #{self._timeout_count}). Skipping LLM processing."
            return f"Error querying Chicago crime database: {str(e)}"
    
    def get_timeout_stats(self) -> dict:
        """Get timeout monitoring statistics."""
        return {
            "timeout_count": self._timeout_count,
            "timeout_threshold": self._timeout_seconds
        }
    
    def reset_timeout_count(self) -> None:
        """Reset the timeout counter."""
        self._timeout_count = 0
    
    def _format_recent_crimes(self, df: pd.DataFrame) -> str:
        """Format recent crimes for readability."""
        if df.empty:
            return "No recent crimes found."
        
        summary = f"Found {len(df)} recent crime incidents:\n\n"
        
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
        
        stats = f"Crime Statistics Summary ({len(df)} total incidents):\n\n"
        
        # Crime type breakdown
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
        
        return stats
    
    def _format_location_analysis(self, df: pd.DataFrame) -> str:
        """Format location-based analysis."""
        if df.empty:
            return "No location data available for analysis."
        
        analysis = f"Location Analysis ({len(df)} incidents):\n\n"
        
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
        
        return analysis
    
    def _format_trend_analysis(self, df: pd.DataFrame) -> str:
        """Format trend analysis."""
        if df.empty:
            return "No data available for trend analysis."
        
        # Convert date column to datetime for analysis
        df['date'] = pd.to_datetime(df['date'])
        df['date_only'] = df['date'].dt.date
        
        daily_counts = df.groupby('date_only').size().sort_index()
        
        analysis = f"Trend Analysis ({len(df)} incidents):\n\n"
        analysis += f"Date Range: {daily_counts.index[0]} to {daily_counts.index[-1]}\n"
        analysis += f"Average Daily Incidents: {daily_counts.mean():.1f}\n"
        
        if len(daily_counts) > 0:
            analysis += f"Peak Day: {daily_counts.idxmax()} ({daily_counts.max()} incidents)\n"
            analysis += f"Lowest Day: {daily_counts.idxmin()} ({daily_counts.min()} incidents)\n"
        
        return analysis
    
    def _format_general_summary(self, df: pd.DataFrame) -> str:
        """Format general summary of results."""
        return f"Retrieved {len(df)} crime records from Chicago Police Database.\n" + \
               f"Columns available: {', '.join(df.columns.tolist())}"

# Test function
def test_tool():
    """Test the Chicago Crime Tool directly."""
    print("Testing Chicago Crime Tool...")
    
    try:
        # Environment variables are already loaded at module level
        tool = ChicagoCrimeTool(app_token=os.getenv("CHICAGO_DATA_APP_TOKEN"))
        
        result = tool._run(
            query_type="recent_crimes",
            limit=5
        )
        print("✅ Tool test successful!")
        print(result)
    except Exception as e:
        print(f"❌ Tool test failed: {e}")

if __name__ == "__main__":
    test_tool()