import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

def test_environment():
    """Test environment setup."""
    print("🔍 Testing Environment Setup...")
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    chicago_token = os.getenv("CHICAGO_DATA_APP_TOKEN")
    
    print(f"Anthropic API Key: {'✅ Found' if anthropic_key else '❌ Missing'}")
    print(f"Chicago Data Token: {'✅ Found' if chicago_token else '⚠️ Optional but recommended'}")
    
    return anthropic_key is not None

def test_imports():
    """Test all imports work."""
    print("\n📦 Testing Imports...")
    
    try:
        from chicago_crime_tool import ChicagoCrimeTool
        print("✅ ChicagoCrimeTool imported successfully")
    except Exception as e:
        print(f"❌ ChicagoCrimeTool import failed: {e}")
        return False
    
    try:
        from chicago_agent import ChicagoCrimeAgent
        print("✅ ChicagoCrimeAgent imported successfully")
    except Exception as e:
        print(f"❌ ChicagoCrimeAgent import failed: {e}")
        return False
    
    return True

def test_basic_functionality():
    """Test basic functionality."""
    print("\n🔍 Testing Basic Functionality...")
    
    if not test_environment():
        print("❌ Environment setup incomplete")
        return
    
    if not test_imports():
        print("❌ Import errors - check your code")
        return
    
    from chicago_crime_tool import ChicagoCrimeTool
    from chicago_agent import ChicagoCrimeAgent
    
    # Test 1: Basic API connection
    print("\n1. Testing API connection...")
    try:
        crime_tool = ChicagoCrimeTool(app_token=os.getenv("CHICAGO_DATA_APP_TOKEN"))
        result = crime_tool._run(
            query_type="recent_crimes",
            limit=3
        )
        print("✅ API connection successful!")
        print(f"Sample data: {result[:300]}...")
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        print("Try running the tool test directly: python chicago_crime_tool.py")
        return
    
    # Test 2: Agent analysis
    print("\n2. Testing Agent analysis...")
    try:
        agent = ChicagoCrimeAgent(crime_tool)
        response = agent.analyze_crime("Show me recent crime statistics for Chicago")
        print("✅ Agent analysis successful!")
        print(f"Response preview: {response[:400]}...")
    except Exception as e:
        print(f"❌ Agent analysis failed: {e}")
        print("Try running the agent test directly: python chicago_agent.py")

if __name__ == "__main__":
    test_basic_functionality()
