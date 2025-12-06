# server.py
from fastmcp import FastMCP
import socket
import threading
import time
import json

# 전역 소켓 연결 변수
blender_socket = None
socket_connected = False
socket_lock = threading.Lock()


def connect_to_blender():
    """Blender addon 소켓 서버에 연결"""
    global blender_socket, socket_connected

    HOST = "localhost"
    PORT = 8765

    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            print(
                f"[Blender MCP] Attempting to connect to Blender (attempt {attempt + 1}/{max_retries})"
            )

            blender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            blender_socket.settimeout(10.0)
            blender_socket.connect((HOST, PORT))

            with socket_lock:
                socket_connected = True

            print("[Blender MCP] Successfully connected to Blender addon")
            return True

        except Exception as e:
            print(f"[Blender MCP] Connection attempt {attempt + 1} failed: {e}")

            if blender_socket:
                blender_socket.close()
                blender_socket = None

            if attempt < max_retries - 1:
                print(f"[Blender MCP] Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)

    print("[Blender MCP] Failed to connect to Blender after all attempts")
    return False


def disconnect_from_blender():
    """Blender 소켓 연결 해제"""
    global blender_socket, socket_connected

    with socket_lock:
        if blender_socket:
            try:
                blender_socket.close()
            except:
                pass
            blender_socket = None
            socket_connected = False

    try:
        print("[Blender MCP] Disconnected from Blender")
    except:
        pass  # 출력이 닫혀있으면 무시


def ensure_connection():
    """소켓 연결 상태 확인 및 재연결"""
    global socket_connected

    with socket_lock:
        if not socket_connected or not blender_socket:
            return connect_to_blender()

    return True


# MCP 서버 생성 전에 Blender에 연결
print("[Blender MCP] Connecting to Blender before starting MCP server...")
connect_to_blender()

mcp = FastMCP("Blender MCP")


def _send_blender_command(command: str, payload: dict) -> dict:
    """
    Sends a structured JSON command to the Blender addon and returns the response.

    Args:
        command: The command to execute (e.g., 'execute_code', 'get_scene_info').
        payload: A dictionary of data for the command.

    Returns:
        A dictionary containing the parsed JSON response from the addon.
    """
    if not ensure_connection():
        return {"status": "error", "error_message": "Blender connection failed."}

    try:
        with socket_lock:
            if not blender_socket:
                return {
                    "status": "error",
                    "error_message": "No active socket connection.",
                }

            # Construct and send the JSON request
            request_data = json.dumps({"command": command, "payload": payload})
            blender_socket.sendall(request_data.encode("utf-8"))

            # Receive and parse the JSON response
            response_data = blender_socket.recv(4096).decode("utf-8")
            if not response_data:
                return {
                    "status": "error",
                    "error_message": "Received empty response from Blender.",
                }
            return json.loads(response_data)

    except socket.timeout:
        print("[Blender MCP] Socket timeout, attempting to reconnect...")
        with socket_lock:
            socket_connected = False
        return {
            "status": "error",
            "error_message": "Timeout: Blender addon did not respond.",
        }
    except json.JSONDecodeError:
        return {
            "status": "error",
            "error_message": "Failed to decode JSON response from Blender.",
        }
    except Exception as e:
        print(f"[Blender MCP] Error sending command '{command}': {e}")
        with socket_lock:
            socket_connected = False
        return {"status": "error", "error_message": str(e)}


@mcp.tool
def execute_blender_command(python_code: str) -> str:
    """
    Blender에서 Python 코드를 실행하고 결과를 반환합니다.

    Args:
        python_code: Blender에서 실행할 Python 코드

    Returns:
        실행 결과 또는 에러 메시지
    """
    response = _send_blender_command("execute_code", {"code": python_code})

    if response.get("status") == "success":
        return response.get("data", {}).get("output", "SUCCESS: No output returned.")
    else:
        error_msg = response.get("error_message", "Unknown error.")
        return f"ERROR: {error_msg}"


@mcp.tool
def get_blender_info() -> str:
    """블렌더의 기본 정보(씬 정보)를 가져옵니다."""
    response = _send_blender_command("get_scene_info", {})

    if response.get("status") == "success":
        # Pretty-print the JSON data for readability
        return json.dumps(response.get("data", {}), indent=2)
    else:
        error_msg = response.get("error_message", "Unknown error.")
        return f"ERROR: {error_msg}"


@mcp.tool
def get_connection_status() -> str:
    """Blender와의 연결 상태를 반환합니다"""
    with socket_lock:
        if socket_connected and blender_socket:
            return "CONNECTED: Blender에 정상적으로 연결되어 있습니다"
        else:
            return "DISCONNECTED: Blender에 연결되어 있지 않습니다"


if __name__ == "__main__":
    try:
        print("[Blender MCP] Starting MCP server...")
        mcp.run()
    finally:
        # 서버 종료 시 연결 해제
        disconnect_from_blender()
