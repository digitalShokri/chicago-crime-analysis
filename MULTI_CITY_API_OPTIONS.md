# Multi-City Crime Data API Options

## Overview
The Multi-City Crime Analysis system now supports both Chicago and Dallas crime data APIs, each optimized for their specific data structures and timeout constraints.

## Supported Cities

### 🏢 Chicago 
- **Data Source**: Chicago Police Department via City of Chicago Data Portal
- **Base URL**: `data.cityofchicago.org`
- **Dataset ID**: `ijzp-q8t2` 
- **Tool**: `chicago_crime_tool_optimized.py`

### 🌆 Dallas
- **Data Source**: Dallas Police Department via Dallas Open Data Portal  
- **Base URL**: `www.dallasopendata.com`
- **Dataset ID**: `qv6i-rri7`
- **Tool**: `dallas_crime_tool_optimized.py`

## City-Specific Data Fields

### Chicago Crime Data Fields
- `date` - When the crime occurred
- `primary_type` - Main category of crime
- `description` - Detailed description
- `location_description` - Type of location
- `block` - Street block where crime occurred
- `ward` - Political ward number
- `beat` - Police beat number
- `arrest` - Whether an arrest was made
- `domestic` - Whether it was domestic-related

### Dallas Crime Data Fields
- `date1` - When the crime occurred
- `offincident` - Main category/description of crime
- `premise` - Type of location/premise
- `incident_address` - Street address where crime occurred
- `beat` - Police beat number
- `sector` - Police sector
- `division` - Police division
- `incidentnum` - Unique incident number

## Query Types Available

### 1. Recent Crimes
- Returns recent crime incidents with details
- Shows actual crime reports from the database
- **Chicago fields**: date, primary_type, description, location_description, block, ward, beat, arrest, domestic
- **Dallas fields**: date1, offincident, premise, incident_address, beat, sector, division

### 2. Crime Statistics
- Statistical breakdown of crime types and patterns
- Shows top crime categories and percentages
- **Chicago**: Includes arrest rates, domestic incident rates
- **Dallas**: Includes beat, sector, and division statistics

### 3. Location Analysis 
- Analysis by geographic areas and location types
- **Chicago**: Ward-based analysis, location description patterns
- **Dallas**: Beat, sector, and division-based analysis

## Location Filtering Options

### Chicago Location Filtering
- **Ward numbers**: "Ward 1" or "1"
- **Beat numbers**: "Beat 1234" or "1234" 
- **Neighborhood names**: "Lincoln Park", "Loop" (searches in block text)

### Dallas Location Filtering
- **Beat numbers**: "Beat 1" or "1"
- **Sector**: "Sector A" or specific sector codes
- **Address search**: Street names and addresses (searches in incident_address)

## Performance Optimization

### Timeout Handling
- **Both cities**: 10-second timeout matching server constraints
- **Fallback strategies**: Simplified queries when primary queries timeout
- **Proper authentication**: Eliminates API throttling warnings
- **Sample data approach**: Avoids expensive date filtering

### City-Specific Optimizations

#### Chicago Optimizations
- Uses ward/beat filtering (indexed fields)
- Text search limited to block field
- Optimized field selection for performance

#### Dallas Optimizations  
- Uses beat/sector/division filtering (indexed fields)
- Text search in incident_address field
- Optimized for Dallas-specific data structure

## Environment Configuration

Add these to your `.env` file:

```bash
# Chicago API Token
CHICAGO_DATA_APP_TOKEN=your_chicago_token_here

# Dallas API Token  
DALLAS_DATA_APP_TOKEN=your_dallas_token_here

# Anthropic API for LLM analysis
ANTHROPIC_API_KEY=your_anthropic_key_here

# LangSmith for observability
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=multi-city-crime-analysis
LANGCHAIN_API_KEY=your_langsmith_key_here
```

## Usage Examples

### Multi-City Agent Usage
```python
from multi_city_crime_agent import MultiCityCrimeAgent

# Initialize agent (loads both Chicago and Dallas tools)
agent = MultiCityCrimeAgent()

# Analyze Chicago crime
chicago_response = agent.analyze_crime(
    "What are recent crime trends in Lincoln Park?",
    selected_city="chicago"
)

# Analyze Dallas crime  
dallas_response = agent.analyze_crime(
    "Show me crime statistics for downtown Dallas",
    selected_city="dallas"
)
```

### Direct Tool Usage
```python
from chicago_crime_tool_optimized import ChicagoCrimeTool
from dallas_crime_tool_optimized import DallasCrimeTool

# Chicago direct queries
chicago_tool = ChicagoCrimeTool(app_token=os.getenv("CHICAGO_DATA_APP_TOKEN"))
chicago_data = chicago_tool._run(
    query_type="recent_crimes",
    location="Ward 1",
    limit=50
)

# Dallas direct queries
dallas_tool = DallasCrimeTool(app_token=os.getenv("DALLAS_DATA_APP_TOKEN"))
dallas_data = dallas_tool._run(
    query_type="crime_stats", 
    location="Beat 1",
    limit=100
)
```

## Streamlit App Features

### City Selection
- Sidebar dropdown to choose between Chicago and Dallas
- City-specific example queries and placeholders
- Dynamic UI updates based on selected city

### Analysis Modes
- **Basic Analysis**: AI-powered analysis with city-specific insights
- **Direct Tool Query**: Raw database queries with city-specific parameters  
- **Safety Advisory**: City-specific safety recommendations

### City-Specific Examples

#### Chicago Examples
- "What are recent crime trends in downtown Chicago?"
- "Is Wicker Park safe for tourists?"
- "Analyze crime patterns in the Loop area"

#### Dallas Examples
- "What are recent crime trends in downtown Dallas?"
- "Is Uptown Dallas safe for residents?" 
- "Analyze crime patterns in the Arts District"

## Error Handling

### Timeout Responses
Both tools return `DATABASE_TIMEOUT:` prefix when queries timeout, allowing the system to:
- Skip LLM processing for incomplete data
- Provide clear user feedback
- Track timeout statistics for optimization

### City-Specific Error Messages
- Clear indication of which city's API had issues
- Suggestions for query simplification
- Fallback to simpler queries when possible

## Performance Notes

### Chicago Performance
- Ward/beat filtering performs better than neighborhood names
- Simple queries complete in 0.3-1.0 seconds
- Complex location searches may timeout

### Dallas Performance  
- Beat/sector filtering performs well
- Address searches are moderately fast
- Simple queries complete in 0.1-0.5 seconds

### General Performance Tips
- Use smaller limits (10-100) for faster queries
- Prefer structured location filters (ward, beat, sector)
- Monitor timeout statistics to optimize query patterns