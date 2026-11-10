import unittest
from datetime import datetime, date
from unittest.mock import patch
from tools import find_empty_rooms, reserve_room, show_reservations
from shared import ROOMS, EARLIEST_ALLOWED, LATEST_ALLOWED, DURATION_LIMIT

class TestToolRoomFinderAndReservation(unittest.TestCase):

    def setUp(self):
        """Set up a fresh database mock before each test."""
        self.db = {}
        ROOMS.sort(key=lambda room: room["capacity"])
        for room in ROOMS:
            self.db[room["name"]] = {}

    def test_restriction_checker_too_early(self):
        """Test that finding empty rooms fails if start time is before business hours."""
        start = datetime(2026, 12, 30, EARLIEST_ALLOWED.hour - 1, 0)
        end = datetime(2026, 12, 30, EARLIEST_ALLOWED.hour + 1, 0)
        
        result = find_empty_rooms(self.db, 2, start, end)
        self.assertIn("error", result)
        self.assertIn(EARLIEST_ALLOWED.strftime("%I:%M %p"), result["error"])

    def test_restriction_checker_too_late(self):
        """Test that finding empty rooms fails if end time is after business hours."""
        start = datetime(2026, 12, 30, LATEST_ALLOWED.hour - 1, 0)
        end = datetime(2026, 12, 30, LATEST_ALLOWED.hour + 1, 0)
        
        result = find_empty_rooms(self.db, 2, start, end)
        self.assertIn("error", result)
        self.assertIn(LATEST_ALLOWED.strftime("%I:%M %p"), result["error"])

    def test_restriction_checker_invalid_duration(self):
        """Test that appointment duration outside the allowed limit is rejected."""
        start = datetime(2026, 12, 30, 9, 0)
        end = datetime(2026, 12, 30, 9, 30) # Only 30 minutes (too short)
        
        result = find_empty_rooms(self.db, 2, start, end)
        self.assertIn("error", result)
        self.assertIn(f"between {DURATION_LIMIT[0]} to {DURATION_LIMIT[1]} hours", result["error"])

    def test_find_empty_rooms_success(self):
        """Test finding available rooms when slots are free and capacity matches."""
        start = datetime(2026, 12, 30, 9, 0)
        end = datetime(2026, 12, 30, 11, 0)
        
        result = find_empty_rooms(self.db, 3, start, end)
        self.assertIn("message", result)
        self.assertIn("Ruang Merapi", result["message"])

    def test_find_empty_rooms_excludes_insufficient_capacity(self):
        """Test that rooms with insufficient capacity are filtered out of available rooms."""
        start = datetime(2026, 12, 30, 9, 0)
        end = datetime(2026, 12, 30, 11, 0)
        
        # Requesting capacity for 6 people (Ruang Merapi only holds 4)
        result = find_empty_rooms(self.db, 6, start, end)
        self.assertIn("message", result)
        self.assertNotIn("Ruang Merapi", result["message"])
        self.assertIn("Ruang Bromo", result["message"])

    @patch('tools.user_confirmation', return_value=True)
    def test_reserve_room_success(self, mock_confirmation):
        """Test successfully reserving a specific room."""
        start = datetime(2026, 12, 30, 9, 0)
        end = datetime(2026, 12, 30, 11, 0)
        
        result = reserve_room(self.db, 3, start, end, "Alice", "Ruang Merapi")
        self.assertIn("success", result)
        self.assertIn("Ruang Merapi", result["success"])
        
        # Verify persistence in db
        d_key = date(2026, 12, 30)
        self.assertEqual(len(self.db["Ruang Merapi"][d_key]), 1)
        self.assertEqual(self.db["Ruang Merapi"][d_key][0].name, "Alice")

    def test_reserve_room_non_existent(self):
        """Test that reserving a room that doesn't exist returns an error."""
        start = datetime(2026, 12, 30, 9, 0)
        end = datetime(2026, 12, 30, 11, 0)
        
        result = reserve_room(self.db, 3, start, end, "Bob", "Ruang Angkasa")
        self.assertIn("error", result)
        self.assertIn("does not exist", result["error"])

    def test_reserve_room_insufficient_capacity(self):
        """Test that booking a room with too many people for its capacity fails."""
        start = datetime(2026, 12, 30, 9, 0)
        end = datetime(2026, 12, 30, 11, 0)
        
        # Ruang Merapi capacity is 4, trying to pack 10 people
        result = reserve_room(self.db, 10, start, end, "Charlie", "Ruang Merapi")
        self.assertIn("error", result)
        self.assertIn("insufficient", result["error"])

    @patch('tools.user_confirmation', return_value=True)
    def test_reserve_room_scheduling_conflict(self, mock_confirmation):
        """Test that overlapping reservations on the same room are blocked with a conflict error."""
        start1 = datetime(2026, 12, 30, 9, 0)
        end1 = datetime(2026, 12, 30, 11, 0)
        
        # 1. First booking succeeds
        reserve_room(self.db, 2, start1, end1, "David", "Ruang Merapi")
        
        # 2. Overlapping booking on the same room should fail
        start2 = datetime(2026, 12, 30, 10, 0)
        end2 = datetime(2026, 12, 30, 12, 0)
        
        result = reserve_room(self.db, 2, start2, end2, "Eve", "Ruang Merapi")
        self.assertIn("error", result)
        self.assertIn("scheduling conflict", result["error"])

    def test_show_reservation_empty(self):
        """Test show_reservations returns a string list indicating empty reservations for all rooms."""
        query_datetime = datetime(2026, 12, 30, 9, 0)
        result = show_reservations(self.db, query_datetime)
        
        self.assertIn("list of rooms", result)
        rooms_list_str = result["list of rooms"]
        
        # Since it returns a string representation, check that room names and 'empty' appear in it
        self.assertIsInstance(rooms_list_str, str)
        self.assertIn("Ruang Merapi", rooms_list_str)
        self.assertIn("Ruang Bromo", rooms_list_str)
        self.assertIn("empty", rooms_list_str)

    @patch('tools.user_confirmation', return_value=True)
    def test_show_reservation_with_active_bookings(self, mock_confirmation):
        """Test show_reservations string output correctly contains active appointment details."""
        start = datetime(2026, 12, 30, 9, 0)
        end = datetime(2026, 12, 30, 11, 0)
        
        # Book an appointment in Ruang Merapi
        reserve_room(self.db, 2, start, end, "Alice", "Ruang Merapi")
        
        # Query reservations for that date
        query_datetime = datetime(2026, 12, 30, 10, 0)
        result = show_reservations(self.db, query_datetime)
        
        self.assertIn("list of rooms", result)
        rooms_list_str = result["list of rooms"]
        
        # Verify output is a string containing the booker's name and room name
        self.assertIsInstance(rooms_list_str, str)
        self.assertIn("Ruang Merapi", rooms_list_str)
        self.assertIn("Alice", rooms_list_str)


if __name__ == "__main__":
    unittest.main()