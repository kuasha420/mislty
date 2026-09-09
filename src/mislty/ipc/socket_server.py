"""
mislty.ipc.socket_server
~~~~~~~~~~~~~~~~~~~~~~~~

High-performance standard-library Unix Domain Socket JSON-RPC 2.0 server.
Listens on /run/user/$UID/mislty/mislty.sock with user-only permissions (0600).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import socket
import threading
from typing import Any, Dict, List, Optional, Union

from mislty.ipc.dispatcher import InvalidParamsError, IpcDispatcher, IpcError, MethodNotFoundError

logger = logging.getLogger("mislty.ipc.socket")


def get_default_socket_path() -> Path:
    """Determine canonical Unix domain socket path for current user."""
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir and Path(runtime_dir).is_dir():
        sock_dir = Path(runtime_dir) / "mislty"
    else:
        sock_dir = Path(f"/tmp/mislty-{os.getuid()}")

    sock_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(sock_dir, 0o700)
    except OSError:
        pass

    return sock_dir / "mislty.sock"


class JsonRpcSocketServer:
    """
    Multithreaded JSON-RPC 2.0 Unix Domain Socket Server.
    """

    def __init__(
        self,
        dispatcher: IpcDispatcher,
        socket_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.dispatcher = dispatcher
        self.socket_path = Path(socket_path) if socket_path else get_default_socket_path()
        self.server_sock: Optional[socket.socket] = None
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._client_threads: List[threading.Thread] = []
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> None:
        """Start socket server and listen for local client connections."""
        with self._lock:
            if self._is_running:
                return

            self._cleanup_stale_socket()

            self.server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server_sock.bind(str(self.socket_path))
            try:
                os.chmod(self.socket_path, 0o600)
            except OSError as exc:
                logger.warning("Could not set 0600 permissions on %s: %s", self.socket_path, exc)

            self.server_sock.listen(16)
            self._is_running = True

            self._thread = threading.Thread(
                target=self._accept_loop,
                name="mislty-sock-accept",
                daemon=True,
            )
            self._thread.start()
            logger.info("JSON-RPC socket server listening on %s", self.socket_path)

    def stop(self) -> None:
        """Terminate socket server and remove socket file."""
        with self._lock:
            if not self._is_running:
                return

            self._is_running = False

            if self.server_sock:
                try:
                    self.server_sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                self.server_sock.close()
                self.server_sock = None

            try:
                if self.socket_path.exists():
                    self.socket_path.unlink(missing_ok=True)
            except OSError:
                pass

            logger.info("JSON-RPC socket server stopped.")

    def _cleanup_stale_socket(self) -> None:
        """Unlink existing socket file if no process is currently listening."""
        if not self.socket_path.exists():
            return

        test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            test_sock.connect(str(self.socket_path))
            test_sock.close()
            raise RuntimeError(f"Another process is already listening on {self.socket_path}")
        except OSError:
            # Stale socket from previous ungraceful shutdown
            try:
                self.socket_path.unlink()
                logger.debug("Cleaned up stale socket at %s", self.socket_path)
            except OSError as exc:
                logger.warning("Failed to unlink stale socket: %s", exc)

    def _accept_loop(self) -> None:
        """Accept incoming client socket connections."""
        while self._is_running and self.server_sock:
            try:
                client_sock, _ = self.server_sock.accept()
            except OSError:
                break

            t = threading.Thread(
                target=self._handle_client,
                args=(client_sock,),
                name="mislty-sock-client",
                daemon=True,
            )
            t.start()
            self._client_threads.append(t)

    def _handle_client(self, client_sock: socket.socket) -> None:
        """Handle communication session with a connected client."""
        client_sock.settimeout(30.0)
        buffer = ""

        try:
            while self._is_running:
                try:
                    chunk = client_sock.recv(4096).decode("utf-8")
                except (socket.timeout, OSError):
                    break

                if not chunk:
                    break

                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    response_bytes = self._process_request(line)
                    if response_bytes:
                        client_sock.sendall(response_bytes)
        finally:
            try:
                client_sock.close()
            except OSError:
                pass

    def _process_request(self, raw_json: str) -> Optional[bytes]:
        """Process a single JSON-RPC 2.0 request and formulate response."""
        req_id: Optional[Union[str, int]] = None
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
                "id": None,
            }
            return (json.dumps(err_resp) + "\n").encode("utf-8")

        if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0" or "method" not in payload:
            err_resp = {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request: must contain jsonrpc 2.0 and method"},
                "id": payload.get("id") if isinstance(payload, dict) else None,
            }
            return (json.dumps(err_resp) + "\n").encode("utf-8")

        req_id = payload.get("id")
        method = payload["method"]
        params = payload.get("params")

        try:
            result = self.dispatcher.dispatch(method, params)
            if req_id is None:
                # Notification: no response sent
                return None

            success_resp = {
                "jsonrpc": "2.0",
                "result": result,
                "id": req_id,
            }
            return (json.dumps(success_resp) + "\n").encode("utf-8")

        except MethodNotFoundError as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": str(exc)},
                "id": req_id,
            }
            return (json.dumps(err_resp) + "\n").encode("utf-8")

        except InvalidParamsError as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": str(exc)},
                "id": req_id,
            }
            return (json.dumps(err_resp) + "\n").encode("utf-8")

        except IpcError as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "error": {"code": exc.code, "message": str(exc), "data": exc.data},
                "id": req_id,
            }
            return (json.dumps(err_resp) + "\n").encode("utf-8")

        except Exception as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {exc}"},
                "id": req_id,
            }
            return (json.dumps(err_resp) + "\n").encode("utf-8")
