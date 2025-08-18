# 🚨 Chicago Crime Analysis with LLM Observability

An intelligent crime analysis system for Chicago using Claude AI, with comprehensive LangSmith observability and AWS deployment capabilities.

## 🌟 Features

- **🔍 Crime Data Analysis** - Query Chicago Police Department's public crime database
- **🤖 AI-Powered Insights** - Claude 3.5 Sonnet generates safety recommendations and trend analysis
- **🛡️ Safety Advisory System** - Human-in-the-loop safety recommendations with review workflows
- **📊 LLM Observability** - Comprehensive monitoring with LangSmith integration
- **☁️ AWS Deployment** - Production-ready Terraform infrastructure
- **🚀 Streamlit Interface** - User-friendly web application

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit UI  │───▶│  LangGraph Agent │───▶│ Chicago Crime   │
│                 │    │  (Claude 3.5)   │    │ Database API    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       
         ▼                       ▼                       
┌─────────────────┐    ┌──────────────────┐              
│ LLM Observability│    │   Safety Advisory│              
│   Dashboard     │    │     System       │              
└─────────────────┘    └──────────────────┘              
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker (for deployment)
- AWS CLI (for cloud deployment)
- API Keys:
  - [Anthropic API Key](https://console.anthropic.com/) (required)
  - [LangSmith API Key](https://smith.langchain.com/) (optional, for observability)
  - [Chicago Data Portal Token](https://data.cityofchicago.org/) (optional, improves rate limits)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd chicago_crime_project
   ```

2. **Set up environment**
   ```bash
   python -m venv chicago_crime_env
   source chicago_crime_env/bin/activate  # On Windows: chicago_crime_env\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Run the application**
   ```bash
   streamlit run streamlit_app.py
   ```

5. **Access the app**
   - Open http://localhost:8501 in your browser

## 📊 Application Modes

### 🔍 Basic Crime Analysis
- Ask natural language questions about Chicago crime data
- Get AI-generated insights and safety recommendations
- Download analysis reports

### 🛡️ Safety Advisory (Human-in-the-Loop)
- High-risk safety queries flagged for human review
- Balanced, responsible safety recommendations
- Escalation workflows for sensitive queries

### 🔧 Direct Tool Query
- Direct access to Chicago crime database
- Customizable parameters (location, crime type, time range)
- Raw data export capabilities

### 📊 LLM Observability Dashboard
- Real-time metrics and performance monitoring
- Anomaly detection and evaluation results
- Token usage and cost tracking

## 🌩️ AWS Deployment

Deploy to AWS with a single command:

```bash
# Configure Terraform variables
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit terraform.tfvars with your settings

# Deploy everything
./deploy.sh
```

### Infrastructure Includes:
- **ECS Fargate** - Serverless container hosting
- **Application Load Balancer** - SSL termination and health checks
- **VPC with Private Subnets** - Secure network isolation
- **AWS Secrets Manager** - Secure API key storage
- **CloudWatch** - Comprehensive logging and monitoring
- **ECR** - Container image registry

**Estimated Cost: $20-50/month**

## 🔒 Security Features

- **Private Subnets** - Application isolated from direct internet access
- **Secrets Manager** - API keys stored securely, never in code
- **IAM Least Privilege** - Minimal required permissions
- **Security Groups** - Restricted network access
- **Container Scanning** - Automatic vulnerability detection
- **SSL/HTTPS** - Encrypted data in transit

## 📈 Observability & Monitoring

### LangSmith Integration
- **Automatic Tracing** - All LLM calls traced and monitored
- **Custom Evaluators** - Hallucination detection, safety appropriateness
- **Anomaly Detection** - Automatic flagging of problematic responses
- **Performance Metrics** - Response times, success rates, costs

### Custom Metrics
- API call success/failure rates
- Response time tracking
- Token usage and cost analysis
- User satisfaction tracking

## 🛠️ Development

### Project Structure
```
├── streamlit_app.py              # Main Streamlit application
├── chicago_crime_agent_fixed.py  # LangGraph agent with Claude
├── chicago_crime_tool_fixed.py   # Chicago crime database tool
├── safety_advisory_system.py     # Human-in-the-loop safety system
├── langsmith_config.py           # LLM observability configuration
├── observability_dashboard.py    # Metrics and monitoring dashboard
├── terraform/                    # AWS infrastructure as code
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container configuration
└── deploy.sh                     # Automated deployment script
```

### Key Components

- **LangGraph Agent** - Orchestrates multi-step crime analysis workflow
- **Chicago Crime Tool** - Interfaces with Chicago Police Department API
- **Safety Advisory System** - Manages human review for sensitive queries
- **LangSmith Observability** - Comprehensive LLM monitoring and evaluation

### Testing

```bash
# Test the crime analysis agent
python chicago_crime_agent_fixed.py

# Test the observability setup
python setup_observability.py

# Run comprehensive tests
python comprehensive_test_script.py
```

## 📝 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | Claude AI API key |
| `LANGCHAIN_API_KEY` | ⚠️ | LangSmith observability (optional) |
| `CHICAGO_DATA_APP_TOKEN` | ⚠️ | Chicago Data Portal token (optional) |
| `LANGCHAIN_TRACING_V2` | ⚠️ | Enable LangSmith tracing |
| `LANGCHAIN_PROJECT` | ⚠️ | LangSmith project name |

### Application Settings

- **Default Time Range**: Last 7 days (configurable)
- **API Timeout**: 30 seconds (configurable)
- **Rate Limiting**: Respects Chicago Data Portal limits
- **Caching**: In-memory metrics caching

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for informational purposes only. Always use your own judgment for safety decisions. Crime data may not be real-time and should supplement, not replace, official safety resources.

## 🙏 Acknowledgments

- [Chicago Police Department](https://data.cityofchicago.org/) for providing public crime data
- [Anthropic](https://www.anthropic.com/) for Claude AI
- [LangChain](https://langchain.com/) for LangSmith observability platform
- [Streamlit](https://streamlit.io/) for the web application framework

---

**🔗 Links**
- [Chicago Data Portal](https://data.cityofchicago.org/)
- [Anthropic Console](https://console.anthropic.com/)
- [LangSmith Platform](https://smith.langchain.com/)