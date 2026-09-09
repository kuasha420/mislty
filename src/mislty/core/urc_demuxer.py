"""
mislty.core.urc_demuxer
~~~~~~~~~~~~~~~~~~~~~~~

Asynchronous Unsolicited Result Code (URC) demultiplexer and publish-subscribe event bus.
Intercepts spontaneous modem events (SMS arrivals, incoming voice calls, radio mode changes,
network registration transitions, and RF signal changes) without polling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union

from mislty.core.serial_transport import SerialTransport, SerialTransportError

logger = logging.getLogger("mislty.urc")

T = TypeVar("T", bound="UrcEvent")


@dataclass
class UrcEvent:
    """Base class for all parsed Unsolicited Result Codes."""
    raw_line: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class SmsReceivedEvent(UrcEvent):
    """
    Spontaneous incoming SMS arrival indication (+CMTI: "SM", <index>).
    """
    storage: str = "SM"
    index: int = 1


@dataclass
class IncomingCallEvent(UrcEvent):
    """
    Incoming voice call or ringing indication (RING or +CLIP: "<number>", ...).
    """
    caller_id: Optional[str] = None
    number_type: Optional[int] = None


@dataclass
class CallTerminatedEvent(UrcEvent):
    """
    Call termination or carrier disconnect indication (NO CARRIER, BUSY).
    """
    reason: str = "NO CARRIER"


@dataclass
class NetworkRegistrationEvent(UrcEvent):
    """
    Network registration state transition (+CREG, +CGREG, +CEREG).
    Status:
      0 = Not registered, not searching
      1 = Registered, home network
      2 = Not registered, searching
      3 = Registration denied
      4 = Unknown
      5 = Registered, roaming
    """
    domain: str = "EPS"  # CS, PS, EPS
    status: int = 0
    lac: Optional[str] = None
    ci: Optional[str] = None
    act: Optional[int] = None

    @property
    def is_registered(self) -> bool:
        """True if attached to home or roaming network."""
        return self.status in (1, 5)

    @property
    def is_roaming(self) -> bool:
        """True if attached on a roaming partner network."""
        return self.status == 5


@dataclass
class ModeChangeEvent(UrcEvent):
    """
    Qualcomm radio technology / system mode change indication (^MODE: <sys_mode>, <sub_mode>).
    """
    mode: int = 0
    submode: int = 0

    @property
    def technology(self) -> str:
        """Human-readable Radio Access Technology (RAT) string."""
        mode_map = {
            0: "NO SERVICE",
            1: "AMPS",
            2: "CDMA",
            3: "GSM/GPRS",
            4: "HDR",
            5: "WCDMA",
            6: "GPS",
            7: "GSM/WCDMA",
            8: "LTE",
            9: "TD-SCDMA",
        }
        return mode_map.get(self.mode, f"MODE_{self.mode}")


@dataclass
class SignalChangeEvent(UrcEvent):
    """
    RF signal strength change indication (^RSSI: <rssi> or +CSQ).
    """
    rssi: int = 0

    @property
    def bars(self) -> int:
        """Signal bars 0 to 5."""
        if self.rssi == 99 or self.rssi <= 0:
            return 0
        if self.rssi < 10:
            return 1
        if self.rssi < 15:
            return 2
        if self.rssi < 20:
            return 3
        if self.rssi < 25:
            return 4
        return 5

    @property
    def dbm(self) -> Optional[int]:
        """Signal level in dBm (-113 dBm to -51 dBm)."""
        if self.rssi == 99:
            return None
        return -113 + 2 * self.rssi


@dataclass
class RawUrcEvent(UrcEvent):
    """Fallback event for unspecialized or vendor-specific URCs."""
    pass


class UrcDemuxer:
    """
    Decoupled publish-subscribe event bus for Unsolicited Result Codes.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[Type[UrcEvent], List[Callable[[Any], None]]] = {}
        self._global_subscribers: List[Callable[[UrcEvent], None]] = []
        self._lock = threading.Lock()
        self._listener_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def subscribe(
        self,
        event_type: Type[T],
        callback: Callable[[T], None],
    ) -> Callable[[], None]:
        """
        Subscribe to a specific typed URC event.
        Returns an unsubscribe function.
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if event_type in self._subscribers and callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)

        return unsubscribe

    def subscribe_all(self, callback: Callable[[UrcEvent], None]) -> Callable[[], None]:
        """
        Subscribe to all incoming URC events.
        Returns an unsubscribe function.
        """
        with self._lock:
            self._global_subscribers.append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._global_subscribers:
                    self._global_subscribers.remove(callback)

        return unsubscribe

    def parse_line(self, raw_line: str) -> Optional[UrcEvent]:
        """
        Parse an unsolicited string line into a specialized UrcEvent instance.
        Returns None if line is empty or does not resemble a URC.
        """
        line = raw_line.strip()
        if not line:
            return None

        # 1. SMS arrival: +CMTI: "SM", 1
        m_cmti = re.match(r'^\+CMTI:\s*"([^"]+)",\s*(\d+)', line)
        if m_cmti:
            return SmsReceivedEvent(
                raw_line=line,
                storage=m_cmti.group(1),
                index=int(m_cmti.group(2)),
            )

        # 2. Incoming Call with Caller ID: +CLIP: "+88017...", 145,...
        m_clip = re.match(r'^\+CLIP:\s*"([^"]+)"(?:,\s*(\d+))?', line)
        if m_clip:
            type_val = int(m_clip.group(2)) if m_clip.group(2) else None
            return IncomingCallEvent(
                raw_line=line,
                caller_id=m_clip.group(1),
                number_type=type_val,
            )

        # 3. Incoming Call Ring: RING
        if re.match(r'^RING\b', line):
            return IncomingCallEvent(raw_line=line)

        # 4. Call Disconnect: NO CARRIER, BUSY
        m_term = re.match(r'^(NO CARRIER|BUSY)\b', line)
        if m_term:
            return CallTerminatedEvent(raw_line=line, reason=m_term.group(1))

        # 5. Network Registration: +CEREG, +CGREG, +CREG
        m_reg = re.match(r'^\+(CEREG|CGREG|CREG):\s*(\d+)(?:,\s*(\d+))?(?:,\s*"([0-9a-fA-F]+)")?(?:,\s*"([0-9a-fA-F]+)")?(?:,\s*(\d+))?', line)
        if m_reg:
            prefix = m_reg.group(1)
            domain = "EPS" if prefix == "CEREG" else ("PS" if prefix == "CGREG" else "CS")
            # Format can be either (<stat>) or (<n>, <stat>)
            if m_reg.group(3) is not None:
                status = int(m_reg.group(3))
                lac = m_reg.group(4)
                ci = m_reg.group(5)
                act = int(m_reg.group(6)) if m_reg.group(6) else None
            else:
                status = int(m_reg.group(2))
                lac = m_reg.group(4)
                ci = m_reg.group(5)
                act = int(m_reg.group(6)) if m_reg.group(6) else None

            return NetworkRegistrationEvent(
                raw_line=line,
                domain=domain,
                status=status,
                lac=lac,
                ci=ci,
                act=act,
            )

        # 6. Qualcomm Mode change: ^MODE: 3, 2
        m_mode = re.match(r'^\^MODE:\s*(\d+)(?:,\s*(\d+))?', line)
        if m_mode:
            subm = int(m_mode.group(2)) if m_mode.group(2) else 0
            return ModeChangeEvent(
                raw_line=line,
                mode=int(m_mode.group(1)),
                submode=subm,
            )

        # 7. Qualcomm Signal strength: ^RSSI: 18
        m_rssi = re.match(r'^\^RSSI:\s*(\d+)', line)
        if m_rssi:
            return SignalChangeEvent(
                raw_line=line,
                rssi=int(m_rssi.group(1)),
            )

        # 8. Generic URC fallback if line starts with '+' or '^'
        if line.startswith(("+", "^")):
            return RawUrcEvent(raw_line=line)

        return None

    def feed_line(self, raw_line: str) -> Optional[UrcEvent]:
        """
        Process a raw incoming line from the modem.
        If it maps to a UrcEvent, dispatches it to all registered subscribers.
        """
        event = self.parse_line(raw_line)
        if not event:
            return None

        self.dispatch(event)
        return event

    def dispatch(self, event: UrcEvent) -> None:
        """
        Dispatch a typed UrcEvent to registered subscribers.
        Subscriber exceptions are caught and logged so listener threads are not halted.
        """
        callbacks_to_invoke: List[Callable[[Any], None]] = []

        with self._lock:
            # Type-specific subscribers
            event_cls = type(event)
            for sub_cls, callbacks in self._subscribers.items():
                if issubclass(event_cls, sub_cls):
                    callbacks_to_invoke.extend(callbacks)

            # Global subscribers
            callbacks_to_invoke.extend(self._global_subscribers)

        for cb in callbacks_to_invoke:
            try:
                cb(event)
            except Exception as exc:
                logger.error("Error in URC subscriber callback %s: %s", cb, exc, exc_info=True)

    def start_listener(
        self,
        transport: SerialTransport,
        shared_lock: Optional[threading.RLock] = None,
        poll_interval: float = 0.05,
    ) -> None:
        """
        Start a background thread listening for idle unsolicited notifications on transport.
        """
        if self._listener_thread is not None and self._listener_thread.is_alive():
            return

        self._stop_event.clear()
        lock = shared_lock or threading.RLock()

        def _reader_loop() -> None:
            while not self._stop_event.is_set():
                # Attempt to acquire lock without blocking indefinitely
                acquired = lock.acquire(blocking=True, timeout=0.1)
                if not acquired:
                    continue

                try:
                    if transport.is_open:
                        line = transport.read_line(timeout=poll_interval)
                        if line:
                            self.feed_line(line)
                except SerialTransportError as exc:
                    logger.debug("SerialTransport read error in URC listener: %s", exc)
                except Exception as exc:
                    logger.error("Unexpected error in URC listener: %s", exc)
                finally:
                    lock.release()

                # Cooperative sleep when idle
                time.sleep(0.01)

        self._listener_thread = threading.Thread(
            target=_reader_loop,
            name="mislty-urc-listener",
            daemon=True,
        )
        self._listener_thread.start()

    def stop_listener(self, timeout: float = 1.0) -> None:
        """Stop background listener thread."""
        self._stop_event.set()
        if self._listener_thread is not None:
            self._listener_thread.join(timeout=timeout)
            self._listener_thread = None
