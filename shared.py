from dataclasses import dataclass
from datetime import datetime, time


EARLIEST_ALLOWED = time(8)

LATEST_ALLOWED = time(17)

DURATION_LIMIT = [1, 4]

INSTRUCTIONS = f"""\
Today's date is {datetime.now().date()}.
Always answer back in Bahasa Indonesia.
Always use the 24 hour format for the tool arguments.
Any query regarding room availability or reservation can only come from the tool's result (never
use past messages or history to get your answers from to reply back to the user).
Before invoking a tool, ensure that user have given all the required parameters from their query,
ask the user for those missing parameter if any is/are missing.
Never chain call the tool `find_empty_rooms` and `reserve_room` sequentially. Always present your
finding to the user first after calling `find_empty_rooms`, even if they have provided all the
necessary arguments to call `reserve_room` and the conditions are positive from the result of
`find_empty_rooms`.
If user ask to reserve a room that is not present from the results of `find_empty_rooms`, then make
an attempt to reserve that room and present the result afterwards.
We are enforcing an `on the hour` format. Users can only specify whole hour numbers only for room
reservations (reserve a room at 8 for 2 hours is allowed, reserve a room at 8.30 for 2 hours and 5
minutes is not allowed).
The earliest time user can reserve a room is at {EARLIEST_ALLOWED}.
Room reservation must end on {LATEST_ALLOWED}. No reservation is allowed to last longer than this.
User can only reserve a room for {DURATION_LIMIT[0]} - {DURATION_LIMIT[1]} hours.
"""

HISTORY_FILE_PATH = "riwayat.json"

RESERVATION_FILE_PATH = "pemesanan.json"

MAX_QUERIES_STORED = 8

ROOMS = [
    {"name": "Ruang Merapi", "capacity": 4},
    {"name": "Ruang Bromo", "capacity": 8},
    {"name": "Ruang Rinjani", "capacity": 12},
]


@dataclass
class Appointment:
    name : str
    start_time : datetime
    end_time : datetime