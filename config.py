import os

# UART Configuration Defaults
PORT = "COM3"
BAUDRATE = 115200

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
