"""Abstract Base Class for hardware communicators (UART Serial, CAN Bus, etc.)."""

from abc import ABC, abstractmethod


class BaseCommunicator(ABC):
    """Abstract interface defining standard hardware communication operations."""

    @abstractmethod
    def connect(self, port_or_channel: str = None, baud_or_bitrate: int = None) -> bool:
        """Establish connection to hardware interface."""
        pass

    @abstractmethod
    def disconnect(self):
        """Close hardware interface connection."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check whether the hardware interface is actively connected."""
        pass

    @abstractmethod
    def write_bytes(self, data: bytes) -> bool:
        """Queue raw bytes for transmission."""
        pass

    @abstractmethod
    def get_raw_batch(self, max_items: int = 50) -> list[bytes]:
        """Fetch batch of received raw binary payloads."""
        pass

    @abstractmethod
    def set_disconnect_callback(self, callback):
        """Set callback to notify UI thread when connection drops asynchronously."""
        pass
