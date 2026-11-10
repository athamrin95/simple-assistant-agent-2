import json
import os
import sys
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

from shared import HISTORY_FILE_PATH, INSTRUCTIONS, MAX_QUERIES_STORED, RESERVATION_FILE_PATH, ROOMS, Appointment
from tools import TOOLS, tool_finder


def check_env(api_key:str, base_url:str, model:str) -> str:
    """Returns None if .env is loaded properly and the necessary properties are present."""
    if any(value is None or value == "" for value in(api_key, base_url, model)):
        return "OPENROUTER_API_KEY, OPENROUTER_BASE_URL, and/or OPENROUTER_MODEL is missing or cannot be read from your .env file. Exiting..."
    else:
        return None
    
def call_ai_with_tools(client:OpenAI, openrouter_model:str, input_list:list, user_input:str, count_list:list, db:dict) -> str:
    try:
        temp_list = list(input_list)
        count = len(temp_list)
        temp_list.append({"role": "user", "content": user_input})

        max_chains = 4
        chain_number = 0
        while chain_number < max_chains:
            chain_number += 1
            response_stream = client.responses.create(
                model=openrouter_model,
                instructions=INSTRUCTIONS,
                input=temp_list,
                tools=TOOLS,
                stream = True,
            )
            response_output = None
            response_collected = False
            for event in response_stream:
                if event.type == "response.output_text.delta":
                    # Agent is giving the final answer to user's query
                    print(event.delta, end="", flush=True)

                elif event.type == "response.completed":
                    temp_list += event.response.output
                    response_output = event.response.output
                    response_collected = True
                    
            # Do final check if response has been properly completed
            if not response_collected:
                return "An error has occurred. It seems that the response from the agent has never reached completion status. Please retry your query again."
            
            tools_called = False
            for item in response_output:
                if item.type == "function_call":
                    # Preparing for the next chain function call
                    tools_called = True
                    tool_output = json.dumps(tool_finder(db, item.name, item.arguments))
                    temp_list.append(
                        {
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": tool_output,
                        }
                    )   
            if not tools_called:
                # This should be the "final complete" non-tool answer from the agent to the user's query
                count = len(temp_list) - count
                input_list.clear()
                input_list.extend(temp_list)
                count_list.append(count)
                return ""
            
        # Over the limit of max_chains
        return "An error has occurred. It seems that your request is too complex to be completed all at once. Please try a simpler query."

    except Exception as e:
        # e should be put to a log file for future expansion
        return f"An unexpected error has occurred. {e}"

def trim_history(input_list:list, count_list:list) -> None:
    count = count_list.pop(0)
    del input_list[:count]
    return None

def local_command(user_input:str, input_list:list, count_list:list, db:dict):
    user_input = user_input[1:].casefold()

    if user_input == 'history':
        print(f">>> {count_list}")
        for entry in input_list:
            print(f">>> {entry}")

    elif user_input == 'jadwal':
        for room_name in db.keys():
            print(f"{room_name}:")
            if not db[room_name]:
                print("Empty...")
            else:
                sorted_dates = sorted(db[room_name].items())
                for date, appt_list in sorted_dates:
                    print(f"-) {date}: ")
                    sorted_appts = sorted(appt_list, key=lambda elt: elt.start_time)
                    for appt in sorted_appts:
                        print(f"\t-) {appt.name}, {appt.start_time.time()} - {appt.end_time.time()}")
            print("=============")

    elif user_input == 'keluar':
        with open(HISTORY_FILE_PATH, "w", encoding="utf-8") as f:
            for entry in input_list:
                if hasattr(entry, "model_dump"):
                    entry = entry.model_dump()
                f.write(json.dumps(entry) + "\n")
        print("Exiting...")
        sys.exit(1)
    
    else:
        print("Local command not recognized.")


def load_reservation_file(db:dict):
    try:
        file_string = ""
        with Path(RESERVATION_FILE_PATH).open("r", encoding="utf-8") as f:
            for line in f:
                file_string += line

        if file_string == "":
            # Empty file logic...
            ROOMS.sort(key=lambda room: room["capacity"])
            for room in ROOMS:
                db[room["name"]] = {}
        else:    
            loaded_data = json.loads(file_string)
            # Properly reconstruct date keys and Appointment objects
            for room_name, dates_dict in loaded_data.items():
                db[room_name] = {}
                for date_str, app_list in dates_dict.items():
                    # Convert ISO date string back to a datetime.date object
                    date_obj = datetime.fromisoformat(date_str).date()
                    db[room_name][date_obj] = [
                        Appointment(
                            name=app["name"],
                            start_time=datetime.fromisoformat(app["start_time"]),
                            end_time=datetime.fromisoformat(app["end_time"])
                        )
                        for app in app_list
                    ]  
            
    except FileNotFoundError:
        # File doesn't exist yet, initialize a fresh database structure
        ROOMS.sort(key=lambda room: room["capacity"])
        for room in ROOMS:
            db[room["name"]] = {}
        
    except json.JSONDecodeError:
        print(f"An error has occurred. Unable to load reservation JSON data from {RESERVATION_FILE_PATH} properly. Possible data corruption, exiting...") 
        sys.exit(1)
        
    except Exception as e:
        # e should be placed in a log file in future update
        print(f"An unexpected error has occurred while loading {RESERVATION_FILE_PATH}. Exiting...")
        sys.exit(1)

def load_history_file(input_list:list, count_list:list):
    try:
        with Path(HISTORY_FILE_PATH).open("r", encoding="utf-8") as f:
            for line in f:
                input_list.append(json.loads(line))

        role_check = False
        for index, entry in enumerate(input_list):
            if "role" in entry and entry["role"] == "user":
                if not role_check:
                    count = index
                    role_check = True
                else:
                    raise Exception("Missing proper message sequence from file!")
            elif "phase" in entry and entry["phase"] == "final_answer" :
                if role_check:
                    count_list.append(index + 1 - count)
                    role_check = False
                else:
                    raise Exception("Missing proper message sequence from file!")

        if role_check:
            raise Exception("Missing proper message sequence from file!")

        while len(count_list) > MAX_QUERIES_STORED:
            trim_history(input_list, count_list)
            
    except Exception as e:
        # e should be put to a log file for future expansion.
        print(f"An error has occurred. Unable to load {HISTORY_FILE_PATH}\nContinuing with an empty message history...")
        input_list.clear()
        count_list.clear()

def main() -> None:
    # Load the .env properties first
    load_dotenv()
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    openrouter_base_url = os.getenv("OPENROUTER_BASE_URL")
    openrouter_model = os.getenv("OPENROUTER_MODEL")
    result = check_env(openrouter_api_key, openrouter_base_url, openrouter_model)
    if result:
        print(result)
        sys.exit(1)
    # Load message history
    input_list = []
    count_list = []
    load_history_file(input_list, count_list)
    """
    The structure for db should look like this:
    {
        "Ruang Merapi": {"2026-12-30": [Appointment1, Appointment2]},
        "Ruang Bromo": {},
        ...
    }
    """
    # Load reservation data
    db = {}
    load_reservation_file(db) 

    client = OpenAI(api_key=openrouter_api_key, base_url=openrouter_base_url)
    while True:
        user_input = input("Please enter an input regarding room reservation: ")
        user_input = user_input.strip()
        if user_input == '':
            print(f"You've entered an empty command, please try again.")
            continue
        if user_input[0] == '/':
            local_command(user_input, input_list, count_list, db)
            continue

        result = call_ai_with_tools(client, openrouter_model, input_list, user_input, count_list, db)
        print(result)
            
        while len(count_list) > MAX_QUERIES_STORED:
            trim_history(input_list, count_list)

if __name__ == "__main__":
    main()