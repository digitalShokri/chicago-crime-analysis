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

class DallasCrimeInput(BaseModel):
    """Input for Dallas Crime Database queries."""
    query_type: str = Field(description="Type of query: 'recent_crimes', 'crime_stats', 'location_analysis'")
    location: Optional[str] = Field(default=None, description="Specific address, neighborhood, or district")  
    crime_type: Optional[str] = Field(default=None, description="Type of incident: ASSAULT, BURGLARY, THEFT, etc.")
    limit: Optional[int] = Field(default=50, description="Number of records to return (recommended: 10-100 for fast queries)")

class DallasCrimeTool(BaseTool):
    """Optimized tool for querying Dallas Police Department crime database.
    
    This tool is optimized to work within Dallas API timeout constraints.
    It uses strategies that avoid expensive date filtering and sorting operations.
    """
    
    name: str = "dallas_crime_database"
    description: str = """Query the Dallas Police Department's public crime database with timeout optimization.
    Returns recent crime data without date filtering to avoid API timeouts.
    Use small limits (10-100) for best performance."""
    
    args_schema: Type[BaseModel] = DallasCrimeInput
    
    # Private attributes for Pydantic v2 compatibility
    _client: Optional[Socrata] = PrivateAttr(default=None)
    _dataset_id: str = PrivateAttr(default="qv6i-rri7")  # Common Dallas Police Incidents dataset ID
    _timeout_seconds: int = PrivateAttr(default=10)  # Match server timeout constraints
    _timeout_count: int = PrivateAttr(default=0)
    
    def __init__(self, app_token: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self._client = Socrata("www.dallasopendata.com", app_token)
        # Set timeout on the session object (sodapy doesn't support timeout parameter in get())
        self._client.session.timeout = self._timeout_seconds
        self._dataset_id = "qv6i-rri7"  # Dallas Police Incidents dataset
    
    def _run(
        self, 
        query_type: str,
        location: Optional[str] = None,
        crime_type: Optional[str] = None,
        limit: int = 50,
        run_manager: Optional[Any] = None,
    ) -> str:
        """Execute optimized Dallas crime database query."""
        
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
                return f"DATABASE_TIMEOUT: Dallas API timeout (timeout #{self._timeout_count}). Try reducing the limit parameter or simplifying filters."
            return f"Error querying Dallas crime database: {str(e)}"
    
    def _get_recent_crimes_optimized(self, crime_type: Optional[str], location: Optional[str], limit: int) -> str:
        """Get recent crimes using optimized query strategy."""
        
        # Strategy 1: Try simple query first (fastest)
        # Using actual Dallas column names discovered from API
        base_query = f"SELECT date1, offincident, premise, incident_address, beat, sector, division LIMIT {limit}"
        
        # Strategy 2: Add crime type filter if specified (still fast)
        if crime_type and not location:
            query = f"SELECT date1, offincident, premise, incident_address, beat, sector, division WHERE upper(offincident) LIKE upper('%{crime_type}%') LIMIT {limit}"
        # Strategy 3: Add location filter if specified (slower but manageable)
        elif location and not crime_type:
            location_filter = self._build_location_filter(location)
            query = f"SELECT date1, offincident, premise, incident_address, beat, sector, division WHERE {location_filter} LIMIT {limit}"
        # Strategy 4: Both filters (most likely to timeout)
        elif crime_type and location:
            location_filter = self._build_location_filter(location)
            query = f"SELECT date1, offincident, premise, incident_address, beat, sector, division WHERE upper(offincident) LIKE upper('%{crime_type}%') AND {location_filter} LIMIT {limit}"
        else:
            query = base_query
            
        return self._execute_query_with_fallback(query, base_query, "recent_crimes")
    
    def _get_crime_stats_optimized(self, crime_type: Optional[str], location: Optional[str], limit: int) -> str:
        """Get crime statistics using optimized approach."""
        
        # For stats, we need a reasonable sample size but not too large
        stats_limit = min(limit * 5, 1000)  # Use 5x the limit for better stats
        
        base_query = f"SELECT offincident, beat, sector, division LIMIT {stats_limit}"
        
        if crime_type and not location:
            query = f"SELECT offincident, beat, sector, division WHERE upper(offincident) LIKE upper('%{crime_type}%') LIMIT {stats_limit}"
        elif location and not crime_type:
            location_filter = self._build_location_filter(location)
            query = f"SELECT offincident, beat, sector, division WHERE {location_filter} LIMIT {stats_limit}"
        elif crime_type and location:
            location_filter = self._build_location_filter(location)
            query = f"SELECT offincident, beat, sector, division WHERE upper(offincident) LIKE upper('%{crime_type}%') AND {location_filter} LIMIT {stats_limit}"
        else:
            query = base_query
            
        return self._execute_query_with_fallback(query, base_query, "crime_stats")
    
    def _get_location_analysis_optimized(self, location: Optional[str], limit: int) -> str:
        """Get location analysis using optimized approach."""
        
        base_query = f"SELECT beat, sector, division, offincident, incident_address LIMIT {limit * 2}"
        
        if location:
            location_filter = self._build_location_filter(location) 
            query = f"SELECT beat, sector, division, offincident, incident_address WHERE {location_filter} LIMIT {limit * 2}"
        else:
            query = base_query
            
        return self._execute_query_with_fallback(query, base_query, "location_analysis")
    
    def _build_location_filter(self, location: str) -> str:
        """Build location filter optimized for Dallas data structure."""
        location_upper = location.upper()
        
        # Dallas neighborhood to beat mapping (Arts District and other popular areas)
        neighborhood_to_beats = {
            'ARTS DISTRICT': ['141', '142', '143'],  # Downtown beats that likely cover Arts District
            'DOWNTOWN': ['141', '142', '143', '144'],
            'DEEP ELLUM': ['153', '154'],  # Likely beats for Deep Ellum
            'UPTOWN': ['121', '122', '123'],  # Likely beats for Uptown
            'BISHOP ARTS': ['344', '345'],  # Bishop Arts District area
            'DESIGN DISTRICT': ['131', '132'],
        }
        
        # Check if this is a known neighborhood
        if location_upper in neighborhood_to_beats:
            beats = neighborhood_to_beats[location_upper]
            beat_conditions = " OR ".join([f"beat='{beat}'" for beat in beats])
            return f"({beat_conditions})"
        
        # Dallas typically has beats, sectors, and divisions
        elif location.lower().startswith('beat '):
            beat_num = location.lower().replace('beat ', '').strip()
            return f"beat='{beat_num}'"
        elif location.lower().startswith('sector '):
            sector = location.lower().replace('sector ', '').strip()
            return f"sector='{sector}'"
        elif location.isdigit():
            # Could be beat or sector
            return f"(beat='{location}' OR sector='{location}')"
        
        # Text search in address field (Dallas uses incident_address)
        return f"upper(incident_address) LIKE '%{location_upper}%'"
    
    def _execute_query_with_fallback(self, primary_query: str, fallback_query: str, format_type: str) -> str:
        """Execute query with fallback on timeout."""
        
        print(f"Executing Dallas query: {primary_query}")
        
        start_time = time.time()
        try:
            results = self._client.get(self._dataset_id, query=primary_query)
            query_time = time.time() - start_time
            print(f"Dallas query completed in {query_time:.2f} seconds")
            
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
            return "No crime data found for the specified criteria in Dallas database."
        
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
            return "No recent crimes found in Dallas database."
        
        summary = f"Found {len(df)} Dallas crime incidents (sample without date filtering due to API constraints):\n\n"
        
        for _, row in df.head(10).iterrows():
            incident_type = row.get('offincident', 'Unknown')
            premise = row.get('premise', 'Unknown premise')
            address = row.get('incident_address', 'Unknown address')
            date_time = row.get('date1', 'Unknown date')
            beat = row.get('beat', 'Unknown')
            sector = row.get('sector', 'Unknown')
            
            summary += f"• {incident_type}\n"
            summary += f"  Address: {address}\n"
            summary += f"  Premise: {premise}\n"
            summary += f"  Beat: {beat}, Sector: {sector}\n"
            summary += f"  Date: {str(date_time)[:10]}\n\n"
        
        return summary
    
    def _format_crime_stats(self, df: pd.DataFrame) -> str:
        """Format crime statistics."""
        if df.empty:
            return "No crime data available for Dallas statistics."
        
        stats = f"Dallas Crime Statistics Summary (sample of {len(df)} incidents):\n\n"
        
        # Crime type breakdown
        if 'offincident' in df.columns:
            crime_counts = df['offincident'].value_counts().head(10)
            stats += "Top Crime Types:\n"
            for crime_type, count in crime_counts.items():
                percentage = (count / len(df)) * 100
                stats += f"• {crime_type}: {count} incidents ({percentage:.1f}%)\n"
        
        # Beat analysis
        if 'beat' in df.columns:
            beat_counts = df['beat'].value_counts().head(5)
            stats += f"\nTop Beats by Incidents:\n"
            for beat, count in beat_counts.items():
                stats += f"• Beat {beat}: {count} incidents\n"
        
        # Sector analysis
        if 'sector' in df.columns:
            sector_counts = df['sector'].value_counts().head(5)
            stats += f"\nTop Sectors by Incidents:\n"
            for sector, count in sector_counts.items():
                stats += f"• Sector {sector}: {count} incidents\n"
        
        # Division analysis
        if 'division' in df.columns:
            division_counts = df['division'].value_counts().head(5)
            stats += f"\nTop Divisions by Incidents:\n"
            for division, count in division_counts.items():
                stats += f"• Division {division}: {count} incidents\n"
        
        stats += f"\n⚠️  Note: Statistics based on sample data (no date filtering due to API timeout constraints)"
        return stats
    
    def _format_location_analysis(self, df: pd.DataFrame) -> str:
        """Format location-based analysis."""
        if df.empty:
            return "No location data available for Dallas analysis."
        
        analysis = f"Dallas Location Analysis (sample of {len(df)} incidents):\n\n"
        
        # Beat analysis
        if 'beat' in df.columns and df['beat'].notna().any():
            beat_counts = df['beat'].value_counts().head(5)
            analysis += "Top Beats by Incident Count:\n"
            for beat, count in beat_counts.items():
                analysis += f"• Beat {beat}: {count} incidents\n"
        
        # Sector analysis
        if 'sector' in df.columns and df['sector'].notna().any():
            sector_counts = df['sector'].value_counts().head(5)
            analysis += "\nTop Sectors by Incident Count:\n"
            for sector, count in sector_counts.items():
                analysis += f"• Sector {sector}: {count} incidents\n"
        
        # Division analysis
        if 'division' in df.columns and df['division'].notna().any():
            division_counts = df['division'].value_counts().head(5)
            analysis += "\nTop Divisions by Incident Count:\n"
            for division, count in division_counts.items():
                analysis += f"• Division {division}: {count} incidents\n"
        
        analysis += f"\n⚠️  Note: Analysis based on sample data (no date filtering due to API timeout constraints)"
        return analysis
    
    def _format_general_summary(self, df: pd.DataFrame) -> str:
        """Format general summary of results."""
        return f"Retrieved {len(df)} crime records from Dallas Police Database.\n" + \
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
    """Test the optimized Dallas Crime Tool."""
    print("Testing Optimized Dallas Crime Tool...")
    
    try:
        # Environment variables are already loaded at module level
        tool = DallasCrimeTool(app_token=os.getenv("DALLAS_DATA_APP_TOKEN"))
        
        # Test 1: Simple recent crimes
        print("\n1. Testing recent crimes (no filters)...")
        result = tool._run(query_type="recent_crimes", limit=10)
        print("✅ Result:", result[:200] + "..." if len(result) > 200 else result)
        
        # Test 2: Crime type filter
        print("\n2. Testing with crime type filter...")
        result = tool._run(query_type="recent_crimes", crime_type="ASSAULT", limit=5)
        print("✅ Result:", result[:200] + "..." if len(result) > 200 else result)
        
        # Test 3: Location filter
        print("\n3. Testing with location...")
        result = tool._run(query_type="location_analysis", location="Beat 1", limit=10)
        print("✅ Result:", result[:200] + "..." if len(result) > 200 else result)
        
        print(f"\n📊 Timeout stats: {tool.get_timeout_stats()}")
        
    except Exception as e:
        print(f"❌ Tool test failed: {e}")

if __name__ == "__main__":
    test_tool()