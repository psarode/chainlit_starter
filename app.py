from dotenv import load_dotenv
import chainlit as cl
from movie_functions import get_now_playing_movies, get_showtimes, buy_ticket, get_reviews
import json
load_dotenv()

# Note: If switching to LangSmith, uncomment the following, and replace @observe with @traceable
# from langsmith.wrappers import wrap_openai
# from langsmith import traceable
# client = wrap_openai(openai.AsyncClient())
from langfuse.decorators import observe
from langfuse.openai import AsyncOpenAI
client = AsyncOpenAI()

gen_kwargs = {
    "model": "gpt-4o",
    "temperature": 0.2,
    "max_tokens": 500
}

SYSTEM_PROMPT = """\
You are a virtual assistant who has the capability to provide a user information about movies, showtimes and possible help them book tickets.

For list current movies requests, use the following function call format:
{"function": "get_now_playing_movies", "parameters": {}}

To get showtimes for a movie, use the following function call format:
{"function": "get_showtimes", "parameters": {"title": "title", "location": "location"}}

If the user indicates they want to buy a ticket, use the following function call format to confirm the details first:
{"function": "buy_ticket", "parameters": {"theater": "theater", "movie": "movie", "showtime": "showtime"}}

After receiving the results of a function call, incorporate that information into your response to the user.
"""

@observe
@cl.on_chat_start
def on_chat_start():    
    message_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    cl.user_session.set("message_history", message_history)

@observe
async def generate_response(client, message_history, gen_kwargs):
    response_message = cl.Message(content="")
    await response_message.send()

    stream = await client.chat.completions.create(messages=message_history, stream=True, **gen_kwargs)
    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await response_message.stream_token(token)
    
    await response_message.update()

    return response_message

@cl.on_message
@observe
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history", [])
    message_history.append({"role": "user", "content": message.content})
    
    response_message = await generate_response(client, message_history, gen_kwargs)
    #print(response_message.content)
    #json_data_with_params = '{"function": "get_now_playing_movies", "parameters": {}}'
    # Split the string to isolate the JSON part
    split_string = response_message.content.split("\n\n")  # Split by the double newline

    # The JSON part is usually the second part after the split
    json_part = split_string[1]

    # Parse the extracted JSON string
    parsed_json = json.loads(json_part)

    # Print the extracted and parsed JSON
    print(parsed_json)


    #print("Function" + function_call)
    #print(json.dumps(parsed_json, indent=4))

    #function_call = json.loads(parsed_json)
   
    if parsed_json["function"] == "get_now_playing_movies":
        print("Function is get_now_playing_movies.")

        # Check if the response contains get_now_playing_movies
        # call the function from movie_functions.py
        current_movies = get_now_playing_movies()

        #Append the function result to the message history
        message_history.append({"role" : "function", "name" : "get_now_playing_movies",  "content": current_movies})
        response_message = await generate_response(client, message_history, gen_kwargs)


    message_history.append({"role": "assistant", "content": response_message.content})
    cl.user_session.set("message_history", message_history)

if __name__ == "__main__":
    cl.main()
