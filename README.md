Another assistant agent designed to execute user's queries using A.I. agent provided via OpenRouter API.<br>

Current feature for `assistant_agent.py`:<br>
- The ability to make a check and make a reservation given the number of people attending, the date, the starting time and duration of the reservation, and the name of the person making the reservation.<br>

Current local commands available for `assistant_agent.py`:<br>
- `/history`: Used as a debugging tool to check all the relevant currently saved messages sent to and received from the agent.<br>
- `/jadwal`: Check all the reservations made by the agent from the user queries.<br>
- `/keluar`: Exits the script while saving the saved messages to an external .json file called "riwayat.json".<br>

Note:<br>
This project has been tested with Python 3.15<br>
Dependencies required can be found in the file `requirements.txt`<br>
Rename the file `.env.example` to `.env` and fill in OPENROUTER_API_KEY with your actual api key<br>
You may change the AI model with a different one that's available in OpenRouter by changing the value of OPENROUTER_MODEL<br>

Changelog:
- Version 1:<br>
Added 3 tools that the A.I. agent can use: `show_empty_rooms`, `reserve_room`, and `show_reservation` to facilitate user queries on making and checking reservations.<br>
Reservation data is saved to an external file called `pemesanan.json`, while messages to and from the agents are saved to `riwayat.json`. Note that `pemesanan.json` is always updated at every user query while `riwayat.json` is only updated when the user types `/keluar` to exit the script.<br>
