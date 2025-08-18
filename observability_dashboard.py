"""
LangSmith Observability Dashboard for Chicago Crime Project
Provides monitoring, metrics visualization, and anomaly detection
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from typing import List, Dict, Any

# Try importing plotly, fallback if not available
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("Plotly not available. Install with: pip install plotly")

# Import LangSmith components with error handling
try:
    from langsmith_config import metrics_collector, observability, evaluators
    LANGSMITH_AVAILABLE = True
except ImportError as e:
    LANGSMITH_AVAILABLE = False
    st.error(f"LangSmith config import failed: {e}")
except Exception as e:
    LANGSMITH_AVAILABLE = False
    st.error(f"LangSmith config error: {e}")


class ObservabilityDashboard:
    """Dashboard for monitoring LLM observability metrics."""
    
    def __init__(self):
        if LANGSMITH_AVAILABLE:
            self.metrics_collector = metrics_collector
        else:
            self.metrics_collector = None
    
    def render_dashboard(self):
        """Render the complete observability dashboard."""
        st.title("🔍 LLM Observability Dashboard")
        st.markdown("Monitor LLM performance, detect anomalies, and track usage metrics")
        
        # Check if system is properly configured
        if not LANGSMITH_AVAILABLE:
            st.error("❌ LangSmith configuration not available. Please check your setup.")
            st.info("Run `python setup_observability.py` to configure the system.")
            return
        
        if not self.metrics_collector:
            st.error("❌ Metrics collector not initialized.")
            return
        
        # Sidebar for controls
        st.sidebar.header("📊 Dashboard Controls")
        refresh_data = st.sidebar.button("🔄 Refresh Data")
        
        # Clear test data button
        if st.sidebar.button("🧹 Clear Test Data"):
            self.metrics_collector.clear_test_data()
            st.sidebar.success("Test data cleared!")
            st.experimental_rerun()
        
        # Show test data toggle
        show_test_data = st.sidebar.checkbox("Show Test Data", value=False)
        
        time_filter = st.sidebar.selectbox(
            "Time Range:",
            ["Last Hour", "Last 24 Hours", "Last 7 Days", "All Time"]
        )
        
        # Main dashboard tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Overview", 
            "🚨 Anomalies", 
            "⚡ Performance", 
            "💰 Usage & Costs",
            "🎯 Evaluations"
        ])
        
        with tab1:
            self.render_overview_tab(show_test_data)
        
        with tab2:
            self.render_anomalies_tab(show_test_data)
        
        with tab3:
            self.render_performance_tab(show_test_data)
        
        with tab4:
            self.render_usage_costs_tab(show_test_data)
        
        with tab5:
            self.render_evaluations_tab()
    
    def render_overview_tab(self, show_test_data=False):
        """Render overview metrics."""
        st.header("📊 System Overview")
        
        metrics = self.metrics_collector.get_metrics(exclude_test_data=not show_test_data)
        
        if not metrics:
            st.info("No metrics data available yet. Run some queries to see metrics.")
            return
        
        # Key metrics cards
        col1, col2, col3, col4 = st.columns(4)
        
        total_calls = len([m for m in metrics if m["type"] == "api_call"])
        successful_calls = len([m for m in metrics if m["type"] == "api_call" and m["success"]])
        total_anomalies = len([m for m in metrics if m["type"] == "anomaly"])
        avg_response_time = self._calculate_avg_response_time(metrics)
        
        with col1:
            st.metric("Total LLM Calls", total_calls)
        
        with col2:
            success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
            st.metric("Success Rate", f"{success_rate:.1f}%")
        
        with col3:
            st.metric("Anomalies Detected", total_anomalies)
        
        with col4:
            st.metric("Avg Response Time", f"{avg_response_time:.2f}s")
        
        # Recent activity
        st.subheader("📝 Recent Activity")
        recent_metrics = sorted(metrics, key=lambda x: x["timestamp"], reverse=True)[:10]
        
        activity_data = []
        for metric in recent_metrics:
            activity_data.append({
                "Time": metric["timestamp"],
                "Type": metric["type"],
                "Endpoint": metric.get("endpoint", metric.get("anomaly_type", "N/A")),
                "Status": "✅ Success" if metric.get("success", True) else "❌ Failed"
            })
        
        if activity_data:
            st.dataframe(pd.DataFrame(activity_data), use_container_width=True)
    
    def render_anomalies_tab(self, show_test_data=False):
        """Render anomalies monitoring."""
        st.header("🚨 Anomaly Detection")
        
        metrics = self.metrics_collector.get_metrics(exclude_test_data=not show_test_data)
        anomalies = [m for m in metrics if m["type"] == "anomaly"]
        
        if not anomalies:
            st.success("🎉 No anomalies detected!")
            return
        
        # Anomaly severity breakdown
        col1, col2 = st.columns(2)
        
        with col1:
            severity_counts = {}
            for anomaly in anomalies:
                severity = anomaly.get("severity", "unknown")
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            if severity_counts:
                if PLOTLY_AVAILABLE:
                    fig = px.pie(
                        values=list(severity_counts.values()),
                        names=list(severity_counts.keys()),
                        title="Anomalies by Severity"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.write("**Anomalies by Severity:**")
                    for severity, count in severity_counts.items():
                        st.write(f"- {severity}: {count}")
        
        with col2:
            anomaly_types = {}
            for anomaly in anomalies:
                atype = anomaly.get("anomaly_type", "unknown")
                anomaly_types[atype] = anomaly_types.get(atype, 0) + 1
            
            if anomaly_types:
                if PLOTLY_AVAILABLE:
                    fig = px.bar(
                        x=list(anomaly_types.keys()),
                        y=list(anomaly_types.values()),
                        title="Anomalies by Type"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.write("**Anomalies by Type:**")
                    for atype, count in anomaly_types.items():
                        st.write(f"- {atype}: {count}")
        
        # Detailed anomaly list
        st.subheader("🔍 Anomaly Details")
        
        anomaly_data = []
        for anomaly in sorted(anomalies, key=lambda x: x["timestamp"], reverse=True):
            severity_icon = {
                "high": "🔴",
                "medium": "🟡", 
                "low": "🟢"
            }.get(anomaly.get("severity", "unknown"), "⚪")
            
            anomaly_data.append({
                "Time": anomaly["timestamp"],
                "Severity": f"{severity_icon} {anomaly.get('severity', 'unknown').title()}",
                "Type": anomaly.get("anomaly_type", "unknown"),
                "Description": anomaly.get("description", "No description")
            })
        
        if anomaly_data:
            st.dataframe(pd.DataFrame(anomaly_data), use_container_width=True)
    
    def render_performance_tab(self, show_test_data=False):
        """Render performance metrics."""
        st.header("⚡ Performance Monitoring")
        
        metrics = self.metrics_collector.get_metrics(exclude_test_data=not show_test_data)
        api_calls = [m for m in metrics if m["type"] == "api_call"]
        
        if not api_calls:
            st.info("No performance data available yet.")
            return
        
        # Response time trends
        call_data = []
        for call in api_calls:
            call_data.append({
                "timestamp": call["timestamp"],
                "endpoint": call.get("endpoint", "unknown"),
                "response_time": call.get("response_time", 0),
                "success": call.get("success", True)
            })
        
        if call_data:
            df = pd.DataFrame(call_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Response time over time
            if PLOTLY_AVAILABLE:
                fig = px.line(
                    df, 
                    x='timestamp', 
                    y='response_time',
                    color='endpoint',
                    title="Response Time Trends"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write("**Response Time Trends:**")
                st.line_chart(df.set_index('timestamp')['response_time'])
            
            # Performance by endpoint
            endpoint_stats = df.groupby('endpoint').agg({
                'response_time': ['mean', 'max', 'count'],
                'success': 'mean'
            }).round(3)
            
            st.subheader("📊 Performance by Endpoint")
            st.dataframe(endpoint_stats, use_container_width=True)
    
    def render_usage_costs_tab(self, show_test_data=False):
        """Render usage and cost metrics."""
        st.header("💰 Usage & Cost Analysis")
        
        metrics = self.metrics_collector.get_metrics(exclude_test_data=not show_test_data)
        api_calls = [m for m in metrics if m["type"] == "api_call"]
        
        if not api_calls:
            st.info("No usage data available yet.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Call volume by endpoint
            endpoint_counts = {}
            for call in api_calls:
                endpoint = call.get("endpoint", "unknown")
                endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
            
            if endpoint_counts:
                if PLOTLY_AVAILABLE:
                    fig = px.bar(
                        x=list(endpoint_counts.keys()),
                        y=list(endpoint_counts.values()),
                        title="API Calls by Endpoint"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.write("**API Calls by Endpoint:**")
                    for endpoint, count in endpoint_counts.items():
                        st.write(f"- {endpoint}: {count} calls")
        
        with col2:
            # Estimated costs (placeholder calculation)
            total_calls = len(api_calls)
            estimated_cost = total_calls * 0.01  # $0.01 per call estimate
            
            st.metric("Total API Calls", total_calls)
            st.metric("Estimated Cost", f"${estimated_cost:.2f}")
            
            # Cost breakdown by endpoint
            st.subheader("💸 Cost Breakdown")
            for endpoint, count in endpoint_counts.items():
                cost = count * 0.01
                st.write(f"**{endpoint}**: {count} calls (${cost:.2f})")
    
    def render_evaluations_tab(self):
        """Render evaluation results."""
        st.header("🎯 LLM Evaluation Results")
        
        st.info("🔧 Evaluation results will be displayed here as they become available through LangSmith integration.")
        
        # Show evaluation configuration
        st.subheader("⚙️ Active Evaluators")
        
        evaluator_info = [
            {
                "Evaluator": "Hallucination Detection",
                "Purpose": "Detect false crime statistics and overconfident claims",
                "Threshold": "< 0.7 score triggers anomaly"
            },
            {
                "Evaluator": "Safety Appropriateness", 
                "Purpose": "Ensure balanced and appropriate safety advice",
                "Threshold": "< 0.7 score triggers anomaly"
            },
            {
                "Evaluator": "Consistency Check",
                "Purpose": "Compare responses to similar queries for consistency",
                "Threshold": "Future implementation"
            }
        ]
        
        st.table(pd.DataFrame(evaluator_info))
        
        # Manual evaluation interface
        st.subheader("🔄 Manual Evaluation")
        
        with st.expander("Test Evaluators"):
            test_query = st.text_input("Test Query:")
            test_response = st.text_area("Test Response:")
            
            if st.button("Run Evaluations") and test_query and test_response:
                inputs = {"input": test_query, "crime_data": {}}
                outputs = {"output": test_response}
                
                # Run evaluations
                if LANGSMITH_AVAILABLE:
                    hallucination_result = evaluators.detect_hallucination(inputs, outputs)
                    safety_result = evaluators.safety_appropriateness(inputs, outputs)
                else:
                    hallucination_result = {"score": 0.0, "comment": "Evaluator not available"}
                    safety_result = {"score": 0.0, "comment": "Evaluator not available"}
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Hallucination Detection:**")
                    st.write(f"Score: {hallucination_result['score']}")
                    st.write(f"Comment: {hallucination_result['comment']}")
                
                with col2:
                    st.write("**Safety Appropriateness:**")
                    st.write(f"Score: {safety_result['score']}")
                    st.write(f"Comment: {safety_result['comment']}")
    
    def _calculate_avg_response_time(self, metrics: List[Dict]) -> float:
        """Calculate average response time from metrics."""
        api_calls = [m for m in metrics if m["type"] == "api_call" and m.get("response_time")]
        if not api_calls:
            return 0.0
        
        total_time = sum(call.get("response_time", 0) for call in api_calls)
        return total_time / len(api_calls)


def render_observability_page():
    """Render the observability dashboard page."""
    dashboard = ObservabilityDashboard()
    dashboard.render_dashboard()


if __name__ == "__main__":
    render_observability_page()