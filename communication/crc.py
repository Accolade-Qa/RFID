def aepl_rfid_calculate_crc16(data: bytes, length: int) -> int:
    """
    Calculate CRC-16/CCITT-FALSE.

    CRC is calculated from data[1] through data[length - 1].

    Example:
        data = 24 11 04 29 03 00 0A

        CRC input:
            11 04 29 03 00 0A
    """

    crc = 0xFFFF

    for byte in range(1, length):
        crc ^= data[byte] << 8

        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF

    return crc & 0xFFFF

def crc_to_bytes(crc: int, big_endian: bool = True) -> bytes:
    """Serialise a 16-bit CRC integer to 2 bytes."""
    return crc.to_bytes(2, "big" if big_endian else "little")
