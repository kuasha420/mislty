"""
mislty.core.at_parser
~~~~~~~~~~~~~~~~~~~~~

Hayes AT syntax parser, 3GPP TS 27.007 / 27.005 terminal error decoders,
priority command dispatching, and asynchronous URC filtering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import queue
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from mislty.core.serial_transport import SerialTransport, SerialTransportError


# 3GPP TS 27.007 Mobile Equipment Error Codes (+CME ERROR)
CME_ERRORS: Dict[int, str] = {
    0: "Phone failure",
    1: "No connection to phone",
    2: "Phone-adapter link reserved",
    3: "Operation not allowed",
    4: "Operation not supported",
    5: "PH-SIM PIN required",
    6: "PH-FSIM PIN required",
    7: "PH-FSIM PUK required",
    10: "SIM not inserted",
    11: "SIM PIN required",
    12: "SIM PUK required",
    13: "SIM failure",
    14: "SIM busy",
    15: "SIM wrong",
    16: "Incorrect password",
    17: "SIM PIN2 required",
    18: "SIM PUK2 required",
    20: "Memory full",
    21: "Invalid index",
    22: "Not found",
    23: "Memory failure",
    24: "Text string too long",
    25: "Invalid characters in text string",
    26: "Dial string too long",
    27: "Invalid characters in dial string",
    30: "No network service",
    31: "Network timeout",
    32: "Network not allowed - emergency calls only",
    40: "Network personalization PIN required",
    100: "Unknown error",
}

# 3GPP TS 27.005 Short Message Service Error Codes (+CMS ERROR)
CMS_ERRORS: Dict[int, str] = {
    300: "ME failure",
    301: "SMS service of ME reserved",
    302: "Operation not allowed",
    303: "Operation not supported",
    304: "Invalid PDU mode parameter",
    305: "Invalid text mode parameter",
    310: "SIM not inserted",
    311: "SIM PIN required",
    312: "PH-SIM PIN required",
    313: "SIM failure",
    314: "SIM busy",
    315: "SIM wrong",
    316: "SIM PUK required",
    317: "SIM PIN2 required",
    318: "SIM PUK2 required",
    320: "Memory failure",
    321: "Invalid memory index",
    322: "Memory full",
    330: "SC address unknown",
    331: "No network service",
    332: "Network timeout",
    500: "Unknown error",
    512: "Facility not implemented",
}

# Known unsolicited result code prefixes
URC_PATTERNS = [
    re.compile(r"^\+CMTI:"),             # SMS indicator
    re.compile(r"^\+CLIP:"),             # Calling line identification
    re.compile(r"^RING\b"),              # Incoming ring
    re.compile(r"^\^MODE:"),             # Qualcomm system mode indication
    re.compile(r"^\^RSSI:"),             # Qualcomm RSSI indication
    re.compile(r"^\+CREG:"),             # Network registration URC
    re.compile(r"^\+CGREG:"),            # GPRS network registration URC
    re.compile(r"^\+CEREG:"),            # EPS network registration URC
    re.compile(r"^\^SYSINFO:"),          # Qualcomm system info
    re.compile(r"^\^DSFLOWRPT:"),        # Qualcomm data flow report
]


@dataclass(order=True)
class AtCommand:
    """
    AT Command transaction request.
    Ordered by priority (0=urgent, 1=normal, 2=telemetry background).
    """
    priority: int = 1
    command: str = field(compare=False, default="")
    timeout: float = field(compare=False, default=3.0)
    expected_prefix: Optional[str] = field(compare=False, default=None)
    prompt_mode: bool = field(compare=False, default=False)
    created_at: float = field(compare=False, default_factory=time.time)


@dataclass
class AtResponse:
    """
    Result of an AT command transaction.
    """
    command: str
    success: bool
    lines: List[str]
    raw_text: str
    error: Optional[str] = None
    error_code: Optional[int] = None
    error_detail: Optional[str] = None
    is_prompt: bool = False
    execution_time_ms: float = 0.0

    @property
    def value(self) -> Optional[str]:
        """Returns the primary payload line if available."""
        return self.lines[0] if self.lines else None

    def as_dict(self) -> Dict[str, Any]:
        """Serialize response to dictionary."""
        return {
            "command": self.command,
            "success": self.success,
            "lines": self.lines,
            "raw_text": self.raw_text,
            "error": self.error,
            "error_code": self.error_code,
            "error_detail": self.error_detail,
            "is_prompt": self.is_prompt,
            "execution_time_ms": round(self.execution_time_ms, 2),
        }

    def __str__(self) -> str:
        if self.success:
            return "\n".join(self.lines) if self.lines else "OK"
        err = self.error or "ERROR"
        detail = f" ({self.error_detail})" if self.error_detail else ""
        return f"{err}{detail}"


def is_urc(line: str) -> bool:
    """Check if a line matches any known unsolicited result code."""
    line_clean = line.strip()
    return any(pat.search(line_clean) for pat in URC_PATTERNS)


def parse_error(error_line: str) -> Tuple[str, Optional[int], Optional[str]]:
    """
    Parse CME/CMS/generic error lines into (error_type, error_code, error_description).
    """
    clean = error_line.strip()

    # Match +CME ERROR: <err>
    cme_match = re.match(r"^\+CME ERROR:\s*(\d+)", clean)
    if cme_match:
        code = int(cme_match.group(1))
        return clean, code, CME_ERRORS.get(code, "Unknown CME error")

    # Match +CMS ERROR: <err>
    cms_match = re.match(r"^\+CMS ERROR:\s*(\d+)", clean)
    if cms_match:
        code = int(cms_match.group(1))
        return clean, code, CMS_ERRORS.get(code, "Unknown CMS error")

    return clean, None, None


class AtParser:
    """
    State machine parser for Hayes AT response sequences.
    """

    TERMINAL_SUCCESS_TOKENS = ("OK", "CONNECT")
    TERMINAL_FAILURE_TOKENS = (
        "ERROR",
        "NO CARRIER",
        "BUSY",
        "NO DIALTONE",
        "NO ANSWER",
        "COMMAND NOT SUPPORT",
    )

    def __init__(self, urc_callback: Optional[Callable[[str], None]] = None) -> None:
        self.urc_callback = urc_callback

    def parse_transaction(
        self,
        command_str: str,
        raw_lines: List[str],
        prompt_mode: bool = False,
        execution_time_ms: float = 0.0,
    ) -> AtResponse:
        """
        Parse raw lines emitted in response to command_str.
        """
        clean_command = command_str.strip()
        filtered_lines: List[str] = []
        terminal_status: Optional[str] = None
        is_prompt = False

        for raw_line in raw_lines:
            line = raw_line.strip()
            if not line:
                continue

            # Strip command echo if present (e.g. ATE1 echo)
            if line == clean_command or line == f"{clean_command}\r":
                continue

            # Check for interactive prompt ('> ')
            if prompt_mode and line.endswith(">"):
                is_prompt = True
                terminal_status = "PROMPT"
                break

            # Check for terminal tokens
            if any(line == tok or line.startswith(f"{tok} ") for tok in self.TERMINAL_SUCCESS_TOKENS):
                terminal_status = line
                break

            if any(line == tok or line.startswith(f"{tok} ") for tok in self.TERMINAL_FAILURE_TOKENS):
                terminal_status = line
                break

            if line.startswith("+CME ERROR:") or line.startswith("+CMS ERROR:"):
                terminal_status = line
                break

            # Filter URCs
            if is_urc(line):
                if self.urc_callback:
                    try:
                        self.urc_callback(line)
                    except Exception:
                        pass
                continue

            filtered_lines.append(line)

        # Determine success / failure
        if terminal_status in ("PROMPT",) or is_prompt:
            return AtResponse(
                command=command_str,
                success=True,
                lines=filtered_lines,
                raw_text="\n".join(raw_lines),
                is_prompt=True,
                execution_time_ms=execution_time_ms,
            )

        if terminal_status and any(
            terminal_status == tok or terminal_status.startswith(f"{tok} ")
            for tok in self.TERMINAL_SUCCESS_TOKENS
        ):
            return AtResponse(
                command=command_str,
                success=True,
                lines=filtered_lines,
                raw_text="\n".join(raw_lines),
                execution_time_ms=execution_time_ms,
            )

        # Handle failure or timeout
        err_str, err_code, err_detail = (
            parse_error(terminal_status) if terminal_status else ("TIMEOUT", None, "Command timed out")
        )

        return AtResponse(
            command=command_str,
            success=False,
            lines=filtered_lines,
            raw_text="\n".join(raw_lines),
            error=err_str,
            error_code=err_code,
            error_detail=err_detail,
            execution_time_ms=execution_time_ms,
        )


class AtDispatcher:
    """
    Priority command queue dispatcher executing AT transactions over a SerialTransport.
    Thread-safe and supports synchronous dispatch with priority preemption.
    """

    def __init__(
        self,
        transport: SerialTransport,
        urc_callback: Optional[Callable[[str], None]] = None,
        lock: Optional[Union[threading.Lock, threading.RLock]] = None,
    ) -> None:
        self.transport = transport
        self.parser = AtParser(urc_callback=urc_callback)
        self._lock = lock if lock is not None else threading.RLock()


    def set_urc_callback(self, callback: Optional[Callable[[str], None]]) -> None:
        """Register or update URC callback."""
        self.parser.urc_callback = callback

    def execute(
        self,
        cmd: Union[AtCommand, str],
        timeout: Optional[float] = None,
    ) -> AtResponse:
        """
        Execute an AT command transaction synchronously under lock.
        """
        if isinstance(cmd, str):
            at_cmd = AtCommand(command=cmd, timeout=timeout or 3.0)
        else:
            at_cmd = cmd
            if timeout is not None:
                at_cmd.timeout = timeout

        with self._lock:
            start_time = time.monotonic()
            raw_lines: List[str] = []

            # Ensure transport is open
            if not self.transport.is_open:
                self.transport.open()

            # Flush stale input from buffer
            self.transport.flush_input()

            # Send command terminated with CR LF
            cmd_payload = at_cmd.command.strip() + "\r\n"
            try:
                self.transport.write(cmd_payload)
            except SerialTransportError as exc:
                elapsed = (time.monotonic() - start_time) * 1000.0
                return AtResponse(
                    command=at_cmd.command,
                    success=False,
                    lines=[],
                    raw_text="",
                    error="TRANSPORT_ERROR",
                    error_detail=str(exc),
                    execution_time_ms=elapsed,
                )

            # Read response lines until terminal token or timeout
            deadline = time.monotonic() + at_cmd.timeout
            while time.monotonic() < deadline:
                rem_timeout = max(0.05, deadline - time.monotonic())
                line = self.transport.read_line(timeout=rem_timeout)
                if line is None:
                    continue

                clean_line = line.strip()
                if clean_line:
                    raw_lines.append(clean_line)

                # Check if prompt mode reached
                if at_cmd.prompt_mode and clean_line.endswith(">"):
                    break

                # Check if terminal status reached
                if any(
                    clean_line == tok or clean_line.startswith(f"{tok} ")
                    for tok in self.parser.TERMINAL_SUCCESS_TOKENS
                ):
                    break
                if any(
                    clean_line == tok or clean_line.startswith(f"{tok} ")
                    for tok in self.parser.TERMINAL_FAILURE_TOKENS
                ):
                    break
                if clean_line.startswith("+CME ERROR:") or clean_line.startswith("+CMS ERROR:"):
                    break

            elapsed_ms = (time.monotonic() - start_time) * 1000.0
            return self.parser.parse_transaction(
                at_cmd.command,
                raw_lines,
                prompt_mode=at_cmd.prompt_mode,
                execution_time_ms=elapsed_ms,
            )
