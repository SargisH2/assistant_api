import os
import json
import time
from openai import OpenAI
from serpapi import GoogleSearch

# import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

ASSISTANT_ID = 'asst_8VWwHooSU70gUK7vHkHvnSRB'

OPENAI_API_KEY = "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"
SERPAPI_API_KEY = 'd277c1be0ca1168875f9e3d817e0b17ff3e3b8b21cbce42dbe10938116c73cb5'

os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
os.environ['SERPAPI_API_KEY'] = SERPAPI_API_KEY

client = OpenAI()
assistant = client.beta.assistants.retrieve(ASSISTANT_ID)


class Details(BaseModel):
    query: str
    chat_id: str
app = FastAPI()

@app.get('/')
def index():
    return {'message': "This is the home page of this API. Go to /gsearch/"}

@app.post('/gsearch/')
def gsearch(data: Details):
    query = data.query
    chat_id = data.chat_id
    id, chat = handle(query, chat_id)
    return {
        'id':  id,
        'chat': chat
        }


def google_search(query):
    print(query)
    params = {
      "engine": "google",
      "q": query,
      "google_domain": "google.com",
      "api_key": SERPAPI_API_KEY
    }
    search = GoogleSearch(params)
    return search.get_dict() 
function_json = {
    "name": "google_search",
    "description": "Search query in google",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        },
        "required": ["query"],
    },
}

def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.3)
    return run



def run_thread(thread):
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id = ASSISTANT_ID
    )
    run = wait_on_run(run, thread)
    if run.status == 'requires_action':
        tool_calls = run.required_action.submit_tool_outputs.tool_calls
        call_ids = []
        call_outputs = []
        for tool_call in tool_calls:
            if tool_call.function.name == 'google_search':
                arguments = json.loads(tool_call.function.arguments)
                search_result = google_search(arguments['query'])
                
                call_outputs.append(json.dumps(search_result))
                call_ids.append(tool_call.id)
                
        run = client.beta.threads.runs.submit_tool_outputs(
            thread_id = thread.id,
            run_id = run.id,
            tool_outputs =
            
            
            [
                {
                    "tool_call_id": id,
                    "output": output,
                } for id, output in zip(call_ids, call_outputs)
            ],
        )
        run = wait_on_run(run, thread)



def handle(query: str, id: str = '') -> tuple:
    if id == '':
        thread = client.beta.threads.create()
        id = thread.id
    else:
        try:
            thread = client.beta.threads.retrieve(id)
        except:
            print('Invalid id. Creating new conversation')
            thread = client.beta.threads.create()
            id = thread.id
    client.beta.threads.messages.create(
        thread_id = id,
        role = "user",
        content = query
    )
    run_thread(thread)
    messages = client.beta.threads.messages.list(
        thread_id=thread.id
    ).data
    messages = reversed(list(map(lambda message: (message.role, message.content[0].text.value), messages)))
    return id, messages



# if __name__ == '__main__':
#     uvicorn.run(app, host='127.0.0.1', port=4000)