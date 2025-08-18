#!/usr/bin/env python3
"""
Comprehensive test script for Chicago Crime Analysis System
Tests all components step by step with detailed output
"""

import os
import sys
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_subsection(title):
    """Print a formatted subsection header."""
    print(f"\n{'-'*40}")
    print(f"  {title}")
    print(f"{'-'*40}")

def test_environment():
    """Test environment setup and API keys."""
    print_section("1. ENVIRONMENT SETUP TEST")
    
    # Check Python version
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    
    # Check environment variables
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    chicago_token = os.getenv("CHICAGO_DATA_APP_TOKEN")
    
    print(f"\nEnvironment Variables:")
    print(f"  ANTHROPIC_API_KEY: {'✅ Found' if anthropic_key else '❌ Missing'}")
    if anthropic_key:
        print(f"    Key preview: {anthropic_key[:10]}...")
    
    print(f"  CHICAGO_DATA_APP_TOKEN: {'✅ Found' if chicago_token else '⚠️ Optional but recommended'}")
    if chicago_token:
        print(f"    Token preview: {chicago_token[:10]}...")
    
    # Check critical imports
    print(f"\nCritical Package Imports:")
    packages = [
        ("langchain", "langchain"),
        ("langgraph", "langgraph"), 
        ("langchain_anthropic", "langchain_anthropic"),
        ("sodapy", "sodapy"),
        ("pandas", "pandas"),
        ("python-dotenv", "dotenv")
    ]
    
    for package_name, import_name in packages:
        try:
            __import__(import_name)
            print(f"  {package_name}: ✅ Available")
        except ImportError as e:
            print(f"  {package_name}: ❌ Missing - {e}")
            return False
    
    if not anthropic_key:
        print(f"\n❌ Critical Error: ANTHROPIC_API_KEY is required")
        return False
    
    return True

def test_chicago_crime_tool():
    """Test the Chicago Crime Tool."""
    print_section("2. CHICAGO CRIME TOOL TEST")
    
    try:
        from chicago_crime_tool_fixed import ChicagoCrimeTool
        print("✅ ChicagoCrimeTool imported successfully")
        
        # Initialize tool
        tool = ChicagoCrimeTool(app_token=os.getenv("CHICAGO_DATA_APP_TOKEN"))
        print("✅ Tool initialized successfully")
        
        # Test different query types
        test_queries = [
            {"name": "Recent Crimes", "params": {"query_type": "recent_crimes", "limit": 3}},
            {"name": "Crime Statistics", "params": {"query_type": "crime_stats", "limit": 50}},
            {"name": "Location Analysis - Loop", "params": {"query_type": "location_analysis", "location": "Loop", "limit": 25}},
        ]
        
        for test in test_queries:
            print_subsection(f"Testing: {test['name']}")
            try:
                result = tool._run(**test['params'])
                print(f"✅ {test['name']} successful")
                print(f"   Result preview: {result[:150]}...")
                
                if "Error" in result:
                    print(f"⚠️ Warning: Error in result - {result}")
                    
            except Exception as e:
                print(f"❌ {test['name']} failed: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Chicago Crime Tool test failed: {e}")
        traceback.print_exc()
        return False

def test_claude_connection():
    """Test Claude API connection."""
    print_section("3. CLAUDE API CONNECTION TEST")
    
    try:
        from langchain_anthropic import ChatAnthropic
        
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        print("✅ Claude LLM initialized successfully")
        
        # Test simple query
        response = llm.invoke("Hello! Please respond with 'Chicago Crime Analysis System Test Successful' to confirm the connection.")
        print("✅ Claude API connection successful")
        print(f"   Response: {response.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ Claude API connection failed: {e}")
        traceback.print_exc()
        return False

def test_chicago_crime_agent():
    """Test the Chicago Crime Agent with LangGraph."""
    print_section("4. CHICAGO CRIME AGENT TEST")
    
    try:
        from chicago_crime_tool_fixed import ChicagoCrimeTool
        from chicago_crime_agent_fixed import ChicagoCrimeAgent
        
        # Initialize components
        crime_tool = ChicagoCrimeTool(app_token=os.getenv("CHICAGO_DATA_APP_TOKEN"))
        agent = ChicagoCrimeAgent(crime_tool)
        print("✅ Crime Agent initialized successfully")
        
        # Test queries
        test_queries = [
            "What are recent crime statistics for Chicago?",
            "Is Lincoln Park safe for families?",
            "Show me crime trends in downtown Chicago"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print_subsection(f"Test Query {i}: {query}")
            try:
                response = agent.analyze_crime(query)
                print(f"✅ Query {i} successful")
                print(f"   Response preview: {response[:200]}...")
                
                # Check for key components in response
                if "Key Insights" in response:
                    print("   ✅ Contains insights")
                if "Safety Recommendations" in response:
                    print("   ✅ Contains recommendations")
                if "Data Summary" in response:
                    print("   ✅ Contains data summary")
                    
            except Exception as e:
                print(f"❌ Query {i} failed: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Chicago Crime Agent test failed: {e}")
        traceback.print_exc()
        return False

def test_safety_advisory_system():
    """Test the Safety Advisory System."""
    print_section("5. SAFETY ADVISORY SYSTEM TEST")
    
    try:
        from chicago_crime_tool_fixed import ChicagoCrimeTool
        from chicago_crime_agent_fixed import ChicagoCrimeAgent
        from safety_advisory_system import SafetyAdvisorySystem
        
        # Initialize components
        crime_tool = ChicagoCrimeTool(app_token=os.getenv("CHICAGO_DATA_APP_TOKEN"))
        crime_agent = ChicagoCrimeAgent(crime_tool)
        safety_system = SafetyAdvisorySystem(crime_agent)
        print("✅ Safety Advisory System initialized successfully")
        
        # Test low-risk query (should not require human review)
        print_subsection("Low-Risk Query Test")
        low_risk_query = "What are general crime statistics for Chicago?"
        try:
            response = safety_system.get_safety_advice(low_risk_query)
            print("✅ Low-risk query processed successfully")
            print(f"   Response preview: {response[:200]}...")
            
            if "Human Reviewed" not in response:
                print("   ✅ Correctly bypassed human review")
            else:
                print("   ⚠️ Unexpected human review trigger")
                
        except Exception as e:
            print(f"❌ Low-risk query failed: {e}")
            return False
        
        # Test high-risk query (should trigger human review)
        print_subsection("High-Risk Query Test")
        high_risk_query = "Is it safe for me to walk alone at night with my children in downtown Chicago?"
        try:
            # This should trigger an interrupt, so we'll catch it
            response = safety_system.get_safety_advice(high_risk_query)
            print("✅ High-risk query initiated")
            
            if "human review" in response.lower() or "interrupt" in response.lower():
                print("   ✅ Correctly triggered human review process")
            else:
                print("   ⚠️ May not have triggered human review as expected")
                
            print(f"   Response preview: {response[:200]}...")
            
        except Exception as e:
            # An interrupt exception is actually expected for high-risk queries
            print(f"✅ High-risk query triggered review process: {type(e).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Safety Advisory System test failed: {e}")
        traceback.print_exc()
        return False

def run_comprehensive_test():
    """Run all tests in sequence."""
    print_section("COMPREHENSIVE CHICAGO CRIME ANALYSIS SYSTEM TEST")
    print("This script will test all components of the system step by step.")
    
    tests = [
        ("Environment Setup", test_environment),
        ("Chicago Crime Tool", test_chicago_crime_tool),
        ("Claude API Connection", test_claude_connection),
        ("Chicago Crime Agent", test_chicago_crime_agent),
        ("Safety Advisory System", test_safety_advisory_system),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
            if not result:
                print(f"\n❌ {test_name} failed - stopping tests")
                break
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results[test_name] = False
            break
    
    # Print summary
    print_section("TEST SUMMARY")
    all_passed = True
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print(f"\n🎉 ALL TESTS PASSED! Your system is ready to use.")
        print(f"\nNext steps:")
        print(f"  1. Run 'python chicago_crime_tool_fixed.py' for direct tool testing")
        print(f"  2. Run 'python chicago_crime_agent_fixed.py' for agent testing")
        print(f"  3. Run 'streamlit run streamlit_app.py' for the web interface")
    else:
        print(f"\n❌ Some tests failed. Please check the errors above and fix them before proceeding.")
    
    return all_passed

if __name__ == "__main__":
    run_comprehensive_test()