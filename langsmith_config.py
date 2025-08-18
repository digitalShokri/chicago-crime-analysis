"""
LangSmith Configuration and Observability Setup for Chicago Crime Project
"""
import os
from typing import Dict, Any, Optional, List
from langsmith import Client, traceable
from langsmith.run_helpers import trace
from datetime import datetime
import json


class LangSmithObservability:
    """Centralized LangSmith observability for the Chicago Crime project."""
    
    def __init__(self):
        self.client = None
        self.project_name = "chicago-crime-analysis"
        self.setup_langsmith()
    
    def setup_langsmith(self):
        """Initialize LangSmith client and configuration."""
        try:
            # Set up LangSmith environment variables
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = self.project_name
            
            # Initialize client
            self.client = Client()
            
            # Create project if it doesn't exist
            try:
                self.client.create_project(
                    project_name=self.project_name,
                    description="LLM observability for Chicago Crime Analysis System"
                )
            except Exception:
                # Project likely already exists
                pass
                
        except Exception as e:
            print(f"Warning: LangSmith setup failed: {e}")
            print("Continuing without LangSmith observability...")
    
    def get_tracer(self):
        """Get LangSmith tracer for manual tracing."""
        return self.client if self.client else None
    
    def log_run_metadata(self, run_id: str, metadata: Dict[str, Any]):
        """Log additional metadata to a run."""
        if self.client:
            try:
                self.client.update_run(run_id, extra=metadata)
            except Exception as e:
                print(f"Failed to log metadata: {e}")


# Custom evaluators for the Chicago Crime Analysis system
class CrimeAnalysisEvaluators:
    """Custom evaluators for detecting issues specific to crime analysis."""
    
    @staticmethod
    def detect_hallucination(inputs: Dict, outputs: Dict) -> Dict[str, Any]:
        """
        Evaluator to detect potential hallucinations in crime analysis.
        
        Flags responses that:
        1. Provide specific statistics without data source
        2. Make confident claims when API failed
        3. Contradict known crime data patterns
        """
        response = outputs.get("output", "").lower()
        crime_data = inputs.get("crime_data", {})
        
        score = 1.0  # Start with perfect score
        reasons = []
        
        # Check for API failure indicators
        if isinstance(crime_data.get("raw_data"), str) and "error" in crime_data.get("raw_data", "").lower():
            if any(phrase in response for phrase in ["statistics show", "data indicates", "according to records"]):
                score = 0.0
                reasons.append("Provides statistics despite API error")
        
        # Check for overconfident language without data
        overconfident_phrases = [
            "definitely safe", "completely safe", "no crime occurs",
            "never any problems", "absolutely secure", "zero risk"
        ]
        if any(phrase in response for phrase in overconfident_phrases):
            score = min(score, 0.3)
            reasons.append("Overconfident safety claims")
        
        # Check for specific numbers without data source
        import re
        if re.search(r'\d+%|\d+\s*(crimes?|incidents?)', response) and not crime_data.get("raw_data"):
            score = min(score, 0.5)
            reasons.append("Specific statistics without data")
        
        return {
            "key": "hallucination_detection",
            "score": score,
            "value": score,
            "comment": "; ".join(reasons) if reasons else "No hallucination detected",
            "correction": None if score > 0.7 else "Response should acknowledge data limitations"
        }
    
    @staticmethod
    def check_consistency(inputs: Dict, outputs: Dict) -> Dict[str, Any]:
        """
        Evaluator to check consistency of responses for similar queries.
        This would need to be implemented with a cache of previous responses.
        """
        # Placeholder implementation - would need conversation history
        return {
            "key": "consistency_check",
            "score": 1.0,
            "value": 1.0,
            "comment": "Consistency check requires conversation history",
            "correction": None
        }
    
    @staticmethod
    def safety_appropriateness(inputs: Dict, outputs: Dict) -> Dict[str, Any]:
        """
        Evaluator to check if safety advice is appropriate and balanced.
        """
        response = outputs.get("output", "").lower()
        score = 1.0
        reasons = []
        
        # Check for balanced safety advice
        if "safety" in inputs.get("input", "").lower():
            if not any(phrase in response for phrase in ["recommend", "suggest", "consider", "be aware"]):
                score = min(score, 0.6)
                reasons.append("Missing actionable safety recommendations")
            
            if not any(phrase in response for phrase in ["judgment", "caution", "aware", "alert"]):
                score = min(score, 0.7)
                reasons.append("Missing safety awareness language")
        
        return {
            "key": "safety_appropriateness",
            "score": score,
            "value": score,
            "comment": "; ".join(reasons) if reasons else "Appropriate safety advice",
            "correction": None if score > 0.7 else "Add balanced safety recommendations"
        }


# Decorator functions for easy tracing
def trace_crime_analysis(func):
    """Decorator to trace crime analysis functions."""
    def wrapper(*args, **kwargs):
        with trace(
            name=f"crime_analysis_{func.__name__}",
            project_name="chicago-crime-analysis",
            tags=["crime_analysis", "llm_call"]
        ) as run:
            try:
                result = func(*args, **kwargs)
                
                # Add custom metrics
                if hasattr(result, 'usage_metadata'):
                    run.end(
                        outputs={"result": str(result)},
                        extra={
                            "token_usage": getattr(result, 'usage_metadata', {}),
                            "model": "claude-3-5-sonnet",
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                else:
                    run.end(outputs={"result": str(result)})
                
                return result
            except Exception as e:
                run.end(error=str(e))
                raise
    
    return wrapper


def trace_safety_advisory(func):
    """Decorator to trace safety advisory functions."""
    def wrapper(*args, **kwargs):
        with trace(
            name=f"safety_advisory_{func.__name__}",
            project_name="chicago-crime-analysis",
            tags=["safety_advisory", "human_review", "llm_call"]
        ) as run:
            try:
                result = func(*args, **kwargs)
                
                # Check if human review was triggered
                human_review_triggered = "human review" in str(result).lower()
                
                run.end(
                    outputs={"result": str(result)},
                    extra={
                        "human_review_triggered": human_review_triggered,
                        "safety_category": True,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                return result
            except Exception as e:
                run.end(error=str(e))
                raise
    
    return wrapper


# Metrics collection utilities
class MetricsCollector:
    """Collect and track custom metrics for the crime analysis system."""
    
    def __init__(self):
        self.metrics = []
    
    def record_api_call(self, endpoint: str, success: bool, response_time: float):
        """Record Chicago Police API call metrics."""
        self.metrics.append({
            "type": "api_call",
            "endpoint": endpoint,
            "success": success,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat()
        })
    
    def record_user_satisfaction(self, query: str, response: str, rating: int):
        """Record user satisfaction metrics."""
        self.metrics.append({
            "type": "user_satisfaction",
            "query": query,
            "response_length": len(response),
            "rating": rating,
            "timestamp": datetime.now().isoformat()
        })
    
    def record_anomaly(self, anomaly_type: str, description: str, severity: str):
        """Record detected anomalies."""
        self.metrics.append({
            "type": "anomaly",
            "anomaly_type": anomaly_type,
            "description": description,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_metrics(self, exclude_test_data: bool = True) -> List[Dict]:
        """Get all collected metrics."""
        if exclude_test_data:
            # Filter out test data based on common test patterns
            filtered_metrics = []
            test_patterns = [
                "test_endpoint",
                "test_anomaly", 
                "Is it safe to walk in downtown Chicago",
                "Show me crime trends in downtown Chicago"
            ]
            
            for metric in self.metrics:
                is_test_data = False
                metric_str = str(metric).lower()
                
                for pattern in test_patterns:
                    if pattern.lower() in metric_str:
                        is_test_data = True
                        break
                
                if not is_test_data:
                    filtered_metrics.append(metric)
            
            return filtered_metrics
        
        return self.metrics.copy()
    
    def clear_test_data(self):
        """Clear test data from metrics."""
        self.metrics = self.get_metrics(exclude_test_data=True)
    
    def clear_all_metrics(self):
        """Clear all metrics."""
        self.metrics = []


# Global instances
observability = LangSmithObservability()
evaluators = CrimeAnalysisEvaluators()
metrics_collector = MetricsCollector()