import os


os.environ["LLM_PROVIDER"] = "offline"
os.environ["OPENAI_API_KEY"] = ""
os.environ["AUTH_ENABLED"] = "false"
os.environ["DATABASE_URL"] = ""
os.environ["STORAGE_PROVIDER"] = "local"
os.environ["RAG_PROVIDER"] = "local"
