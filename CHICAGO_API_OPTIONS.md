# Chicago Crime Data API Query Options

## Overview
The Chicago Crime Database uses the Socrata Open Data API (SODA) with the dataset ID `ijzp-q8t2`.

## Available Query Parameters

### Date Range Options
- `last_3_days` - Default option, queries crimes from the last 3 days
- `last_7_days` - Crimes from the last week
- `last_30_days` - Crimes from the last month  
- `last_year` - Crimes from the last 365 days
- Custom date: `YYYY-MM-DD` format (e.g., "2024-01-15")

### Query Types
1. **recent_crimes** - Lists recent crime incidents with details
2. **crime_stats** - Statistical breakdown of crime types and arrest rates
3. **location_analysis** - Analysis by ward and location type
4. **trend_analysis** - Daily trends and patterns

### Location Filtering
- **Ward numbers**: Use "Ward 1" or just "1" 
- **Beat numbers**: Use "Beat 1234" or just "1234"
- **Neighborhood names**: "Lincoln Park", "Loop", etc. (searches in block text)
- **Street addresses**: Partial street names work

### Crime Type Filtering
Common crime types include:
- THEFT
- BATTERY  
- BURGLARY
- ASSAULT
- CRIMINAL DAMAGE
- ROBBERY
- MOTOR VEHICLE THEFT
- NARCOTICS
- DECEPTIVE PRACTICE

### Available Data Fields
- `date` - When the crime occurred
- `primary_type` - Main category of crime
- `description` - Detailed description
- `location_description` - Type of location (street, residence, etc.)
- `block` - Street block where crime occurred
- `ward` - Political ward number
- `beat` - Police beat number
- `latitude`, `longitude` - Geographic coordinates
- `arrest` - Whether an arrest was made
- `domestic` - Whether it was domestic-related

### Query Limits
- Default limit: 100 records
- Maximum limit: 50,000 records
- API timeout: 30 seconds

## Timeout Monitoring & Optimization

### Optimized Tool (chicago_crime_tool_optimized.py)
The optimized tool includes advanced timeout handling:
- **10-second timeout** matching Chicago API server limits
- **Fallback strategies** - tries simpler queries when complex ones timeout
- **Proper API authentication** - eliminates throttling warnings
- **Timeout statistics** via `get_timeout_stats()`
- **Sample data approach** - avoids date filtering that causes timeouts
- Returns `DATABASE_TIMEOUT:` prefix for timeout responses

### Performance Improvements
- ✅ **No more API token warnings** - proper authentication configured
- ✅ **Faster queries** - optimized field selection and query structure  
- ✅ **Reliable fallback** - attempts simpler queries when primary query times out
- ✅ **Better error handling** - clear timeout indicators for LLM integration

## Usage Examples

### Basic Recent Crimes
```python
tool._run(query_type="recent_crimes", limit=10)
```

### Location-Specific Query
```python
tool._run(
    query_type="crime_stats",
    location="Ward 1",
    date_range="last_7_days"
)
```

### Crime Type Analysis
```python
tool._run(
    query_type="trend_analysis", 
    crime_type="THEFT",
    date_range="last_30_days"
)
```

### Custom Date Range
```python
tool._run(
    query_type="recent_crimes",
    date_range="2024-08-01",
    limit=50
)
```

## Performance Notes
- Queries with broader date ranges may timeout
- Location filtering by neighborhood name is slower than ward/beat numbers
- Consider using smaller limits for initial testing
- Monitor timeout statistics to identify problematic queries