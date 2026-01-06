from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class Template:
    """Domain entity representing a prompt template."""

    id: int
    template_hash: str
    working_window: int
    observation_count: int = 0
    avg_distance: float = 0.0
    optimal_batch_size: Optional[int] = None
    fingerprint_64: Optional[str] = None
    fingerprint_128: Optional[str] = None
    fingerprint_256: Optional[str] = None
    fingerprint_512: Optional[str] = None
    fingerprint_1024: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def fingerprints(self) -> Dict[int, int]:
        """Get fingerprints as dict of resolution -> int value.

        Returns:
            Dictionary mapping resolution (64, 128, 256, 512, 1024) to integer fingerprint values.
            Only includes fingerprints that are not None.
        """
        fps: Dict[int, int] = {}
        if self.fingerprint_64 is not None:
            fps[64] = int(self.fingerprint_64, 16)
        if self.fingerprint_128 is not None:
            fps[128] = int(self.fingerprint_128, 16)
        if self.fingerprint_256 is not None:
            fps[256] = int(self.fingerprint_256, 16)
        if self.fingerprint_512 is not None:
            fps[512] = int(self.fingerprint_512, 16)
        if self.fingerprint_1024 is not None:
            fps[1024] = int(self.fingerprint_1024, 16)
        return fps

    @staticmethod
    def _hex_to_int(hex_str: Optional[str]) -> Optional[int]:
        """Convert a hex string to an integer.

        Args:
            hex_str: Hex string representation (e.g., "abc123")

        Returns:
            Integer value or None if input is None
        """
        if hex_str is None:
            return None
        return int(hex_str, 16)

    @staticmethod
    def int_to_hex(value: int) -> str:
        """Convert an integer to a hex string.

        Args:
            value: Integer value to convert

        Returns:
            Hex string representation without '0x' prefix
        """
        return hex(value)[2:]

    def get_fingerprint_at_resolution(self, resolution: int) -> Optional[int]:
        """Get fingerprint value at a specific resolution.

        Args:
            resolution: The resolution to get fingerprint for (64, 128, 256, 512, 1024)

        Returns:
            Integer fingerprint value or None if not available
        """
        if resolution == 64:
            return self._hex_to_int(self.fingerprint_64)
        elif resolution == 128:
            return self._hex_to_int(self.fingerprint_128)
        elif resolution == 256:
            return self._hex_to_int(self.fingerprint_256)
        elif resolution == 512:
            return self._hex_to_int(self.fingerprint_512)
        elif resolution == 1024:
            return self._hex_to_int(self.fingerprint_1024)
        return None

    def set_fingerprint_at_resolution(self, resolution: int, value: int) -> None:
        """Set fingerprint value at a specific resolution.

        Args:
            resolution: The resolution to set fingerprint for (64, 128, 256, 512, 1024)
            value: Integer fingerprint value to store
        """
        hex_value = self.int_to_hex(value)
        if resolution == 64:
            self.fingerprint_64 = hex_value
        elif resolution == 128:
            self.fingerprint_128 = hex_value
        elif resolution == 256:
            self.fingerprint_256 = hex_value
        elif resolution == 512:
            self.fingerprint_512 = hex_value
        elif resolution == 1024:
            self.fingerprint_1024 = hex_value

    def to_dict(self) -> Dict:
        """Convert the Template to a dictionary.

        Returns:
            Dictionary representation of the Template
        """
        return {
            "id": self.id,
            "template_hash": self.template_hash,
            "working_window": self.working_window,
            "observation_count": self.observation_count,
            "avg_distance": self.avg_distance,
            "optimal_batch_size": self.optimal_batch_size,
            "fingerprint_64": self.fingerprint_64,
            "fingerprint_128": self.fingerprint_128,
            "fingerprint_256": self.fingerprint_256,
            "fingerprint_512": self.fingerprint_512,
            "fingerprint_1024": self.fingerprint_1024,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Template":
        """Create a Template from a dictionary.

        Args:
            data: Dictionary containing Template data

        Returns:
            Template instance
        """
        return cls(
            id=data.get("id", 0),
            template_hash=data.get("template_hash", ""),
            working_window=data.get("working_window", 0),
            observation_count=data.get("observation_count", 0),
            avg_distance=data.get("avg_distance", 0.0),
            optimal_batch_size=data.get("optimal_batch_size"),
            fingerprint_64=data.get("fingerprint_64"),
            fingerprint_128=data.get("fingerprint_128"),
            fingerprint_256=data.get("fingerprint_256"),
            fingerprint_512=data.get("fingerprint_512"),
            fingerprint_1024=data.get("fingerprint_1024"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
