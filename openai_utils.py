import os
import json
from dotenv import load_dotenv
from websockets.sync.client import connect

load_dotenv()

# Constants
WORKFLOW_ID = "8556ba87-acf8-4049-98a3-fc62a300656c"  # Workflow ID for Open AI GPT4
ESSO_TOKEN = os.getenv("ESSO_TOKEN", "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IlJERTBPVEF3UVVVMk16Z3hPRUpGTkVSRk5qUkRNakkzUVVFek1qZEZOVEJCUkRVMlJrTTRSZyJ9.eyJodHRwczovL3RyLmNvbS9mZWRlcmF0ZWRfdXNlcl9pZCI6IjYxMjQ3ODciLCJodHRwczovL3RyLmNvbS9mZWRlcmF0ZWRfcHJvdmlkZXJfaWQiOiJUUlNTTyIsImh0dHBzOi8vdHIuY29tL2xpbmtlZF9kYXRhIjpbeyJzdWIiOiJvaWRjfHNzby1hdXRofFRSU1NPfDYxMjQ3ODcifV0sImh0dHBzOi8vdHIuY29tL2V1aWQiOiJlMmZhNjVlNC0xMTEwLTRhOWItOGI5YS02YWFmM2M5YzI3NmUiLCJodHRwczovL3RyLmNvbS9hc3NldElEIjoiYTIwODE5OSIsImlzcyI6Imh0dHBzOi8vYXV0aC50aG9tc29ucmV1dGVycy5jb20vIiwic3ViIjoiYXV0aDB8NjVmMDQwMWFiNGIxOTkyNDJiNmQxMjQ3IiwiYXVkIjpbIjQ5ZDcwYTU4LTk1MDktNDhhMi1hZTEyLTRmNmUwMGNlYjI3MCIsImh0dHBzOi8vbWFpbi5jaWFtLnRob21zb25yZXV0ZXJzLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NTIxMzQ4MDksImV4cCI6MTc1MjIyMTIwOSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6InRnVVZad1hBcVpXV0J5dXM5UVNQaTF5TnlvTjJsZmxJIn0.jmL1rsMpbnuPIskSFfjvBH0JsJPNZWqhw6UkOsFfnPBAAllxutFdCzycm4fgOfisMllDh9mrjkzY6NKFSeKfcAE3WrTl420MNfqM6LWIse873byg8vsgqKwc9KhdV1GQiFrQJWyr9z6szr4mvL3sVPzTE2GFL-Pniyyw8G7oHmS0yUfcbT_oP0yEh2a7kJekzAKntWFzl-N8Culq39K2DW4PlNedktvOXa676RNKsWQ7y93bp5phhH1dYaezRxt8AzwnyzaNTruHFBts7FtuGPeSVkoykOZ5BjhB4KecVsCw9ZlPSekQDevIgM4pQaZn_i8aVAlnQmGTdC4o8MY90Q")
URL = f"wss://wymocw0zke.execute-api.us-east-1.amazonaws.com/prod/?Authorization={ESSO_TOKEN}"

def query_workflow(query: str, workflow_id: str = WORKFLOW_ID, is_persistence_allowed: str = "false"):
    """
    Send a query to the workflow through websocket connection.
    
    Args:
        query (str): The query to send
        workflow_id (str): The workflow ID
        is_persistence_allowed (str): Whether persistence is allowed
        
    Returns:
        tuple: (answer, cost_tracker)
    """
    msg = {
        "action": "SendMessage",
        "workflow_id": workflow_id,
        "query": query,
        "is_persistence_allowed": is_persistence_allowed
    }
    
    ws = connect(URL)
    ws.send(json.dumps(msg))
    answer = str()
    cost_tracker = dict()
    eof = False
    
    while not eof:
        message = ws.recv()
        message = json.loads(message)
        for model, value in message.items():
            if "answer" in value:
                answer += value["answer"]
            elif "cost_track" in value:
                cost_tracker = value['cost_track']
                eof = True
    
    ws.close()
    return answer, cost_tracker


def generate_sql_query(prompt: str, schema_info: str) -> str:
    """
    Generate SQL query from natural language prompt using websocket API.
    
    Args:
        prompt (str): Natural language query
        schema_info (str): Database schema information
        
    Returns:
        str: Generated SQL query
    """
    try:
        # Construct the system prompt with schema information
        system_prompt = f"""You are a SQL expert. Given the following database schema:
        {schema_info}
        
        Convert the following natural language query to SQL.
        Return ONLY the SQL query without any explanations."""

        # Format the complete prompt
        full_prompt = f"{system_prompt}\n\nQuery: {prompt}"
        
        # Get response through websocket
        answer, _ = query_workflow(full_prompt)
        return answer.strip()
    except Exception as e:
        return f"Error generating SQL query: {str(e)}"