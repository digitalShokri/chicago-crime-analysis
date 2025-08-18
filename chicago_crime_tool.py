from langchain.tools import BaseTool
from langchain_core.callbacks.manager import CallbackManagerForToolUse
from sodapy import Socrata
import pandas as pd
from typing import Optional, Type, Any
from pydantic import BaseModel, Field
import json
import os
from dotenv import load_dotenv

load_dotenv()

class ChicagoCrimeInput(BaseModel):
    """Input for Chicago Crime Database queries."""
    query_type: str = Field(description="Type of query: 'recent_crimes', 'crime_stats', 'location_analysis', 'trend_analysis'")
    location: Optional[str] = Field(default=None, description="Specific address, neighborhood, or ward")
    crime_type: Optional[str] = Field(default=None, description="Type of crime: THEFT, BATTERY, BURGLARY, etc.")
    date_range: Optional[str] = Field(default="last_30_days", description="Time period: last_7_days, last_30_days, last_year, or custom YYYY-MM-DD format")
    limit: Optional[int] = Field(default=100, description="Number of records to return (max 50000)")

class ChicagoCrimeTool(BaseTool):
    """Tool for querying Chicago Police Department crime database."""
    
    name = "chicago_crime_database"
    description = """Query the Chicago Police Department's public crime database. 
    Can search for recent crimes, analyze crime statistics, examine location-based patterns, 
    and identify trends. Data includes crime type, location, date, and other incident details."""
    
    args_schema: Type[BaseModel] = ChicagoCrimeInput
    
    def __init__(self, app_token: Optional[str] = None):
        super().__init__()
        self.client = Socrata("data.cityofchicago.org", app_token)
        self.dataset_id = "ijzp-q8t2"  # Main crime dataset
    
    def _run(
        self, 
        query_type: str,
        location: Optional[str] = None,
        crime_type: Optional[str] = None,
        date_range: str = "last_30_days",
        limit: int = 100,
        run_manager: Optional[CallbackManagerForToolUse] = None,
    ) -> str:
        """Execute the Chicago crime database query."""
        
        try:
            # Build SoQL query based on parameters
            where_clauses = []
            
            # Date filtering - using more recent dates for testing
            if date_range == "last_7_days":
                where_clauses.append("date >= '2024-08-01T00:00:00'")
            elif date_range == "last_30_days":
                where_clauses.append("date >= '2024-07-01T00:00:00'")
            elif date_range == "last_year":
                where_clauses.append("date >= '2023-08-01T00:00:00'")
            
            # Crime type filtering
            if crime_type:
                where_clauses.append(f"primary_type='{crime_type.upper()}'")
            
            # Location filtering (using ward, beat, or block text search)
            if location:
                location_upper = location.upper()
                where_clauses.append(f"(ward='{location}' OR beat='{location}' OR upper(block) LIKE '%{location_upper}%')")
            
            # Build the query
            select_clause = "date, primary_type, description, location_description, block, ward, beat, latitude, longitude, arrest, domestic"
            where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            order_clause = "ORDER BY date DESC"
            limit_clause = f"LIMIT {min(limit, 50000)}"
            
            # Combine query parts
            query_parts = [select_clause, where_clause, order_clause, limit_clause]
            query = " ".join(filter(None, query_parts))
            
            print(f"Executing query: {query}")  # Debug output
            
            # Execute query
            results = self.client.get(self.dataset_id, query=query)
            
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
            return f"Error querying Chicago crime database: {str(e)}"
    
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
    
    tool = ChicagoCrimeTool(app_token=os.getenv("CHICAGO_DATA_APP_TOKEN"))
    
    try:
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

