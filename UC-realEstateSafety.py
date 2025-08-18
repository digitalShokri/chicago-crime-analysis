def real_estate_safety_bot():
    """Chatbot for real estate safety inquiries."""
    
    # LangChain chain for property safety analysis
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    
    safety_template = """
    You are a real estate safety assistant using Chicago crime data.
    
    User Query: {user_query}
    Crime Data: {crime_data}
    
    Provide a comprehensive safety assessment for this location including:
    1. Overall safety rating (1-10)
    2. Key safety concerns
    3. Best times to visit/avoid
    4. Specific recommendations for residents
    5. Nearby safety resources
    
    Be honest but constructive in your assessment.
    """
    
    prompt = PromptTemplate(
        input_variables=["user_query", "crime_data"],
        template=safety_template
    )
    
    return LLMChain(llm=llm, prompt=prompt)