import unittest
import json
from datetime import date
from unittest.mock import patch
from tools import tool_finder
from shared import ROOMS, EARLIEST_ALLOWED

class TestToolFinder(unittest.TestCase):

    def setUp(self):
        """Set up a fresh database mock before each test."""
        self.db = {}
        ROOMS.sort(key=lambda room: room["capacity"])
        for room in ROOMS:
            self.db[room["name"]] = {}

    def test_tool_finder_find_empty_rooms_success(self):
        """Test tool_finder correctly parses arguments and calls find_empty_rooms."""
        args_payload = {
            "year": 2026,
            "month": 12,
            "day": 30,
            "start hour": 9,
            "duration hour": 2,
            "amount": 3
        }
        
        result = tool_finder(self.db, "find_empty_rooms", json.dumps(args_payload))
        self.assertIn("message", result)
        self.assertIn("Ruang Merapi", result["message"])

    def test_tool_finder_find_empty_rooms_restriction_failure(self):
        """Test that find_empty_rooms fails through tool_finder if start time is too early."""
        args_payload = {
            "year": 2026,
            "month": 12,
            "day": 30,
            "start hour": EARLIEST_ALLOWED.hour - 1, # Too early
            "duration hour": 2,
            "amount": 2
        }
        
        result = tool_finder(self.db, "find_empty_rooms", json.dumps(args_payload))
        self.assertIn("error", result)
        self.assertIn(EARLIEST_ALLOWED.strftime("%I:%M %p"), result["error"])

    @patch('tools.user_confirmation', return_value=True)
    def test_tool_finder_reserve_room_success(self, mock_confirmation):
        """Test tool_finder correctly parses arguments and calls reserve_room."""
        args_payload = {
            "year": 2026,
            "month": 12,
            "day": 30,
            "start hour": 10,
            "duration hour": 1,
            "amount": 2,
            "person name": "Alice",
            "room name": "Ruang Merapi"
        }
        
        result = tool_finder(self.db, "reserve_room", json.dumps(args_payload))
        self.assertIn("success", result)
        self.assertIn("Ruang Merapi", result["success"])
        
        # Verify persistence in the db structure
        d_key = date(2026, 12, 30)
        self.assertEqual(len(self.db["Ruang Merapi"][d_key]), 1)
        self.assertEqual(self.db["Ruang Merapi"][d_key][0].name, "Alice")

    @patch('tools.user_confirmation', return_value=False)
    def test_tool_finder_reserve_room_denied(self, mock_confirmation):
        """Test that reserve_room returns failure when user denies confirmation."""
        args_payload = {
            "year": 2026,
            "month": 12,
            "day": 30,
            "start hour": 10,
            "duration hour": 1,
            "amount": 2,
            "person name": "Alice",
            "room name": "Ruang Merapi"
        }
        
        result = tool_finder(self.db, "reserve_room", json.dumps(args_payload))
        self.assertIn("failure", result)

    def test_tool_finder_reserve_room_non_existent_failure(self):
        """Test that reserving a non-existent room through tool_finder returns an error."""
        args_payload = {
            "year": 2026,
            "month": 12,
            "day": 30,
            "start hour": 9,
            "duration hour": 2,
            "amount": 2,
            "person name": "Bob",
            "room name": "Ruang Fantasi" # Doesn't exist
        }
        
        result = tool_finder(self.db, "reserve_room", json.dumps(args_payload))
        self.assertIn("error", result)
        self.assertIn("does not exist", result["error"])

    def test_tool_finder_reserve_room_insufficient_capacity_failure(self):
        """Test that reserving a room with too many people through tool_finder returns an error."""
        args_payload = {
            "year": 2026,
            "month": 12,
            "day": 30,
            "start hour": 9,
            "duration hour": 2,
            "amount": 10, # Exceeds Ruang Merapi capacity (4)
            "person name": "Charlie",
            "room name": "Ruang Merapi"
        }
        
        result = tool_finder(self.db, "reserve_room", json.dumps(args_payload))
        self.assertIn("error", result)
        self.assertIn("insufficient", result["error"])

    @patch('tools.user_confirmation', return_value=True)
    def test_tool_finder_show_reservations_success(self, mock_confirmation):
        """Test tool_finder correctly parses arguments and calls show_reservations, returning a string list."""
        # 1. First, make a reservation so there's data to show
        reserve_payload = {
            "year": 2026,
            "month": 12,
            "day": 30,
            "start hour": 9,
            "duration hour": 2,
            "amount": 2,
            "person name": "Diana",
            "room name": "Ruang Bromo"
        }
        tool_finder(self.db, "reserve_room", json.dumps(reserve_payload))

        # 2. Query reservations via show_reservations through tool_finder
        show_payload = {
            "year": 2026,
            "month": 12,
            "day": 30
        }
        
        result = tool_finder(self.db, "show_reservations", json.dumps(show_payload))
        
        self.assertIn("list of rooms", result)
        rooms_list_str = result["list of rooms"]
        
        # Verify that output is a string containing the booker's name and room names
        self.assertIsInstance(rooms_list_str, str)
        self.assertIn("Ruang Bromo", rooms_list_str)
        self.assertIn("Diana", rooms_list_str)
        self.assertIn("Ruang Merapi", rooms_list_str)

    def test_tool_finder_invalid_json(self):
        """Test that tool_finder safely catches malformed JSON strings and returns an error."""
        invalid_json_str = "{ 'year': 2026, malformed_json }"
        
        result = tool_finder(self.db, "find_empty_rooms", invalid_json_str)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "The given argument is not JSON")

    def test_tool_finder_non_existent_tool(self):
        """Test that requesting an unregistered tool name returns a proper error message."""
        args_payload = {"year": 2026}
        
        result = tool_finder(self.db, "delete_universe", json.dumps(args_payload))
        self.assertIn("error", result)
        self.assertIn("does not exist", result["error"])


if __name__ == "__main__":
    unittest.main()