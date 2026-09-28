"""CRC-16/CCITT-FALSE implementation (poly=0x1021, init=0xFFFF)."""

def aepl_rfid_calculate_crc16(data: bytes, length: int) -> int:
    '''
        #define AEPL_RFID_CRC_INITIAL_VALUE             (0xFFFFU)
        #define AEPL_RFID_CRC_POLYNOMIAL                (0x1021U)
        #define AEPL_RFID_CRC_MSB_MASK                  (0x8000U)
        #define AEPL_RFID_CRC_START_INDEX                0U
    '''

    CRC_INITIAL_VALUE = 0xFFFF  
    CRC_START_INDEX = 0
    CRC_MSB_MASK = 0x8000
    CRC_POLYNOMIAL = 0x1021


    crc = CRC_INITIAL_VALUE

    if data is not None:
        for byte_index in range(CRC_START_INDEX, length):

            crc ^= (data[byte_index] << 8)

            for _ in range(8):
                if crc & CRC_MSB_MASK:
                    crc = (crc << 1) ^ CRC_POLYNOMIAL
                else:
                    crc = crc << 1

                # Simulate uint16_t
                crc &= 0xFFFF

    return crc


def crc_to_bytes(crc: int, big_endian: bool = True) -> bytes:
    """Serialise a 16-bit CRC integer to 2 bytes."""
    return crc.to_bytes(2, "big" if big_endian else "little")
