import unittest
import socket
import json
import time
import os
import tempfile


class TestMindDrawAddon(unittest.TestCase):
    """
    Unit and Integration tests for the MindDraw Blender addon.

    This test suite acts as a client to the addon's socket server.
    To run these tests:
    1. Open Blender.
    2. Install and enable the 'render/addon.py' script as an addon.
       (Edit > Preferences > Add-ons > Install...)
    3. Run this Python script from your terminal: `python test/test_addon.py`
    """

    HOST = "localhost"
    PORT = 8765
    _render_output_path = None

    @classmethod
    def tearDownClass(cls):
        """Clean up any files created during tests."""
        if cls._render_output_path and os.path.exists(cls._render_output_path):
            try:
                os.remove(cls._render_output_path)
                print(f"\nCleaned up rendered file: {cls._render_output_path}")
                # Clean up directory if empty
                dir_path = os.path.dirname(cls._render_output_path)
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
            except Exception as e:
                print(f"Error cleaning up file: {e}")

    def _send_command(self, command: str, payload: dict = None) -> dict:
        """Helper function to send a command to the Blender socket server."""
        if payload is None:
            payload = {}
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((self.HOST, self.PORT))
                request = {"command": command, "payload": payload}
                s.sendall(json.dumps(request).encode("utf-8"))
                response_data = s.recv(4096)
                return json.loads(response_data.decode("utf-8"))
            except ConnectionRefusedError:
                self.fail(
                    f"Connection to {self.HOST}:{self.PORT} was refused. "
                    "Is Blender running with the MindDraw addon enabled?"
                )
            except Exception as e:
                self.fail(f"An unexpected error occurred: {e}")

    def test_01_server_connection_and_blender_info(self):
        """Test if the server is reachable and get basic Blender info."""
        print("\nTesting: Server Connection & Blender Info")
        response = self._send_command("get_blender_info")
        self.assertEqual(
            response["status"],
            "success",
            f"Server returned an error response: {response}",
        )
        self.assertIn("blender_version", response["data"])
        self.assertIsInstance(response["data"]["blender_version"], str)
        print(f"  Success: Connected to Blender {response['data']['blender_version']}")

    def test_02_get_scene_info(self):
        """Test the get_scene_info command."""
        print("Testing: Get Scene Info")
        response = self._send_command("get_scene_info")
        self.assertEqual(
            response["status"],
            "success",
            f"Server returned an error response: {response}",
        )
        data = response["data"]
        self.assertIn("scene_name", data)
        self.assertIn("object_count", data)
        self.assertIn("active_object", data)
        self.assertIn("selected_objects", data)
        self.assertIn("mode", data)
        print("  Success: Received valid scene info.")

    def test_03_execute_code(self):
        """Test the execute_code command."""
        print("Testing: Execute Code")
        code_to_run = "print('Hello from test!')"
        response = self._send_command("execute_code", {"code": code_to_run})
        self.assertEqual(
            response["status"],
            "success",
            f"Server returned an error response: {response}",
        )
        self.assertIn("Hello from test!", response["data"]["output"])
        print("  Success: Code execution and output capture work.")

    def test_04_draw_stroke(self):
        """Test the draw_stroke command."""
        print("Testing: Draw Stroke")
        stroke_payload = {
            "layer_name": "TestStrokeLayer",
            "color": [1.0, 0.0, 0.0, 1.0],  # Red
            "points": [
                {"x": 0, "y": 0, "z": 0},
                {"x": 1, "y": 0, "z": 1},
                {"x": 2, "y": 0, "z": 0},
            ],
            "clear_layer": True,
        }
        response = self._send_command("draw_stroke", stroke_payload)
        self.assertEqual(
            response["status"],
            "success",
            f"Server returned an error response: {response}",
        )
        self.assertIn("Stroke with 3 points drawn", response["data"]["message"])
        print("  Success: draw_stroke command acknowledged.")

    def test_05_draw_circle(self):
        """Test the draw_circle command."""
        print("Testing: Draw Circle")
        circle_payload = {
            "layer_name": "TestCircleLayer",
            "color": [0.0, 0.0, 1.0, 1.0],  # Blue
            "radius": 2.5,
            "center": [0, 0, 0],
            "clear_layer": True,
        }
        response = self._send_command("draw_circle", circle_payload)
        self.assertEqual(
            response["status"],
            "success",
            f"Server returned an error response: {response}",
        )
        self.assertIn("Stroke with 65 points drawn", response["data"]["message"])
        print("  Success: draw_circle command acknowledged.")

    def test_06_render_image(self):
        """Test the render_image command and verify file creation."""
        print("Testing: Render Image")
        # Using a temporary directory for the output
        temp_dir = tempfile.mkdtemp(prefix="mindraw_test_render_")
        output_path = os.path.join(temp_dir, "test_render.png")
        self.__class__._render_output_path = output_path

        render_payload = {
            "output_path": output_path,
            "resolution_x": 128,
            "resolution_y": 128,
        }
        response = self._send_command("render_image", render_payload)
        self.assertEqual(
            response["status"],
            "success",
            f"Server returned an error response: {response}",
        )
        self.assertEqual(response["data"]["image_path"], output_path)

        # Verify that the file was actually created
        self.assertTrue(
            os.path.exists(output_path), f"Rendered file not found at {output_path}"
        )
        self.assertTrue(os.path.getsize(output_path) > 0, "Rendered file is empty.")
        print(f"  Success: Image rendered to {output_path}")

    def test_07_unknown_command(self):
        """Test sending a command that does not exist."""
        print("Testing: Unknown Command")
        response = self._send_command("non_existent_command")
        self.assertEqual(response["status"], "error")
        self.assertIn("Unknown command", response["error_message"])
        print("  Success: Server correctly handled an unknown command.")

    def test_08_invalid_payload(self):
        """Test sending a command with an invalid or incomplete payload."""
        print("Testing: Invalid Payload")
        response = self._send_command("draw_stroke", {"layer_name": "bad_layer"})
        self.assertEqual(response["status"], "error")
        self.assertIn("must contain", response["error_message"])
        print("  Success: Server correctly handled a payload with missing keys.")


if __name__ == "__main__":
    print("=" * 70)
    print("      Running MindDraw Addon Integration Tests")
    print("=" * 70)
    print("  This script will attempt to connect to a running Blender instance")
    print("  with the MindDraw addon enabled. Please ensure Blender is ready.")
    print("-" * 70)
    time.sleep(2)  # Give user a moment to read the header

    unittest.main(verbosity=0)
