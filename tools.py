import json
from json import JSONDecodeError
from datetime import date, datetime, timedelta

from shared import DURATION_LIMIT, EARLIEST_ALLOWED, LATEST_ALLOWED, RESERVATION_FILE_PATH, ROOMS, Appointment

TOOLS = [
    {
        "type": "function",
        "name": "find_empty_rooms",
        "description": (
            "Returns a list of empty/available rooms for reservation given the date, start time, duration of the reservation, and the amount of person joining in."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "The year of the requested reservation date",
                },
                "month": {
                    "type": "integer",
                    "description": "The month (in numerical format) of the requested reservation date",
                },
                "day": {
                    "type": "integer",
                    "description": "The day (in numerical format) of the requested reservation date",
                },
                "start hour": {
                    "type": "integer",
                    "description": "The starting hour of the requested reservation date",
                },
                "duration hour": {
                    "type": "integer",
                    "description": "The duration of the reservation in hour",
                },
                "amount": {
                    "type": "integer",
                    "description": "The amount of person who will be joining in during the requested reservation schedule",
                },
            },
            "required": ["year","month","day","start hour","duration hour","amount"],
        },
    },
    {
        "type": "function",
        "name": "reserve_room",
        "description": (
            "Reserve a room given the required parameters. Note that the program will have the user make the final confirmation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "The year of the requested reservation date",
                },
                "month": {
                    "type": "integer",
                    "description": "The month (in numerical format) of the requested reservation date",
                },
                "day": {
                    "type": "integer",
                    "description": "The day (in numerical format) of the requested reservation date",
                },
                "start hour": {
                    "type": "integer",
                    "description": "The starting hour of the requested reservation date",
                },
                "duration hour": {
                    "type": "integer",
                    "description": "The duration of the reservation in hour",
                },
                "amount": {
                    "type": "integer",
                    "description": "The amount of person who will be joining in during the requested reservation schedule",
                },
                "person name": {
                    "type": "string",
                    "description": "The name of the person who requested the reservation",
                },
                "room name": {
                    "type": "string",
                    "description": "The name of the room that is being requested for the reservation",
                },
            },
            "required": ["year","month","day","start hour","duration hour","amount","person name","room name"],
        },
    },
    {
        "type": "function",
        "name": "show_reservations",
        "description": (
            "Returns a list of rooms with their reservation details given the date that you wish to check."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "The year of the date ",
                },
                "month": {
                    "type": "integer",
                    "description": "The month (in numerical format) of the date",
                },
                "day": {
                    "type": "integer",
                    "description": "The day (in numerical format) of the date",
                },
            },
            "required": ["year", "month", "day"],
        },
    },
]


def restriction_checker(start_time:datetime, end_time:datetime) -> dict:
    if start_time.time() < EARLIEST_ALLOWED:
        return {"error": f"The earliest time you can appoint a room is {EARLIEST_ALLOWED.strftime("%I:%M %p")}."}
    if end_time.time() > LATEST_ALLOWED:
        return {"error": f"Room reservation must end on {LATEST_ALLOWED.strftime("%I:%M %p")}. No reservation is allowed to last longer than this."}
    if not (timedelta(hours=DURATION_LIMIT[0]) <= end_time - start_time <= timedelta(hours=DURATION_LIMIT[1])):
        return {"error": f"Appointment duration must be between {DURATION_LIMIT[0]} to {DURATION_LIMIT[1]} hours."}
    return {"success": "Initial requirements passed."}

def find_empty_rooms(db:dict, amount:int, start_time:datetime, end_time:datetime) -> dict:
    # Check for restrictions
    result = restriction_checker(start_time, end_time)
    if "error" in result:
        return result

    available_rooms = [] # A list of potential available rooms
    date = start_time.date()
    for room in ROOMS:
        if(amount > room["capacity"]):
            # Room has insufficient capacity, checking other rooms if available
            continue
        else:
            if date not in db[room["name"]]:
                # Room has no appointment yet for the whole day, adding room
                available_rooms.append(room)
            else:
                no_conflict = True
                for appointment in db[room["name"]][date]:
                    if start_time < appointment.end_time and end_time > appointment.start_time:
                        # Conflict detected, check if other room is available
                        no_conflict = False
                        break
                if no_conflict:
                    # No conflict detected, adding room
                    available_rooms.append(room)

    if len(available_rooms) == 0:
        return {"error": "All rooms during your specified time are unavailable due to incompatible scheduling or insufficient room capacity."}

    return {"message": f"Here are the available room(s) found: {available_rooms}."}

def user_confirmation(room_name:str, start_time:datetime, end_time:datetime, person_name:str, amount:int) -> bool:
    print(
        "Please confirm your reservation details:\n"
        f"Room: {room_name}\n"
        f"Date: {start_time.date()}\n"
        f"Time: {start_time.time()} – {end_time.time()}\n"
        f"Attendees: {amount} people\n"
        f"Reserved Under: {person_name}"
    )
    reply = input("Should I proceed with booking this room? (y/n): ")
    if reply.casefold() == "y":
        return True
    else:
        return False

def save_reservation_to_file(db:dict):
    serializable_db = {}
    # 1. Transform custom objects (dates and Appointment dataclasses) into JSON-safe structures
    for room_name, dates_dict in db.items():
        serializable_db[room_name] = {}
        for d_key, appointments in dates_dict.items():
            # Convert date object key to an ISO string (since JSON keys must be strings)
            date_str = d_key.isoformat() if isinstance(d_key, (date, datetime)) else str(d_key)
            serializable_db[room_name][date_str] = [
                {
                    "name": app.name,
                    "start_time": app.start_time.isoformat(),
                    "end_time": app.end_time.isoformat()
                }
                for app in appointments
            ]
    try:
        with open(RESERVATION_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(json.dumps(serializable_db))
    except Exception as e:
        print(f"An error occurred while saving the file: {e}")

def reserve_room(db:dict, amount:int, start_time:datetime, end_time:datetime, person_name:str, room_name:str) -> dict:
    # Double check for any mishaps
    result = restriction_checker(start_time, end_time)
    if "error" in result:
        return result
    
    room = next((room for room in ROOMS if room["name"] == room_name), None)
    if room is None:
        return {"error": f"{room_name} does not exist!"}

    date = start_time.date()
    if(amount > room["capacity"]):
        # Room has insufficient capacity
        return {"error": f"{room_name} has a capacity of {room["capacity"]} people, which is insufficient to hold your requested amount of {amount} people."}
    if date not in db[room_name]:
        # First appointment for the whole day
        if user_confirmation(room_name, start_time, end_time, person_name, amount):
            db[room_name][date] = [Appointment(person_name, start_time, end_time)]
            save_reservation_to_file(db)
            return {"success": f"Room appointment for {room_name}, {start_time} - {end_time} under the name of {person_name} has been successfully booked!"}
        else:
            return {"failure": "Room appointment was denied by the user."}
    else:
        for appointment in db[room_name][date]:
            if start_time < appointment.end_time and end_time > appointment.start_time:
                # Conflict detected
                return {"error": f"There is a scheduling conflict for {room_name} due to another existing schedule between {appointment.start_time} - {appointment.end_time}"}
        # No conflict
        if user_confirmation(room_name, start_time, end_time, person_name, amount):
            db[room["name"]][date].append(Appointment(person_name, start_time, end_time))
            save_reservation_to_file(db)
            return {"success": f"Room appointment for {room_name}, {start_time} - {end_time} under the name of {person_name} has been successfully booked!"}
        else:
            return {"failure": "Room appointment was denied by the user."}

def show_reservations(db:dict, datetime:datetime):
    list = []
    date = datetime.date()
    for room_name in db.keys():
        if date not in db[room_name]:
            # No reservation for the day
            list.append({"name": room_name, "date": date, "reservation": "empty"})
        else:
            list.append({"name": room_name, "date": date, "reservation": db[room_name][date]})
    return {"list of rooms": str(list)}            

def tool_finder(db:dict, tool_name:str, args:str) -> dict:
    try:
        args_dict = json.loads(args)
    except JSONDecodeError:
        return {"error": "The given argument is not JSON"}
    except Exception as e:
        raise Exception(e)

    if tool_name == "find_empty_rooms":
        start_time = datetime(args_dict["year"], args_dict["month"], args_dict["day"], args_dict.get("start hour", 0))
        end_time = datetime(args_dict["year"], args_dict["month"], args_dict["day"], args_dict.get("start hour", 0) + args_dict.get("duration hour", 0))
        arg_amount = args_dict["amount"]
        print(f"Tool {tool_name}({arg_amount}, {start_time}, {end_time}) has been requested by the agent")
        return find_empty_rooms(db, arg_amount, start_time, end_time)

    elif tool_name == "reserve_room":
        start_time = datetime(args_dict["year"], args_dict["month"], args_dict["day"], args_dict.get("start hour", 0))
        end_time = datetime(args_dict["year"], args_dict["month"], args_dict["day"], args_dict.get("start hour", 0) + args_dict.get("duration hour", 0))
        arg_amount = args_dict["amount"]
        arg_person_name = args_dict["person name"]
        arg_room_name = args_dict["room name"]
        print(f"Tool {tool_name}({arg_amount}, {start_time}, {end_time}, {arg_person_name}, {arg_room_name}) has been requested by the agent")
        return reserve_room(db, arg_amount, start_time, end_time, arg_person_name, arg_room_name)

    elif tool_name == "show_reservations":
        date_time = datetime(args_dict["year"], args_dict["month"], args_dict["day"])
        print(f"Tool {tool_name}({date_time}) has been requested by the agent")
        return show_reservations(db, date_time)

    else:
        print(f"Tool {tool_name} has been requested by the agent, but this tool does not exist!")
        return {"error": f"Tool `{tool_name}` does not exist."}