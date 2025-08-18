from langgraph.types import interrupt, Command
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from typing import Literal
from typing_extensions import TypedDict
from chicago_crime_agent_fixed import ChicagoCrimeAgent, ChicagoCrimeAgentState
import os
from dotenv import load_dotenv
import time
from datetime import datetime

# Import LangSmith observability
from langsmith_config import (
    observability, 
    trace_safety_advisory, 
    metrics_collector,
    evaluators
)

load_dotenv()

class SafetyAdvisoryState(TypedDict):
    """Extended state for safety advisory system."""
    messages: list
    crime_analysis: str
    is_high_risk: bool
    needs_human_review: bool
    human_feedback: str
    final_recommendations: str
    human_reviewed: bool
    escalation_reason: str

class SafetyAdvisorySystem:
    """Human-in-the-loop system for safety recommendations."""
    
    def __init__(self, crime_agent: ChicagoCrimeAgent):
        self.crime_agent = crime_agent
        self.graph = self._build_advisory_graph()
    
    def _build_advisory_graph(self):
        """Build graph with human review for safety recommendations."""
        
        def analyze_safety_request(state: SafetyAdvisoryState):
            """Initial analysis of safety request."""
            # Handle message object correctly
            latest_message = state["messages"][-1]
            if hasattr(latest_message, 'content'):
                query = latest_message.content
            elif isinstance(latest_message, dict):
                query = latest_message.get("content", "")
            else:
                query = str(latest_message)
            
            # Check if this is a high-risk query requiring human review
            high_risk_keywords = [
                "walking alone", "late night", "safety", "dangerous", "avoid",
                "moving", "living", "children", "family", "elderly", "vulnerable"
            ]
            
            is_high_risk = any(keyword in query.lower() for keyword in high_risk_keywords)
            
            # Get initial crime analysis
            try:
                crime_analysis = self.crime_agent.analyze_crime(query)
            except Exception as e:
                crime_analysis = f"Error getting crime analysis: {e}"
            
            return {
                "crime_analysis": crime_analysis,
                "is_high_risk": is_high_risk,
                "needs_human_review": is_high_risk,
                "human_feedback": "",
                "final_recommendations": "",
                "human_reviewed": False,
                "escalation_reason": ""
            }
        
        def human_safety_review(state: SafetyAdvisoryState) -> Command[Literal["deliver_recommendations", "modify_recommendations", "escalate_to_expert"]]:
            """Human review for safety-critical recommendations."""
            
            if not state["needs_human_review"]:
                return Command(goto="deliver_recommendations")
            
            # Interrupt for human review
            human_input = interrupt({
                "type": "safety_review",
                "query": state["messages"][-1]["content"] if isinstance(state["messages"][-1], dict) else state["messages"][-1].content,
                "analysis": state["crime_analysis"],
                "message": "Please review this safety analysis. Are the recommendations appropriate and complete?",
                "instructions": [
                    "Review the crime analysis for accuracy",
                    "Check if safety recommendations are appropriate",
                    "Ensure no harmful or misleading advice is given",
                    "Consider if additional warnings are needed"
                ],
                "options": {
                    "approve": "Approve recommendations as-is",
                    "modify": "Request modifications to recommendations", 
                    "escalate": "Escalate to safety expert"
                }
            })
            
            action = human_input.get("action", "approve")
            
            if action == "approve":
                return Command(goto="deliver_recommendations")
            elif action == "modify":
                return Command(
                    goto="modify_recommendations",
                    update={"human_feedback": human_input.get("feedback", "")}
                )
            else:  # escalate
                return Command(
                    goto="escalate_to_expert",
                    update={"escalation_reason": human_input.get("reason", "")}
                )
        
        def modify_recommendations(state: SafetyAdvisoryState):
            """Modify recommendations based on human feedback."""
            feedback = state.get("human_feedback", "")
            original_analysis = state["crime_analysis"]
            
            modified_prompt = f"""
            Original crime analysis:
            {original_analysis}
            
            Human reviewer feedback for modification:
            {feedback}
            
            Please revise the safety recommendations based on this feedback.
            Ensure all recommendations are:
            - Practical and specific
            - Actionable for the user
            - Appropriate for the risk level
            - Clear and easy to understand
            
            Maintain the same format but improve the content based on the feedback.
            """
            
            try:
                response = self.crime_agent.llm.invoke(modified_prompt)
                modified_recommendations = response.content
            except Exception as e:
                modified_recommendations = f"Error modifying recommendations: {e}\n\nOriginal analysis:\n{original_analysis}"
            
            return {
                "final_recommendations": modified_recommendations,
                "human_reviewed": True
            }
        
        def escalate_to_expert(state: SafetyAdvisoryState):
            """Escalate complex safety questions to domain experts."""
            # Handle message object correctly
            latest_message = state["messages"][-1]
            if hasattr(latest_message, 'content'):
                query_content = latest_message.content
            elif isinstance(latest_message, dict):
                query_content = latest_message.get("content", "")
            else:
                query_content = str(latest_message)
                
            escalation_msg = f"""
            🚨 **SAFETY QUERY ESCALATED TO EXPERT REVIEW** 🚨
            
            **Original Query**: {query_content}
            
            **Reason for Escalation**: {state.get('escalation_reason', 'Complex safety concern requiring expert input')}
            
            **Initial Analysis**: 
            {state['crime_analysis'][:500]}...
            
            ---
            
            **Next Steps**:
            This query requires expert review before providing safety recommendations. 
            Please contact appropriate resources:
            
            **For Immediate Safety Concerns**:
            - Emergency: 911
            - Chicago Police Non-Emergency: (312) 746-6000
            - Chicago 311 for city services: 311
            
            **For Community Safety Information**:
            - Chicago Police Community Relations: (312) 745-4420
            - Local Ward Office
            - Community Safety Organizations
            
            **For Housing/Moving Decisions**:
            - Local real estate professionals
            - Neighborhood association contacts
            - Community forums and local knowledge
            
            This automated system cannot provide expert-level safety advice for complex situations.
            """
            
            return {
                "final_recommendations": escalation_msg,
                "human_reviewed": True
            }
        
        def deliver_recommendations(state: SafetyAdvisoryState):
            """Deliver final safety recommendations with appropriate disclaimers."""
            
            if "final_recommendations" in state and state["final_recommendations"]:
                recommendations = state["final_recommendations"]
            else:
                recommendations = state["crime_analysis"]
            
            # Add comprehensive disclaimer
            disclaimer = """
            
            ---
            
            ⚠️ **IMPORTANT DISCLAIMERS**:
            
            • This analysis is based on publicly available data and should not be your only source for safety decisions
            • Crime data reflects reported incidents only and may not capture all safety considerations
            • Safety conditions can change rapidly and vary by specific location and time
            • Always trust your personal instincts and take appropriate precautions
            • For immediate safety concerns, contact emergency services (911)
            • Consider consulting local law enforcement, community organizations, or safety experts for personalized advice
            
            **Data Source**: Chicago Police Department via City of Chicago Data Portal
            **Last Updated**: Data reflects reported incidents with approximately 7-day delay
            """
            
            human_review_note = ""
            if state.get("human_reviewed"):
                human_review_note = "\n✅ **Human Reviewed**: This response has been reviewed by a human moderator.\n"
            
            final_response = recommendations + human_review_note + disclaimer
            
            # Return proper message object
            from langchain_core.messages import AIMessage
            return {
                "messages": [AIMessage(content=final_response)]
            }
        
        # Build the graph
        graph_builder = StateGraph(SafetyAdvisoryState)
        
        graph_builder.add_node("analyze_safety", analyze_safety_request)
        graph_builder.add_node("human_review", human_safety_review)
        graph_builder.add_node("modify_recommendations", modify_recommendations)
        graph_builder.add_node("escalate_to_expert", escalate_to_expert)
        graph_builder.add_node("deliver_recommendations", deliver_recommendations)
        
        graph_builder.add_edge(START, "analyze_safety")
        graph_builder.add_edge("analyze_safety", "human_review")
        graph_builder.add_edge("modify_recommendations", "deliver_recommendations")
        graph_builder.add_edge("escalate_to_expert", "deliver_recommendations")
        graph_builder.add_edge("deliver_recommendations", END)
        
        return graph_builder.compile(checkpointer=InMemorySaver())
    
    @trace_safety_advisory
    def get_safety_advice(self, user_query: str, thread_id: str = "default") -> str:
        """Get safety advice with human-in-the-loop review for high-risk queries."""
        config = {"configurable": {"thread_id": thread_id}}
        start_time = time.time()
        
        try:
            # Create proper message object
            from langchain_core.messages import HumanMessage
            
            # Run the safety advisory graph
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
            
            end_time = time.time()
            
            # Record safety advisory metrics
            metrics_collector.record_api_call(
                endpoint="safety_advisory_complete",
                success=True,
                response_time=end_time - start_time
            )
            
            # Run evaluations specific to safety advice
            self._run_safety_evaluations(user_query, response_content, result)
            
            return response_content
            
        except Exception as e:
            end_time = time.time()
            
            # Record failed safety advisory
            metrics_collector.record_api_call(
                endpoint="safety_advisory_complete",
                success=False,
                response_time=end_time - start_time
            )
            
            # Record anomaly
            metrics_collector.record_anomaly(
                anomaly_type="safety_advisory_failure",
                description=f"Safety advisory failed: {str(e)}",
                severity="high"
            )
            
            return f"Error in safety advisory system: {e}"
    
    def _run_safety_evaluations(self, user_query: str, response: str, result: dict):
        """Run safety-specific evaluations."""
        try:
            inputs = {"input": user_query}
            outputs = {"output": response}
            
            # Run safety appropriateness check
            safety_eval = evaluators.safety_appropriateness(inputs, outputs)
            if safety_eval["score"] < 0.7:
                metrics_collector.record_anomaly(
                    anomaly_type="inappropriate_safety_advice",
                    description=safety_eval["comment"],
                    severity="high"
                )
            
            # Check if human review was triggered
            if result.get("needs_human_review", False):
                metrics_collector.record_anomaly(
                    anomaly_type="human_review_triggered",
                    description=f"High-risk query required human review: {user_query[:100]}",
                    severity="medium"
                )
            
        except Exception as e:
            print(f"Safety evaluation failed: {e}")
    
    def handle_human_review_response(self, thread_id: str, action: str, feedback: str = ""):
        """Handle response from human reviewer."""
        config = {"configurable": {"thread_id": thread_id}}
        
        # Resume the graph with human input
        try:
            human_response = {
                "action": action,
                "feedback": feedback,
                "reason": feedback if action == "escalate" else ""
            }
            
            # Use Command to resume the interrupted graph
            result = self.graph.invoke(
                Command(resume=human_response),
                config
            )
            
            return result["messages"][-1]["content"]
            
        except Exception as e:
            return f"Error handling human review response: {e}"

# Test function
def test_safety_system():
    """Test the Safety Advisory System."""
    print("Testing Safety Advisory System...")
    
    try:
        from chicago_crime_tool_fixed import ChicagoCrimeTool
        
        # Initialize components
        crime_tool = ChicagoCrimeTool(app_token=os.getenv("CHICAGO_DATA_APP_TOKEN"))
        crime_agent = ChicagoCrimeAgent(crime_tool)
        safety_system = SafetyAdvisorySystem(crime_agent)
        
        # Test with a high-risk query
        response = safety_system.get_safety_advice(
            "Is it safe for me to walk alone at night in downtown Chicago with my children?"
        )
        
        print("✅ Safety system test initiated!")
        print("Response:")
        print(response)
        
    except Exception as e:
        print(f"❌ Safety system test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_safety_system()