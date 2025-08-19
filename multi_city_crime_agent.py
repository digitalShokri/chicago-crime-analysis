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

# Import city-specific tools
from chicago_crime_tool_optimized import ChicagoCrimeTool
from dallas_crime_tool_optimized import DallasCrimeTool

from langsmith_config import (
    observability, 
    trace_crime_analysis, 
    metrics_collector,
    evaluators
)

load_dotenv()

class MultiCityCrimeAgentState(TypedDict):
    """State for Multi-City Crime Analysis Agent."""
    messages: Annotated[list, add_messages]
    selected_city: str
    user_location: str
    analysis_type: str
    crime_data: dict
    insights: List[str]
    recommendations: List[str]

class MultiCityCrimeAgent:
    """Intelligent agent for multi-city crime data analysis using LangGraph."""
    
    def __init__(self):
        # Initialize city-specific tools
        self.chicago_tool = ChicagoCrimeTool(app_token=os.getenv("CHICAGO_DATA_APP_TOKEN"))
        self.dallas_tool = DallasCrimeTool(app_token=os.getenv("DALLAS_DATA_APP_TOKEN"))
        
        self.tools = {
            "chicago": self.chicago_tool,
            "dallas": self.dallas_tool
        }
        
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        def analyze_request_node(state: MultiCityCrimeAgentState):
            """Analyze the user's request to determine city and analysis type."""
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
            
            # Use Claude to categorize the request and determine city preference
            analysis_prompt = f"""
            Analyze this user request about crime data: "{latest_message_content}"
            
            Determine:
            1. What type of analysis they want (recent_crimes, crime_stats, location_analysis)
            2. Any specific location mentioned (neighborhood, address, ward, beat, sector)
            3. Any specific crime types mentioned
            4. Which city they're asking about (look for "Chicago", "Dallas", or context clues)
            
            Return JSON format:
            {{
                "analysis_type": "recent_crimes|crime_stats|location_analysis",
                "location": "extracted location or empty string",
                "crime_type": "extracted crime type or empty string",
                "suggested_city": "chicago|dallas|unknown"
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
                        "suggested_city": "chicago"  # Default to Chicago
                    }
                
                print(f"[DEBUG] Parsed analysis request: {analysis}")
                
                # Use selected city from state, or fall back to suggestion
                selected_city = state.get("selected_city", analysis.get("suggested_city", "chicago"))
                
                return {
                    "analysis_type": analysis.get("analysis_type", "crime_stats"),
                    "user_location": analysis.get("location", ""),
                    "selected_city": selected_city,
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
                    "selected_city": state.get("selected_city", "chicago"),
                    "crime_data": {},
                    "insights": [],
                    "recommendations": []
                }
        
        def fetch_crime_data_node(state: MultiCityCrimeAgentState):
            """Fetch relevant crime data from the selected city's database."""
            try:
                selected_city = state["selected_city"]
                crime_tool = self.tools.get(selected_city)
                
                if not crime_tool:
                    error_msg = f"City '{selected_city}' is not supported. Available cities: {list(self.tools.keys())}"
                    return {"crime_data": {"raw_data": error_msg}}
                
                # Build parameters for the selected city's tool
                params = {
                    "query_type": state["analysis_type"],
                    "limit": 100  # Reduced for better performance
                }
                
                # Only add location if it exists
                if state["user_location"]:
                    params["location"] = state["user_location"]
                
                print(f"[DEBUG] Calling {selected_city} crime tool with params: {params}")
                
                # Call the appropriate city's tool
                crime_data = crime_tool._run(**params)
                
                print(f"[DEBUG] {selected_city.title()} tool response: {type(crime_data)} - {str(crime_data)[:200]}...")
                
                return {"crime_data": {"raw_data": crime_data, "city": selected_city}}
                
            except Exception as e:
                error_data = f"Error fetching crime data from {state.get('selected_city', 'unknown')}: {e}"
                print(f"[ERROR] Crime data fetch failed: {error_data}")
                import traceback
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
                return {"crime_data": {"raw_data": error_data, "city": state.get("selected_city", "unknown")}}
        
        def generate_insights_node(state: MultiCityCrimeAgentState):
            """Generate insights from the crime data."""
            crime_data = state["crime_data"]["raw_data"]
            city = state["crime_data"].get("city", state.get("selected_city", "unknown"))
            
            insights_prompt = f"""
            Based on this {city.title()} crime data:
            {crime_data}
            
            Generate 3-5 key insights about:
            - Crime patterns and trends in {city.title()}
            - Safety considerations specific to {city.title()}
            - Notable statistics from the data
            
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
        
        def generate_recommendations_node(state: MultiCityCrimeAgentState):
            """Generate safety recommendations based on the analysis."""
            crime_data = state["crime_data"]["raw_data"]
            insights = state["insights"]
            location = state["user_location"]
            city = state["crime_data"].get("city", state.get("selected_city", "unknown"))
            
            location_text = f" in {location}, {city.title()}" if location else f" in {city.title()}"
            
            recommendations_prompt = f"""
            Based on this crime analysis for{location_text}:
            
            Crime Data: {crime_data}
            Key Insights: {', '.join(insights)}
            
            Generate 3-5 practical safety recommendations for residents or visitors to {city.title()}.
            Focus on actionable advice specific to {city.title()}'s crime patterns.
            
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
        
        def format_response_node(state: MultiCityCrimeAgentState):
            """Format the final response for the user."""
            city = state["crime_data"].get("city", state.get("selected_city", "unknown"))
            location_text = f" in {state['user_location']}" if state['user_location'] else ""
            
            response = f"# {city.title()} Crime Analysis{location_text}\n\n"
            
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
            
            response += f"\n⚠️ **Disclaimer**: This analysis is based on publicly available {city.title()} data and should supplement, not replace, your own safety judgment."
            
            # Return as a proper message object
            from langchain_core.messages import AIMessage
            return {"messages": [AIMessage(content=response)]}
        
        # Build the graph
        graph_builder = StateGraph(MultiCityCrimeAgentState)
        
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
    def analyze_crime(self, user_query: str, selected_city: str = "chicago", thread_id: str = "default") -> str:
        """Analyze crime data for the selected city based on user query."""
        config = {"configurable": {"thread_id": thread_id}}
        start_time = time.time()
        
        try:
            # Create proper message object
            from langchain_core.messages import HumanMessage
            
            # Run the graph with city selection
            result = self.graph.invoke(
                {
                    "messages": [HumanMessage(content=user_query)],
                    "selected_city": selected_city
                },
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
            self._run_evaluations(user_query, response_content, result, selected_city)
            
            end_time = time.time()
            
            # Record overall analysis metrics
            metrics_collector.record_api_call(
                endpoint=f"{selected_city}_crime_analysis_complete",
                success=True,
                response_time=end_time - start_time
            )
            
            return response_content
            
        except Exception as e:
            end_time = time.time()
            
            # Record failed analysis
            metrics_collector.record_api_call(
                endpoint=f"{selected_city}_crime_analysis_complete",
                success=False,
                response_time=end_time - start_time
            )
            
            # Record anomaly
            metrics_collector.record_anomaly(
                anomaly_type="analysis_failure",
                description=f"{selected_city.title()} crime analysis failed: {str(e)}",
                severity="high"
            )
            
            return f"Error in {selected_city} crime analysis: {e}"
    
    def _run_evaluations(self, user_query: str, response: str, result: dict, city: str):
        """Run custom evaluations on the analysis result."""
        try:
            inputs = {
                "input": user_query,
                "crime_data": result.get("crime_data", {}),
                "city": city
            }
            outputs = {"output": response}
            
            # Run hallucination detection
            hallucination_eval = evaluators.detect_hallucination(inputs, outputs)
            if hallucination_eval["score"] < 0.7:
                metrics_collector.record_anomaly(
                    anomaly_type="potential_hallucination",
                    description=f"{city}: {hallucination_eval['comment']}",
                    severity="high" if hallucination_eval["score"] < 0.3 else "medium"
                )
            
            # Run safety appropriateness check
            safety_eval = evaluators.safety_appropriateness(inputs, outputs)
            if safety_eval["score"] < 0.7:
                metrics_collector.record_anomaly(
                    anomaly_type="inappropriate_safety_advice",
                    description=f"{city}: {safety_eval['comment']}",
                    severity="medium"
                )
            
        except Exception as e:
            print(f"Evaluation failed: {e}")
    
    def get_supported_cities(self) -> List[str]:
        """Get list of supported cities."""
        return list(self.tools.keys())

# Test function
def test_agent():
    """Test the Multi-City Crime Agent."""
    print("Testing Multi-City Crime Agent...")
    
    try:
        # Initialize agent
        print("[DEBUG] Initializing multi-city agent...")
        agent = MultiCityCrimeAgent()
        print("[DEBUG] Agent initialized successfully")
        print(f"[DEBUG] Supported cities: {agent.get_supported_cities()}")
        
        # Test Chicago query
        print("\n[DEBUG] Testing Chicago analysis...")
        response = agent.analyze_crime(
            "What are the recent crime trends in Lincoln Park? I'm considering moving there.",
            selected_city="chicago"
        )
        print("✅ Chicago test successful!")
        print("Response:", response[:300] + "..." if len(response) > 300 else response)
        
        # Test Dallas query
        print("\n[DEBUG] Testing Dallas analysis...")
        response = agent.analyze_crime(
            "What are the crime statistics in downtown Dallas?",
            selected_city="dallas"
        )
        print("✅ Dallas test successful!")
        print("Response:", response[:300] + "..." if len(response) > 300 else response)
        
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        import traceback
        print(f"[ERROR] Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_agent()