from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_anthropic import ChatAnthropic
from typing_extensions import TypedDict
from typing import Annotated, List, Optional
import json
import os
from dotenv import load_dotenv
import time
from datetime import datetime

# Import our custom tool and LangSmith observability
from chicago_crime_tool_optimized import ChicagoCrimeTool
from langsmith_config import (
    observability, 
    trace_crime_analysis, 
    metrics_collector,
    evaluators
)

load_dotenv()

class ChicagoCrimeAgentState(TypedDict):
    """State for Chicago Crime Analysis Agent."""
    messages: Annotated[list, add_messages]
    user_location: str
    analysis_type: str
    crime_data: dict
    insights: List[str]
    recommendations: List[str]

class ChicagoCrimeAgent:
    """Intelligent agent for Chicago crime data analysis using LangGraph."""
    
    def __init__(self, chicago_crime_tool: ChicagoCrimeTool):
        self.crime_tool = chicago_crime_tool
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        def analyze_request_node(state: ChicagoCrimeAgentState):
            """Analyze the user's request to determine what kind of crime analysis they need."""
            messages = state["messages"]
            # Fix: Handle both dict and Message object formats
            if messages:
                latest_message = messages[-1]
                if hasattr(latest_message, 'content'):
                    # It's a Message object
                    latest_message_content = latest_message.content
                elif isinstance(latest_message, dict):
                    # It's a dictionary
                    latest_message_content = latest_message.get("content", "")
                else:
                    latest_message_content = str(latest_message)
            else:
                latest_message_content = ""
            
            # Use Claude to categorize the request
            analysis_prompt = f"""
            Analyze this user request about Chicago crime data: "{latest_message_content}"
            
            Determine:
            1. What type of analysis they want (recent_crimes, crime_stats, location_analysis, trend_analysis)
            2. Any specific location mentioned (neighborhood, address, ward)
            3. Any specific crime types mentioned
            4. Time period of interest - DEFAULT to last_7_days unless they specifically ask for longer periods
            
            Time period guidelines:
            - Use "last_7_days" for recent activity, current conditions, or no time specified
            - Use "last_30_days" if they ask for "monthly", "past month", or "recent trends"
            - Use "last_year" only if they specifically ask for "yearly", "annual", or "long-term trends"
            
            Return JSON format:
            {{
                "analysis_type": "recent_crimes|crime_stats|location_analysis|trend_analysis",
                "location": "extracted location or empty string",
                "crime_type": "extracted crime type or empty string",
                "time_period": "last_7_days|last_30_days|last_year"
            }}
            """
            
            try:
                start_time = time.time()
                response = self.llm.invoke(analysis_prompt)
                end_time = time.time()
                
                # Record metrics
                metrics_collector.record_api_call(
                    endpoint="claude_analysis", 
                    success=True, 
                    response_time=end_time - start_time
                )
                
                # Extract JSON from response
                response_text = response.content
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    analysis = json.loads(json_str)
                else:
                    # Fallback analysis
                    analysis = {
                        "analysis_type": "crime_stats",
                        "location": "",
                        "crime_type": "",
                        "time_period": "last_7_days"
                    }
                
                return {
                    "analysis_type": analysis.get("analysis_type", "crime_stats"),
                    "user_location": analysis.get("location", ""),
                    "crime_data": {},
                    "insights": [],
                    "recommendations": []
                }
                
            except Exception as e:
                print(f"Error in analyze_request_node: {e}")
                # Record failed API call
                metrics_collector.record_api_call(
                    endpoint="claude_analysis", 
                    success=False, 
                    response_time=0
                )
                return {
                    "analysis_type": "crime_stats",
                    "user_location": "",
                    "crime_data": {},
                    "insights": [],
                    "recommendations": []
                }
        
        def fetch_crime_data_node(state: ChicagoCrimeAgentState):
            """Fetch relevant crime data from Chicago database."""
            try:
                # Build parameters for optimized tool (no date_range)
                params = {
                    "query_type": state["analysis_type"],
                    "limit": 100  # Reduced for better performance
                }
                
                if state["user_location"]:
                    params["location"] = state["user_location"]
                
                crime_data = self.crime_tool._run(**params)
                
                return {"crime_data": {"raw_data": crime_data}}
                
            except Exception as e:
                error_data = f"Error fetching crime data: {e}"
                return {"crime_data": {"raw_data": error_data}}
        
        def generate_insights_node(state: ChicagoCrimeAgentState):
            """Generate insights from the crime data."""
            crime_data = state["crime_data"]["raw_data"]
            
            insights_prompt = f"""
            Based on this Chicago crime data:
            {crime_data}
            
            Generate 3-5 key insights about:
            - Crime patterns and trends
            - Safety considerations
            - Notable statistics
            
            Return each insight on a separate line, starting with a bullet point.
            Keep insights concise and actionable.
            """
            
            try:
                start_time = time.time()
                response = self.llm.invoke(insights_prompt)
                end_time = time.time()
                
                # Record metrics
                metrics_collector.record_api_call(
                    endpoint="claude_insights", 
                    success=True, 
                    response_time=end_time - start_time
                )
                
                insights_text = response.content
                
                # Parse insights from response
                insights = []
                for line in insights_text.split('\n'):
                    line = line.strip()
                    if line and (line.startswith('•') or line.startswith('-') or line.startswith('*')):
                        # Remove bullet point and clean up
                        insight = line[1:].strip()
                        if insight:
                            insights.append(insight)
                
                # Fallback if no properly formatted insights found
                if not insights:
                    insights = [insights_text.strip()[:200] + "..."]
                
                return {"insights": insights[:5]}  # Limit to 5 insights
                
            except Exception as e:
                # Record failed API call
                metrics_collector.record_api_call(
                    endpoint="claude_insights", 
                    success=False, 
                    response_time=0
                )
                return {"insights": [f"Error generating insights: {e}"]}
        
        def generate_recommendations_node(state: ChicagoCrimeAgentState):
            """Generate safety recommendations based on the analysis."""
            crime_data = state["crime_data"]["raw_data"]
            insights = state["insights"]
            location = state["user_location"]
            
            recommendations_prompt = f"""
            Based on this crime analysis for {location or 'Chicago'}:
            
            Crime Data: {crime_data}
            Key Insights: {', '.join(insights)}
            
            Generate 3-5 practical safety recommendations for residents or visitors.
            Focus on actionable advice they can follow.
            
            Return each recommendation on a separate line, starting with a bullet point.
            Keep recommendations specific and practical.
            """
            
            try:
                start_time = time.time()
                response = self.llm.invoke(recommendations_prompt)
                end_time = time.time()
                
                # Record metrics
                metrics_collector.record_api_call(
                    endpoint="claude_recommendations", 
                    success=True, 
                    response_time=end_time - start_time
                )
                
                recommendations_text = response.content
                
                # Parse recommendations from response
                recommendations = []
                for line in recommendations_text.split('\n'):
                    line = line.strip()
                    if line and (line.startswith('•') or line.startswith('-') or line.startswith('*')):
                        # Remove bullet point and clean up
                        rec = line[1:].strip()
                        if rec:
                            recommendations.append(rec)
                
                # Fallback if no properly formatted recommendations found
                if not recommendations:
                    recommendations = [recommendations_text.strip()[:200] + "..."]
                
                return {"recommendations": recommendations[:5]}
                
            except Exception as e:
                # Record failed API call
                metrics_collector.record_api_call(
                    endpoint="claude_recommendations", 
                    success=False, 
                    response_time=0
                )
                return {"recommendations": [f"Error generating recommendations: {e}"]}
        
        def format_response_node(state: ChicagoCrimeAgentState):
            """Format the final response for the user."""
            location_text = f" in {state['user_location']}" if state['user_location'] else ""
            
            response = f"# Chicago Crime Analysis{location_text}\n\n"
            
            if state["insights"]:
                response += "## 🔍 Key Insights\n"
                for insight in state["insights"]:
                    response += f"• {insight}\n"
                response += "\n"
            
            if state["recommendations"]:
                response += "## 🛡️ Safety Recommendations\n"
                for rec in state["recommendations"]:
                    response += f"• {rec}\n"
                response += "\n"
            
            response += "## 📊 Data Summary\n"
            response += f"```\n{state['crime_data']['raw_data'][:1000]}...\n```\n"
            
            response += "\n⚠️ **Disclaimer**: This analysis is based on publicly available data and should supplement, not replace, your own safety judgment."
            
            # Return as a proper message object
            from langchain_core.messages import AIMessage
            return {"messages": [AIMessage(content=response)]}
        
        # Build the graph
        graph_builder = StateGraph(ChicagoCrimeAgentState)
        
        # Add nodes
        graph_builder.add_node("analyze_request", analyze_request_node)
        graph_builder.add_node("fetch_data", fetch_crime_data_node)
        graph_builder.add_node("generate_insights", generate_insights_node)
        graph_builder.add_node("generate_recommendations", generate_recommendations_node)
        graph_builder.add_node("format_response", format_response_node)
        
        # Add edges
        graph_builder.add_edge(START, "analyze_request")
        graph_builder.add_edge("analyze_request", "fetch_data")
        graph_builder.add_edge("fetch_data", "generate_insights")
        graph_builder.add_edge("generate_insights", "generate_recommendations")
        graph_builder.add_edge("generate_recommendations", "format_response")
        graph_builder.add_edge("format_response", END)
        
        # Compile with memory
        memory = InMemorySaver()
        return graph_builder.compile(checkpointer=memory)
    
    @trace_crime_analysis
    def analyze_crime(self, user_query: str, thread_id: str = "default") -> str:
        """Analyze Chicago crime data based on user query."""
        config = {"configurable": {"thread_id": thread_id}}
        start_time = time.time()
        
        try:
            # Create proper message object
            from langchain_core.messages import HumanMessage
            
            # Run the graph
            result = self.graph.invoke(
                {"messages": [HumanMessage(content=user_query)]},
                config
            )
            
            # Extract content from the result message
            final_message = result["messages"][-1]
            if hasattr(final_message, 'content'):
                response_content = final_message.content
            elif isinstance(final_message, dict):
                response_content = result.get("content", "No response generated")
            else:
                response_content = str(final_message)
            
            # Run evaluations
            self._run_evaluations(user_query, response_content, result)
            
            end_time = time.time()
            
            # Record overall analysis metrics
            metrics_collector.record_api_call(
                endpoint="crime_analysis_complete",
                success=True,
                response_time=end_time - start_time
            )
            
            return response_content
            
        except Exception as e:
            end_time = time.time()
            
            # Record failed analysis
            metrics_collector.record_api_call(
                endpoint="crime_analysis_complete",
                success=False,
                response_time=end_time - start_time
            )
            
            # Record anomaly
            metrics_collector.record_anomaly(
                anomaly_type="analysis_failure",
                description=f"Crime analysis failed: {str(e)}",
                severity="high"
            )
            
            return f"Error in crime analysis: {e}"
    
    def _run_evaluations(self, user_query: str, response: str, result: dict):
        """Run custom evaluations on the analysis result."""
        try:
            inputs = {
                "input": user_query,
                "crime_data": result.get("crime_data", {})
            }
            outputs = {"output": response}
            
            # Run hallucination detection
            hallucination_eval = evaluators.detect_hallucination(inputs, outputs)
            if hallucination_eval["score"] < 0.7:
                metrics_collector.record_anomaly(
                    anomaly_type="potential_hallucination",
                    description=hallucination_eval["comment"],
                    severity="high" if hallucination_eval["score"] < 0.3 else "medium"
                )
            
            # Run safety appropriateness check
            safety_eval = evaluators.safety_appropriateness(inputs, outputs)
            if safety_eval["score"] < 0.7:
                metrics_collector.record_anomaly(
                    anomaly_type="inappropriate_safety_advice",
                    description=safety_eval["comment"],
                    severity="medium"
                )
            
        except Exception as e:
            print(f"Evaluation failed: {e}")

# Test function
def test_agent():
    """Test the Chicago Crime Agent."""
    print("Testing Chicago Crime Agent...")
    
    try:
        # Initialize components
        crime_tool = ChicagoCrimeTool(app_token=os.getenv("CHICAGO_DATA_APP_TOKEN"))
        agent = ChicagoCrimeAgent(crime_tool)
        
        # Test query
        response = agent.analyze_crime(
            "What are the recent crime trends in Lincoln Park? I'm considering moving there."
        )
        
        print("✅ Agent test successful!")
        print("Response:")
        print(response)
        
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_agent()