import streamlit as st
import os
from dotenv import load_dotenv
import traceback
from datetime import datetime

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Multi-City Crime Intelligence Assistant",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
</style>
""", unsafe_allow_html=True)

def initialize_system():
    """Initialize the multi-city crime analysis system."""
    if 'system_initialized' not in st.session_state:
        st.session_state.system_initialized = False
        st.session_state.initialization_error = None
        st.session_state.multi_city_agent = None
    
    if not st.session_state.system_initialized:
        try:
            with st.spinner("Initializing Multi-City Crime Analysis System..."):
                # Import multi-city agent
                from multi_city_crime_agent import MultiCityCrimeAgent
                
                # Initialize multi-city agent
                multi_city_agent = MultiCityCrimeAgent()
                
                # Store in session state
                st.session_state.multi_city_agent = multi_city_agent
                st.session_state.system_initialized = True
                
                return True
                
        except Exception as e:
            st.session_state.initialization_error = str(e)
            return False
    
    return True

def main():
    """Main application function."""
    
    # Initialize session state variables first
    if 'selected_city' not in st.session_state:
        st.session_state.selected_city = 'chicago'  # Default to Chicago
    
    # Header
    st.markdown('<h1 class="main-header">🚨 Multi-City Crime Intelligence Assistant</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">Powered by Claude AI with Chicago & Dallas Police Data</p>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.header("🔧 System Configuration")
    
    # City Selection
    st.sidebar.subheader("🏙️ City Selection")
    selected_city = st.sidebar.selectbox(
        "Choose a city to analyze:",
        ["chicago", "dallas"],
        format_func=lambda x: x.title(),
        index=0 if st.session_state.selected_city == "chicago" else 1
    )
    st.session_state.selected_city = selected_city
    
    # Check environment setup
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    chicago_token = os.getenv("CHICAGO_DATA_APP_TOKEN")
    dallas_token = os.getenv("DALLAS_DATA_APP_TOKEN")
    
    st.sidebar.subheader("Environment Status")
    if anthropic_key:
        st.sidebar.success("✅ Anthropic API Key configured")
    else:
        st.sidebar.error("❌ Anthropic API Key missing")
        st.sidebar.warning("Please set ANTHROPIC_API_KEY in your .env file")
    
    if chicago_token:
        st.sidebar.success("✅ Chicago Data Token configured")
    else:
        st.sidebar.warning("⚠️ Chicago Data Token not configured (optional)")
        st.sidebar.info("Consider adding CHICAGO_DATA_APP_TOKEN for better performance")
        
    if dallas_token:
        st.sidebar.success("✅ Dallas Data Token configured")
    else:
        st.sidebar.warning("⚠️ Dallas Data Token not configured (optional)")
        st.sidebar.info("Consider adding DALLAS_DATA_APP_TOKEN for better performance")
    
    # Initialize system
    if not anthropic_key:
        st.error("❌ Cannot start without Anthropic API Key. Please check your .env file.")
        st.stop()
    
    system_ready = initialize_system()
    
    if not system_ready:
        st.error(f"❌ System initialization failed: {st.session_state.initialization_error}")
        with st.expander("Show Error Details"):
            st.code(st.session_state.initialization_error)
        st.stop()
    
    st.sidebar.success("✅ System Ready")
    
    # Mode selection
    st.sidebar.subheader("Analysis Mode")
    mode = st.sidebar.selectbox(
        "Choose analysis mode:",
        ["🔍 Basic Crime Analysis", "🛡️ Safety Advisory (with Human Review)", "🔧 Direct Tool Query", "📊 LLM Observability Dashboard"]
    )
    
    # Main content area
    if mode == "🔍 Basic Crime Analysis":
        basic_analysis_mode()
    elif mode == "🛡️ Safety Advisory (with Human Review)":
        safety_advisory_mode()
    elif mode == "📊 LLM Observability Dashboard":
        observability_mode()
    else:
        direct_tool_mode()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #888; font-size: 0.9rem;">
        <p><strong>Data Source:</strong> Chicago Police Department via City of Chicago Data Portal</p>
        <p><strong>Disclaimer:</strong> This tool is for informational purposes only. Always use your own judgment for safety decisions.</p>
        <p><strong>Last Updated:</strong> {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)

def basic_analysis_mode():
    """Basic crime analysis interface."""
    selected_city = st.session_state.selected_city
    st.header(f"🔍 {selected_city.title()} Crime Analysis")
    st.write(f"Ask questions about {selected_city.title()} crime data and get AI-powered insights.")
    
    # Add city-specific optimization notice
    with st.expander("⚙️ System Optimizations"):
        st.success(f"✅ **City-Optimized**: This system uses {selected_city.title()}-specific timeout-optimized queries with proper API authentication.")
        st.info("💡 **Recent Data**: Queries fetch sample data from recent crime patterns without date filtering to avoid API timeouts.")
        st.warning("⏰ **Timeout Handling**: If queries timeout, the system will skip LLM processing and provide clear error messages.")
        st.info(f"🏙️ **Multi-City Support**: Switch between cities using the sidebar selector. Each city has optimized API handling.")
    
    # City-specific example queries
    st.subheader("💡 Example Questions")
    if selected_city == "chicago":
        examples = [
            "What are recent crime trends in downtown Chicago?",
            "Show me crime statistics for Lincoln Park",
            "Is Wicker Park safe for tourists?",
            "What types of crimes are most common in Chicago?",
            "Analyze crime patterns in the Loop area"
        ]
    else:  # Dallas
        examples = [
            "What are recent crime trends in downtown Dallas?",
            "Show me crime statistics for Deep Ellum",
            "Is Uptown Dallas safe for residents?",
            "What types of crimes are most common in Dallas?",
            "Analyze crime patterns in the Arts District"
        ]
    
    col1, col2 = st.columns(2)
    for i, example in enumerate(examples):
        if i % 2 == 0:
            if col1.button(f"📝 {example}", key=f"example_{i}"):
                st.session_state.user_query = example
        else:
            if col2.button(f"📝 {example}", key=f"example_{i}"):
                st.session_state.user_query = example
    
    # User input
    user_query = st.text_area(
        "Your Question:",
        value=st.session_state.get('user_query', ''),
        placeholder=f"Ask about {selected_city.title()} crime data...",
        height=100
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_button = st.button(f"🔍 Analyze {selected_city.title()} Crime Data", type="primary", use_container_width=True)
    
    if analyze_button and user_query:
        with st.spinner(f"🔍 Analyzing {selected_city.title()} crime data with Claude..."):
            try:
                response = st.session_state.multi_city_agent.analyze_crime(
                    user_query, 
                    selected_city=selected_city
                )
                
                st.success(f"✅ {selected_city.title()} Analysis Complete")
                st.markdown(f"### 📊 {selected_city.title()} Analysis Results")
                st.markdown(response)
                
                # Add download option
                st.download_button(
                    label="📥 Download Analysis",
                    data=response,
                    file_name=f"{selected_city}_crime_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
                
            except Exception as e:
                st.error(f"❌ Analysis failed: {e}")
                with st.expander("Show Error Details"):
                    st.code(traceback.format_exc())

def safety_advisory_mode():
    """Safety advisory interface with human-in-the-loop."""
    selected_city = st.session_state.selected_city
    st.header("🛡️ Safety Advisory System")
    st.write(f"Get {selected_city.title()}-specific safety recommendations with human oversight for critical queries.")
    
    st.info("🔍 High-risk safety queries will be flagged for human review before providing recommendations.")
    
    # Add notice about optimized data
    st.info(f"ℹ️ Safety recommendations are based on recent sample {selected_city.title()} crime data due to API optimization. The system uses the most current available data patterns.")
    
    # City-specific safety query examples
    st.subheader("💡 Safety Questions")
    if selected_city == "chicago":
        safety_examples = [
            "Is it safe to walk alone at night in downtown Chicago?",
            "I'm moving to Lincoln Park with my family - what should I know about safety?",
            "What safety precautions should tourists take in Chicago?",
            "Are there any areas in Chicago I should avoid?",
            "Safety tips for using public transportation in Chicago"
        ]
    else:  # Dallas
        safety_examples = [
            "Is it safe to walk alone at night in downtown Dallas?",
            "I'm moving to Uptown Dallas with my family - what should I know about safety?",
            "What safety precautions should tourists take in Dallas?",
            "Are there any areas in Dallas I should avoid?",
            "Safety tips for using DART public transportation in Dallas"
        ]
    
    for i, example in enumerate(safety_examples):
        if st.button(f"🛡️ {example}", key=f"safety_example_{i}"):
            st.session_state.safety_query = example
    
    # User input
    safety_query = st.text_area(
        "Your Safety Question:",
        value=st.session_state.get('safety_query', ''),
        placeholder=f"Ask about safety in {selected_city.title()}...",
        height=100
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        safety_button = st.button(f"🛡️ Get {selected_city.title()} Safety Advice", type="primary", use_container_width=True)
    
    if safety_button and safety_query:
        # For now, use the multi-city agent for safety analysis
        with st.spinner(f"🔍 Analyzing {selected_city.title()} safety considerations..."):
            try:
                # Use the multi-city agent with a safety-focused query
                safety_focused_query = f"Safety analysis: {safety_query}"
                response = st.session_state.multi_city_agent.analyze_crime(
                    safety_focused_query,
                    selected_city=selected_city
                )
                
                if "human review" in response.lower() or "interrupt" in response.lower():
                    st.warning("⏸️ This query requires human review. In a production system, a human moderator would review this before providing recommendations.")
                    st.info("🔄 For this demo, the system would pause here for human input.")
                
                st.success(f"✅ {selected_city.title()} Safety Analysis Complete")
                st.markdown(f"### 🛡️ {selected_city.title()} Safety Recommendations")
                st.markdown(response)
                
                # Add download option
                st.download_button(
                    label="📥 Download Safety Report",
                    data=response,
                    file_name=f"{selected_city}_safety_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
                
            except Exception as e:
                if "interrupt" in str(e).lower():
                    st.warning("⏸️ This query has been flagged for human review.")
                    st.info("In a production system, a human moderator would review this query before providing safety recommendations.")
                else:
                    st.error(f"❌ {selected_city.title()} safety analysis failed: {e}")
                    with st.expander("Show Error Details"):
                        st.code(traceback.format_exc())

def direct_tool_mode():
    """Direct tool query interface."""
    selected_city = st.session_state.selected_city
    st.header("🔧 Direct Tool Query")
    st.write(f"Query the {selected_city.title()} crime database directly with specific parameters.")
    
    # Add optimization info
    st.info(f"⚙️ **Optimized Mode**: This tool uses the new timeout-optimized {selected_city.title()} crime API client with proper authentication and fallback strategies.")
    
    # Query parameters
    col1, col2 = st.columns(2)
    
    with col1:
        query_type = st.selectbox(
            "Query Type:",
            ["recent_crimes", "crime_stats", "location_analysis"]
        )
        
        location = st.text_input(
            "Location (optional):",
            placeholder="e.g., Loop, Lincoln Park, Ward 1"
        )
    
    with col2:
        crime_type = st.text_input(
            "Crime Type (optional):",
            placeholder="e.g., THEFT, BATTERY, BURGLARY"
        )
        
        limit = st.number_input(
            "Number of records (recommended 10-100):",
            min_value=1,
            max_value=1000,
            value=50,
            help="Smaller limits work better due to API timeout constraints"
        )
    
    # Remove date_range since optimized tool doesn't support it due to timeout constraints
    st.info("⚠️ Note: The optimized tool fetches recent sample data without date filtering to avoid API timeouts. Results represent recent crime patterns.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        query_button = st.button("🔍 Execute Query", type="primary", use_container_width=True)
    
    if query_button:
        with st.spinner(f"📡 Querying {selected_city.title()} Police Database..."):
            try:
                # Get the appropriate city tool
                if selected_city == "chicago":
                    city_tool = st.session_state.multi_city_agent.chicago_tool
                else:  # dallas
                    city_tool = st.session_state.multi_city_agent.dallas_tool
                
                # Build parameters for optimized tool
                params = {
                    "query_type": query_type,
                    "limit": limit
                }
                
                if location:
                    params["location"] = location
                if crime_type:
                    params["crime_type"] = crime_type
                
                # Execute query
                result = city_tool._run(**params)
                
                st.success("✅ Query Executed Successfully")
                st.markdown("### 📊 Query Results")
                
                # Handle timeout responses
                if result.startswith("DATABASE_TIMEOUT:"):
                    st.warning("⏰ Query timed out due to API constraints")
                    st.error(result)
                    st.info("💡 Try reducing the limit or simplifying your query parameters.")
                else:
                    # Display successful results
                    if len(result) > 2000:
                        st.markdown("**Result Preview (first 2000 characters):**")
                        st.text(result[:2000] + "...")
                        
                        with st.expander("Show Full Results"):
                            st.text(result)
                    else:
                        st.text(result)
                        
                    # Show timeout statistics
                    if hasattr(city_tool, 'get_timeout_stats'):
                        timeout_stats = city_tool.get_timeout_stats()
                        if timeout_stats['timeout_count'] > 0:
                            st.warning(f"⚠️ {selected_city.title()} API Timeouts: {timeout_stats['timeout_count']} (threshold: {timeout_stats['timeout_threshold']}s)")
                
                # Add download option
                st.download_button(
                    label="📥 Download Results",
                    data=result,
                    file_name=f"{selected_city}_crime_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"❌ Query failed: {e}")
                with st.expander("Show Error Details"):
                    st.code(traceback.format_exc())

def observability_mode():
    """LLM Observability dashboard interface."""
    try:
        # Try importing with more detailed error handling
        import sys
        import os
        
        # Add current directory to path if needed
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        from observability_dashboard import render_observability_page
        render_observability_page()
        
    except ImportError as e:
        st.error("❌ Observability dashboard not available.")
        st.write("**Import Error Details:**")
        st.code(str(e))
        
        # Show debugging info
        with st.expander("🔧 Debugging Information"):
            st.write("**Python Path:**")
            import sys
            for path in sys.path:
                st.write(f"- {path}")
            
            st.write("**Available modules in current directory:**")
            import os
            files = [f for f in os.listdir('.') if f.endswith('.py')]
            for file in files:
                st.write(f"- {file}")
        
        # Provide fallback manual dashboard
        st.info("**Fallback:** Basic observability status shown below")
        render_basic_observability()
        
    except Exception as e:
        st.error(f"❌ Error loading observability dashboard: {e}")
        with st.expander("Show Error Details"):
            st.code(traceback.format_exc())

def render_basic_observability():
    """Simple fallback observability dashboard."""
    st.header("📊 Basic Observability Status")
    
    # Check LangSmith availability
    try:
        import langsmith
        st.success(f"✅ LangSmith installed: version {langsmith.__version__}")
    except ImportError:
        st.error("❌ LangSmith not installed")
    
    # Check environment variables
    st.subheader("🔧 Environment Configuration")
    
    env_vars = {
        "ANTHROPIC_API_KEY": "Anthropic API Key",
        "LANGCHAIN_TRACING_V2": "LangSmith Tracing",
        "LANGCHAIN_PROJECT": "LangSmith Project",
        "LANGCHAIN_API_KEY": "LangSmith API Key"
    }
    
    for var, description in env_vars.items():
        value = os.getenv(var)
        if value:
            if "key" in var.lower():
                st.success(f"✅ {description}: ••••••••")
            else:
                st.success(f"✅ {description}: {value}")
        else:
            st.warning(f"⚠️ {description}: Not set")
    
    # Test metrics collection
    try:
        from langsmith_config import metrics_collector
        all_metrics = metrics_collector.get_metrics(exclude_test_data=False)
        filtered_metrics = metrics_collector.get_metrics(exclude_test_data=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"📈 All Metrics: {len(all_metrics)}")
        with col2:
            st.subheader(f"📊 Filtered: {len(filtered_metrics)}")
        
        if all_metrics:
            st.write("**Recent metrics (showing source of queries):**")
            for metric in all_metrics[-10:]:
                metric_type = metric.get('type', 'unknown')
                timestamp = metric.get('timestamp', 'no time')
                
                # Show more detail for debugging
                if 'endpoint' in metric:
                    endpoint = metric.get('endpoint', 'unknown')
                    st.write(f"- {metric_type} | {endpoint} | {timestamp}")
                else:
                    st.write(f"- {metric_type} | {timestamp}")
                    # Show the full metric for anomalies to debug
                    if metric_type == 'anomaly':
                        st.json(metric)
        else:
            st.info("No metrics collected yet. Run some queries to see data.")
            
        # Add clear button
        if st.button("🧹 Clear All Test Data"):
            metrics_collector.clear_test_data()
            st.success("Test data cleared!")
            st.experimental_rerun()
            
    except Exception as e:
        st.error(f"❌ Cannot access metrics: {e}")

if __name__ == "__main__":
    main()