"""Protocol frame construction and CRC calculation for RFID reader communication."""

from communication.crc import aepl_rfid_calculate_crc16, crc_to_bytes

HEADER = 0x24       # '$'
TRAILER = 0x23      # '#'
ECU_ID_VLDT = 0x11  # Sender ID for VLDT requests
SET_CMD_ID = 0x29   # Transmission ID for Write SET commands

FIELD_SPECS = {
    "serial": {
        "field_id": 0x01,
        "dtype": "string",
        "data_len": 16,
        "reserve_len": 0,
        "conversion": "alphanumeric",
        "name": "Serial Reader Number",
    },
    "vin": {
        "field_id": 0x02,
        "dtype": "string",
        "data_len": 17,
        "reserve_len": 0,
        "conversion": "alphanumeric",
        "name": "Trailer VIN",
    },
    "axle": {
        "field_id": 0x03,
        "dtype": "uint",
        "data_len": 2,
        "reserve_len": 0,
        "conversion": "numerical",
        "name": "Axle Count",
    },
    "registration": {
        "field_id": 0x04,
        "dtype": "string",
        "data_len": 12,
        "reserve_len": 0,
        "conversion": "alphanumeric",
        "name": "Registration Number",
    },
    "gvw": {
        "field_id": 0x05,
        "dtype": "uint",
        "data_len": 4,
        "reserve_len": 0,
        "conversion": "decimal",
        "name": "Trailer Gross Weight",
    },
    "cert": {
        "field_id": 0x06,
        "dtype": "hex",
        "data_len": 2,
        "reserve_len": 0,
        "conversion": "hex as it is",
        "name": "Meta Data",
    },
}


def build_write_transmission_frame(field_name: str, input_value: str) -> tuple[bytes, str, dict]:
    """
    Build a complete 0x29 SET Transmission Frame with CRC-16/CCITT-FALSE calculation.
    
    Frame structure:
    24 11 <LEN> 29 <FIELD_ID> <DATA_BYTES> <RESERVE_BYTES> <CRC_H> <CRC_L> 23
    """
    if field_name not in FIELD_SPECS:
        raise ValueError(f"Unknown field name: {field_name}")

    spec = FIELD_SPECS[field_name]
    field_id = spec["field_id"]
    dtype = spec["dtype"]
    data_len = spec["data_len"]
    reserve_len = spec.get("reserve_len", 0)

    # Encode payload bytes
    clean_val = input_value.strip()
    if dtype == "string":
        raw = clean_val.encode("ascii", errors="ignore")
        if len(raw) > data_len:
            raw = raw[:data_len]
        payload = raw.ljust(data_len, b" ")
    elif dtype in ("uint", "decimal"):
        try:
            val_float = float(clean_val)
            val_int = int(round(val_float))
        except ValueError:
            val_int = 0
        payload = val_int.to_bytes(data_len, "big")
    elif dtype == "hex":
        compact = clean_val.replace(" ", "")
        try:
            payload = bytes.fromhex(compact)
        except ValueError:
            payload = b"\x00" * data_len
        if len(payload) < data_len:
            payload = payload.ljust(data_len, b"\x00")
        elif len(payload) > data_len:
            payload = payload[:data_len]
    else:
        payload = b"\x00" * data_len

    # Add reserve bytes if required (e.g. Serial Reader Number 0x01)
    if reserve_len > 0:
        payload += b"\x00" * reserve_len

    # Body: 0x29 + Field_ID + Payload
    body = bytes([SET_CMD_ID, field_id]) + payload
    length = len(body)

    # Compute CRC-16/CCITT-FALSE over body
    # crc_val = compute_crc16_ccitt_false(body)
    crc_val = aepl_rfid_calculate_crc16(body, length)
    crc_bytes = crc_to_bytes(crc_val, big_endian=True)

    # Complete frame
    frame = bytes([HEADER, ECU_ID_VLDT, length]) + body + crc_bytes + bytes([TRAILER])
    frame_hex_spaced = frame.hex(" ").upper()

    metadata = {
        "Name": spec["name"],
        "Operation": "Write",
        "Conversion": spec["conversion"],
        "Command Sent": frame_hex_spaced,
        "Field_ID": f"0x{field_id:02X}",
        "CRC": f"0x{crc_val:04X}",
    }

    return frame, frame_hex_spaced, metadata
