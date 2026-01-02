# Constants for Optimizer Agent

# Agent configuration
AGENT_NAME = "opt"

# Optimization parameters
SAFETY_MARGIN = 1.2

# Database configuration
DEFAULT_WORKING_WINDOW = 1024
PRAGMA_JOURNAL_MODE = "PRAGMA journal_mode=WAL"
PRAGMA_SYNCHRONOUS = "PRAGMA synchronous=NORMAL"
PRAGMA_CACHE_SIZE = "PRAGMA cache_size=-64000"

# SimHash configuration
HASHBITS = 64
HASH_BYTES = 16
HASH_SLICE = 16  # Same as HASH_BYTES for slicing MD5 digest
MAX_TOKENS = 1024
TOKEN_REGEX = r"\b\w+\b"
SHINGLE_SIZE = 3
THRESHOLD_DIVISOR = 16  # For default threshold calculation
DEFAULT_RESOLUTIONS = [64, 128, 256, 512, 1024]
DEFAULT_THRESHOLDS = {
    64: 3,  # ~5% of 64 bits
    128: 4,  # ~3% of 128 bits
    256: 6,  # ~2% of 256 bits
    512: 8,  # ~1.5% of 512 bits
    1024: 12,  # ~1% of 1024 bits
}
