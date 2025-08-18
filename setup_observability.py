"""
Setup script for LangSmith observability in Chicago Crime Project
Run this to configure and test the observability system
"""
import os
import sys
from dotenv import load_dotenv

def setup_langsmith():
    """Set up LangSmith configuration."""
    print("🔧 Setting up LangSmith Observability...")
    
    # Load environment variables
    load_dotenv()
    
    # Check required environment variables
    required_vars = {
        "ANTHROPIC_API_KEY": "Anthropic API key for Claude",
        "LANGCHAIN_API_KEY": "LangSmith API key for observability"
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"  - {var}: {description}")
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        print("\n".join(missing_vars))
        print("\nPlease add these to your .env file. See .env.example for template.")
        return False
    
    # Test LangSmith connection
    try:
        from langsmith import Client
        
        client = Client()
        
        # Try to create/access the project
        project_name = "chicago-crime-analysis"
        try:
            client.create_project(
                project_name=project_name,
                description="LLM observability for Chicago Crime Analysis System"
            )
            print(f"✅ Created LangSmith project: {project_name}")
        except Exception:
            print(f"✅ Connected to existing LangSmith project: {project_name}")
        
        print("✅ LangSmith connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ LangSmith connection failed: {e}")
        print("Please check your LANGCHAIN_API_KEY and network connection.")
        return False

def test_observability():
    """Test the observability system with a simple example."""
    print("\n🧪 Testing observability system...")
    
    try:
        from langsmith_config import metrics_collector, evaluators
        
        # Test metrics collection
        metrics_collector.record_api_call(
            endpoint="test_endpoint",
            success=True,
            response_time=0.5
        )
        
        metrics_collector.record_anomaly(
            anomaly_type="test_anomaly",
            description="This is a test anomaly",
            severity="low"
        )
        
        # Test evaluators
        test_inputs = {
            "input": "Is it safe to walk in downtown Chicago?",
            "crime_data": {"raw_data": "Sample crime data"}
        }
        test_outputs = {
            "output": "Based on the data, downtown Chicago has moderate safety levels. I recommend staying aware of your surroundings."
        }
        
        hallucination_result = evaluators.detect_hallucination(test_inputs, test_outputs)
        safety_result = evaluators.safety_appropriateness(test_inputs, test_outputs)
        
        print(f"✅ Hallucination Detection: Score {hallucination_result['score']}")
        print(f"✅ Safety Appropriateness: Score {safety_result['score']}")
        
        # Check metrics
        metrics = metrics_collector.get_metrics()
        print(f"✅ Collected {len(metrics)} test metrics")
        
        print("✅ Observability system test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Observability test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main setup function."""
    print("🚨 Chicago Crime Project - LangSmith Observability Setup")
    print("=" * 60)
    
    # Setup LangSmith
    if not setup_langsmith():
        print("\n❌ LangSmith setup failed. Please fix the issues above and try again.")
        return False
    
    # Test observability
    if not test_observability():
        print("\n❌ Observability test failed. Please check the error messages above.")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 LangSmith observability setup completed successfully!")
    print("\nNext steps:")
    print("1. Run your Streamlit app: streamlit run streamlit_app.py")
    print("2. Use the '📊 LLM Observability Dashboard' mode to view metrics")
    print("3. Check LangSmith web interface for detailed traces")
    print("4. Monitor for anomalies and evaluation results")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)