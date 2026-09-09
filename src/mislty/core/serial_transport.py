"""
mislty.core.serial_transport
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

POSIX non-blocking serial communication layer using Python standard library
(termios, fcntl, select, os) without external dependencies (no pyserial).
Provides exclusive advisory locking via flock to eliminate race conditions
and multi-process clobbering on serial device nodes.
"""

from __future__ import annotations

import errno
import fcntl
import os
from pathlib import Path
import select
import termios
from typing import Optional, Union


class SerialTransportError(Exception):
    """Base exception for all serial transport errors."""
    pass


class PortNotFoundError(SerialTransportError):
    """Raised when the specified serial device node does not exist."""
    pass


class PortBusyError(SerialTransportError):
    """Raised when another process holds an exclusive advisory lock on the port."""
    pass


class SerialTimeoutError(SerialTransportError):
    """Raised when a read or write operation times out."""
    pass


class SerialTransport:
    """
    Non-blocking, POSIX-compliant serial transport with exclusive flock locking.
    """

    BAUD_MAP = {
        9600: termios.B9600,
        19200: termios.B19200,
        38400: termios.B38400,
        57600: termios.B57600,
        115200: termios.B115200,
        230400: termios.B230400,
        460800: getattr(termios, "B460800", termios.B115200),
        921600: getattr(termios, "B921600", termios.B115200),
    }

    def __init__(
        self,
        port: Union[str, Path],
        baudrate: int = 115200,
        timeout: float = 1.0,
        exclusive_lock: bool = True,
    ) -> None:
        self.port = Path(port)
        self.baudrate = baudrate
        self.timeout = timeout
        self.exclusive_lock = exclusive_lock
        self._fd: Optional[int] = None
        self._is_locked: bool = False
        self._rx_buffer = bytearray()

    @property
    def is_open(self) -> bool:
        """Returns True if the serial file descriptor is open."""
        return self._fd is not None

    def open(self) -> None:
        """
        Open the serial device node, acquire exclusive advisory lock, and
        configure 8N1 raw mode terminal attributes.
        """
        if self.is_open:
            return

        if not self.port.exists():
            raise PortNotFoundError(f"Serial device node not found: {self.port}")

        # Open non-blocking, read/write, no controlling tty
        flags = os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK
        try:
            fd = os.open(str(self.port), flags)
        except OSError as exc:
            raise SerialTransportError(f"Failed to open {self.port}: {exc}") from exc

        # Acquire exclusive advisory lock to guard against multi-process clobbering
        if self.exclusive_lock:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._is_locked = True
            except OSError as exc:
                os.close(fd)
                if exc.errno in (errno.EWOULDBLOCK, errno.EAGAIN, errno.EACCES):
                    raise PortBusyError(
                        f"Device {self.port} is exclusively locked by another process."
                    ) from exc
                raise SerialTransportError(
                    f"Failed to acquire advisory lock on {self.port}: {exc}"
                ) from exc

        # Configure POSIX termios raw mode
        try:
            attrs = termios.tcgetattr(fd)
            # Input flags: no break, no parity, no strip, no cr-to-nl, no software flow control
            attrs[0] &= ~(
                termios.IGNBRK
                | termios.BRKINT
                | termios.PARMRK
                | termios.ISTRIP
                | termios.INLCR
                | termios.IGNCR
                | termios.ICRNL
                | termios.IXON
                | termios.IXOFF
            )
            # Output flags: raw output
            attrs[1] &= ~termios.OPOST
            # Control flags: 8 bits, no parity, 1 stop bit, enable receiver, ignore control lines
            attrs[2] &= ~(
                termios.CSIZE
                | termios.PARENB
                | termios.CSTOPB
                | getattr(termios, "CRTSCTS", 0)
            )
            attrs[2] |= termios.CS8 | termios.CREAD | termios.CLOCAL
            # Local flags: disable echo, canonical mode, signal chars, extended input
            attrs[3] &= ~(
                termios.ECHO
                | termios.ECHONL
                | termios.ICANON
                | termios.ISIG
                | termios.IEXTEN
            )
            # Set input/output baud rate
            baud_const = self.BAUD_MAP.get(self.baudrate, termios.B115200)
            attrs[4] = baud_const
            attrs[5] = baud_const
            # Non-blocking character reading
            attrs[6][termios.VMIN] = 0
            attrs[6][termios.VTIME] = 0

            termios.tcsetattr(fd, termios.TCSANOW, attrs)
            termios.tcflush(fd, termios.TCIOFLUSH)
        except (termios.error, OSError) as exc:
            if self._is_locked:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except OSError:
                    pass
            os.close(fd)
            raise SerialTransportError(f"Failed to configure termios for {self.port}: {exc}") from exc

        self._fd = fd
        self._rx_buffer.clear()

    def close(self) -> None:
        """
        Release locks and close the serial file descriptor.
        """
        if self._fd is None:
            return

        fd = self._fd
        self._fd = None
        self._rx_buffer.clear()

        try:
            if self._is_locked:
                fcntl.flock(fd, fcntl.LOCK_UN)
                self._is_locked = False
        except OSError:
            pass
        finally:
            try:
                os.close(fd)
            except OSError:
                pass

    def __enter__(self) -> SerialTransport:
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def write(self, data: Union[bytes, str]) -> int:
        """
        Write data to serial port and block until transmitted.
        """
        if self._fd is None:
            raise SerialTransportError(f"Cannot write: port {self.port} is not open.")

        raw_bytes = data.encode("utf-8") if isinstance(data, str) else data
        total_written = 0
        while total_written < len(raw_bytes):
            # Wait for write readiness
            _, w, _ = select.select([], [self._fd], [], self.timeout)
            if not w:
                raise SerialTimeoutError(f"Write timeout on port {self.port}")
            written = os.write(self._fd, raw_bytes[total_written:])
            total_written += written

        try:
            termios.tcdrain(self._fd)
        except (termios.error, OSError):
            pass

        return total_written

    def read(self, max_bytes: int = 4096, timeout: Optional[float] = None) -> bytes:
        """
        Read up to max_bytes from the serial port within timeout seconds.
        """
        if self._fd is None:
            raise SerialTransportError(f"Cannot read: port {self.port} is not open.")

        # Drain from internal buffer first if populated
        if self._rx_buffer:
            chunk = bytes(self._rx_buffer[:max_bytes])
            del self._rx_buffer[:max_bytes]
            return chunk

        tout = self.timeout if timeout is None else timeout
        r, _, _ = select.select([self._fd], [], [], tout)
        if not r:
            return b""

        try:
            return os.read(self._fd, max_bytes)
        except BlockingIOError:
            return b""
        except OSError as exc:
            raise SerialTransportError(f"Read error on {self.port}: {exc}") from exc

    def read_line(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Read a single CR/LF terminated line from the port within timeout.
        Returns None if timeout expires before newline is received.
        """
        if self._fd is None:
            raise SerialTransportError(f"Cannot read_line: port {self.port} is not open.")

        tout = self.timeout if timeout is None else timeout

        while True:
            # Check if a complete line exists in _rx_buffer
            nl_pos = -1
            for idx, byte in enumerate(self._rx_buffer):
                if byte in (10, 13):  # \n or \r
                    nl_pos = idx
                    break

            if nl_pos != -1:
                line_bytes = self._rx_buffer[:nl_pos]
                # Consume trailing CR/LF sequence
                consume_end = nl_pos + 1
                while consume_end < len(self._rx_buffer) and self._rx_buffer[consume_end] in (10, 13):
                    consume_end += 1
                del self._rx_buffer[:consume_end]
                return line_bytes.decode("utf-8", errors="replace").strip()

            # Need more data: poll with select
            r, _, _ = select.select([self._fd], [], [], tout)
            if not r:
                # Timeout reached
                if self._rx_buffer:
                    # Return remaining buffer if any
                    line = bytes(self._rx_buffer).decode("utf-8", errors="replace").strip()
                    self._rx_buffer.clear()
                    return line if line else None
                return None

            try:
                chunk = os.read(self._fd, 1024)
                if not chunk:
                    return None
                self._rx_buffer.extend(chunk)
            except BlockingIOError:
                return None
            except OSError as exc:
                raise SerialTransportError(f"Read error on {self.port}: {exc}") from exc

    def flush_input(self) -> None:
        """Discard all pending input from hardware FIFO and internal buffer."""
        self._rx_buffer.clear()
        if self._fd is not None:
            try:
                termios.tcflush(self._fd, termios.TCIFLUSH)
            except (termios.error, OSError):
                pass
