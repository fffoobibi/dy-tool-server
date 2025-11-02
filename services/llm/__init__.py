from langchain_openai.chat_models import ChatOpenAI, AzureChatOpenAI


qwen_llm = ChatOpenAI(
    model="qwen-plus",
    api_key="sk-yOcL1v6eTM3sLo8tC74f9823A52a4996Bf2eF6B38656EaE0",
    base_url="http://36.32.174.26:5008/v1",
)


openai_llm = ChatOpenAI(
    model="gpt-4",
    api_key="sk-2xC6rIvCjzrUtjXG914376Fb2c914aEaB960E01e40C02a57",
    base_url="http://36.32.174.26:5008/v1",
)


azure_llm = AzureChatOpenAI(
    azure_deployment="gpt-4o",
    azure_endpoint="https://mediamz-gpt-35-turbo.openai.azure.com/",
    api_key="a6d9b4a7b2924407aa81cfc819a5a287",
    api_version="2024-08-01-preview",
)
