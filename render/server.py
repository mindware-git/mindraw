# server.py
from fastmcp import FastMCP
import socket
import threading
import time

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


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


@mcp.tool
def execute_blender_command(python_code: str) -> str:
    """Blender에서 Python 코드를 실행하고 결과를 반환합니다

    Args:
        python_code: Blender에서 실행할 Python 코드

    Returns:
        실행 결과 또는 에러 메시지
    """
    # 연결 상태 확인 및 재연결
    if not ensure_connection():
        return "ERROR: Blender에 연결할 수 없습니다. Blender addon이 실행 중인지 확인하세요."

    try:
        with socket_lock:
            if not blender_socket:
                return "ERROR: 소켓 연결이 없습니다"

            # Python 코드 전송
            blender_socket.sendall(python_code.encode("utf-8"))

            # 결과 수신
            result = blender_socket.recv(4096).decode("utf-8")

            return result

    except socket.timeout:
        print("[Blender MCP] Socket timeout, attempting to reconnect...")
        with socket_lock:
            socket_connected = False
        return "ERROR: 타임아웃 - Blender addon이 응답하지 않습니다"
    except Exception as e:
        print(f"[Blender MCP] Error executing command: {e}")
        with socket_lock:
            socket_connected = False
        return f"ERROR: {str(e)}"


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
