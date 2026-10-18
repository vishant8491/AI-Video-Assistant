import os
from dotenv import load_dotenv

load_dotenv()

def get_llm(temperature: float = 0.3):
    """
    Auto-detect available LLM provider:
    1. Groq (Fastest & 100% Free) -> GROQ_API_KEY
    2. Hugging Face Inference API (Free) -> HUGGINGFACEHUB_API_TOKEN or HF_TOKEN
    3. Mistral AI -> MISTRAL_API_KEY
    """
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model="qwen/qwen3.8-27b",
            api_key=groq_key,
            temperature=temperature,
        )

    hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HF_TOKEN")
    mistral_key = os.getenv("MISTRAL_API_KEY")

    # If MISTRAL_API_KEY was set with an HF token
    if mistral_key and mistral_key.startswith("hf_"):
        hf_token = mistral_key

    if hf_token:
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
        endpoint = HuggingFaceEndpoint(
            repo_id="mistralai/Mistral-7B-Instruct-v0.3",
            task="text-generation",
            max_new_tokens=1024,
            temperature=temperature,
            huggingfacehub_api_token=hf_token,
        )
        return ChatHuggingFace(llm=endpoint)

    if mistral_key and not mistral_key.startswith("hf_"):
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(
            model="mistral-small-latest",
            mistral_api_key=mistral_key,
            temperature=temperature,
        )

    raise ValueError(
        "No valid LLM API key found in .env! "
        "Please provide GROQ_API_KEY, HUGGINGFACEHUB_API_TOKEN, or MISTRAL_API_KEY."
    )
