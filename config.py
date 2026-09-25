import os

# UART Configuration Defaults
PORT = "COM3"
BAUDRATE = 115200

# CAN Bus Configuration & Hardware Settings
# Supported CAN Interfaces:
# - "pcan": PEAK-System PCAN-USB (Channel: PCAN_USBBUS1, PCAN_USBBUS2) [Recommended for Windows]
# - "slcan": USB-to-CAN Adapters / CANable with SLCAN firmware (Channel: COM port e.g. COM3, COM4)
# - "kvaser": Kvaser Leaf Light / USB CAN (Channel: 0, 1)
# - "vector": Vector VN1610 / VN1630 (Channel: 0, 1)
# - "socketcan": Linux Native CAN / MCP2515 (Channel: can0, vcan0)
# - "virtual": Virtual Loopback Simulator for testing without physical hardware (Channel: 0)

CAN_CHANNEL = "PCAN_USBBUS1"  # e.g. PCAN_USBBUS1, can0, vcan0, SLCAN, COM3
CAN_BUS_TYPE = "pcan"         # e.g. pcan, socketcan, slcan, kvaser, vector, virtual
CAN_BITRATE = 250000          # Standard bitrates: 125000, 250000, 500000, 1000000
CAN_DEFAULT_TX_ID = 0x7E0     # Default Transmit CAN ID (11-bit or 29-bit)
CAN_DEFAULT_RX_ID = 0x7E8     # Default Receive CAN ID (11-bit or 29-bit)
CAN_IS_EXTENDED_ID = False    # True for 29-bit extended CAN ID, False for 11-bit standard ID

# Dynamic CAN ID Mapping per Parameter ID (0x00 Tag ID, 0x01 Serial, 0x02 VIN, 0x03 Axle, 0x04 Reg, 0x05 GVW, 0x06 Cert)
# Format: { param_id: { "tx_id": int, "rx_id": int, "is_extended": bool } }
# When empty or unspecified, CAN_DEFAULT_TX_ID and CAN_DEFAULT_RX_ID are used automatically.
CAN_ID_MAP = {}

LOG_DEFAULT_PATH = os.path.join(os.getcwd(), "activity.log")

# Negative Response Error Codes (VLTD Protocol Spec)
ERROR_CODES = {
    0x00: "AEPL_RFID_RESULT_OK: Request processed successfully.",
    0x01: "AEPL_RFID_RESULT_INVALID_PARAMETER: Invalid or NULL input parameter.",
    0x02: "AEPL_RFID_RESULT_INVALID_FRAME: Invalid or malformed request frame.",
    0x03: "AEPL_RFID_RESULT_INVALID_ECU_ID: Unsupported or incorrect ECU ID.",
    0x04: "AEPL_RFID_RESULT_INVALID_LENGTH: Frame length does not match expected value.",
    0x05: "AEPL_RFID_RESULT_CRC_ERROR: CRC verification failed.",
    0x06: "AEPL_RFID_RESULT_UNSUPPORTED_COMMAND: Requested Command ID is not supported.",
    0x07: "No Tag / Data Unavailable",
    0x08: "AEPL_RFID_RESULT_TX_FAILED: Failed to transmit response frame.",
}
