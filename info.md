# RFID UART Communicator Guide
## ACCOLADE ELECTRONICS PVT LTD

---

## Index

- [1. System Architecture & Technical Design](#1-system-architecture--technical-design)
  - [Component Architecture Diagram](#component-architecture-diagram)
  - [Directory & File Responsibilities](#directory--file-responsibilities)
- [2. Complete Implemented Feature Matrix & User Manual](#2-complete-implemented-feature-matrix--user-manual)
  - [Feature 1: UART Communication](#feature-1-uart-communication)
  - [Feature 3: Non-Blocking Threaded Queue Architecture](#feature-3-non-blocking-threaded-queue-architecture)
  - [Feature 4: Protocol Framing & Checksum](#feature-4-protocol-framing--checksum)
  - [Feature 5: Multi-Field Concurrent Request Tracking & Parameter Mapping](#feature-5-multi-field-concurrent-request-tracking--parameter-mapping)
  - [Feature 6: 5.0-Second Hard Timeout Cap & Auto-Cleanup](#feature-6-50-second-hard-timeout-cap--auto-cleanup)
  - [Feature 7: Real-Time Input Validation (Alphanumeric, Hex & Decimal)](#feature-7-real-time-input-validation-alphanumeric-hex--decimal)
  - [Feature 8: Diagnostic Result Cards with Zero-Trailing-Space Formatting](#feature-8-diagnostic-result-cards-with-zero-trailing-space-formatting)
  - [Feature 9: UI Control Locking on Connection](#feature-9-ui-control-locking-on-connection)
  - [Feature 10: Empty and Missing Data Handling](#feature-10-empty-and-missing-data-handling)
  - [Feature 11: Structured Console & JSON Audit Trail Logging](#feature-11-structured-console--json-audit-trail-logging)
- [3. Protocol Specification & Frame Formats](#3-protocol-specification--frame-formats)
  - [Request & Response Frame Structures](#request--response-frame-structures)
  - [Field Specifications Table](#field-specifications-table)
  - [Negative Response Error Codes](#negative-response-error-codes)
- [4. UART Setup](#4-uart-setup)
- [5. Operational, Feature & Technical Q&A](#5-operational-feature--technical-qa)
  - [Q1: Why was a trailing space added to the Diagnostic status hex response when writing VIN, while ASCII showed without space?](#q1-why-was-a-trailing-space-added-to-the-diagnostic-status-hex-response-when-writing-vin-while-ascii-showed-without-space)
  - [Q2: How does the application work in depth (system architecture & data flow)?](#q2-how-does-the-application-work-in-depth-system-architecture--data-flow)
  - [Q8: How does UI Control Locking work when connected vs. disconnected?](#q8-how-does-ui-control-locking-work-when-connected-vs-disconnected)
  - [Q9: What happens when a Write command is fired, data is written on the tag, but the device returns no response?](#q9-what-happens-when-a-write-command-is-fired-data-is-written-on-the-tag-but-the-device-returns-no-response)
  - [Q10: What if a command is stuck in pending requests and never gives a response?](#q10-what-if-a-command-is-stuck-in-pending-requests-and-never-gives-a-response)
  - [Q11: What happens when a Write command gets an immediate response?](#q11-what-happens-when-a-write-command-gets-an-immediate-response)
  - [Q12: What happens if multiple Read/Write buttons are pressed rapidly one after another? How are responses mapped to exact commands?](#q12-what-happens-if-multiple-readwrite-buttons-are-pressed-rapidly-one-after-another-how-are-responses-mapped-to-exact-commands)
  - [Q13: How do I change the serial COM port?](#q13-how-do-i-change-the-serial-com-port)
  - [Q14: What if COM port access is denied or another application is using the port?](#q14-what-if-com-port-access-is-denied-or-another-application-is-using-the-port)
  - [Q15: What happens if I paste a raw Hex frame directly into the log console window?](#q15-what-happens-if-i-paste-a-raw-hex-frame-directly-into-the-log-console-window)
  - [Q16: Why is there no Write button for Tag EPC ID?](#q16-why-is-there-no-write-button-for-tag-epc-id)
  - [Q17: What if an operator types an incomplete or invalid VIN/Serial into the entry box?](#q17-what-if-an-operator-types-an-incomplete-or-invalid-vinserial-into-the-entry-box)
  - [Q19: How do I export transaction logs for quality control or audit reports?](#q19-how-do-i-export-transaction-logs-for-quality-control-or-audit-reports)
  - [Q20: What happens if the USB cable is physically unplugged while connected?](#q20-what-happens-if-the-usb-cable-is-physically-unplugged-while-connected)
  - [Q22: Why does 'Read All' dispatch commands with a 500ms delay instead of all at once?](#q22-why-does-read-all-dispatch-commands-with-a-500ms-delay-instead-of-all-at-once)
  - [Q23: How do I perform a batch 'Read All' operation across multiple tag fields?](#q23-how-do-i-perform-a-batch-read-all-operation-across-multiple-tag-fields)
  - [Q24: How does the application handle duplicate or stale log entries?](#q24-how-does-the-application-handle-duplicate-or-stale-log-entries)
  - [Q25: How do I clear the form fields and reset the reader status?](#q25-how-do-i-clear-the-form-fields-and-reset-the-reader-status)
  - [Q26: What visual indicators confirm that a communication channel is connected and healthy?](#q26-what-visual-indicators-confirm-that-a-communication-channel-is-connected-and-healthy)
  - [Q27: How does Gross Weight (GVW/GCW) decimal validation work?](#q27-how-does-gross-weight-gvwgcw-decimal-validation-work)
  - [Q28: How is decimal Gross Weight encoded into Write frames and decoded from Response frames?](#q28-how-is-decimal-gross-weight-encoded-into-write-frames-and-decoded-from-response-frames)
  - [Q29: What happens if an operator enters a whole integer for Gross Weight (e.g. 45000)?](#q29-what-happens-if-an-operator-enters-a-whole-integer-for-gross-weight-eg-45000)
  - [Q30: What are the numerical bounds for decimal Gross Weight values?](#q30-what-are-the-numerical-bounds-for-decimal-gross-weight-values)

---

## 1. System Architecture & Technical Design

### Component Architecture Diagram

```mermaid
graph TD
    UI[RFIDApp - ui/app.py] --> CommPanel[CommPanelFrame - ui/components/comm_panel.py]
    UI --> TagForm[TagFormFrame - ui/components/tag_form.py]
    UI --> LogPanel[LogPanelFrame - ui/components/log_panel.py]
    
    TagForm --> Protocol[communication/protocol.py]
    Protocol --> CRC[communication/crc.py]
    
    UI --> UART[SerialReader - communication/uart.py]
    
    UART <--> SerialHW[Serial COM Port / Reader ECU]
    UI --> Logger[logger/log_console.py]
```

### Directory & File Responsibilities

| File Path | Description / Responsibility |
| :--- | :--- |
| `main.py` | Application entry point. Instantiates and runs `RFIDApp`. |
| `ui/app.py` | Main orchestrator. Controls GUI event loop, periodic polling (`update_gui`), and frame parsing (`_parse_uart_response`). |
| `communication/base.py` | Abstract `BaseCommunicator` interface for connection, transmission, receive queues, and disconnect notifications. |
| `communication/uart.py` | Threaded, non-blocking UART Serial communication layer wrapping `pyserial`. |
| `communication/protocol.py` | `0x29` SET transmission frame builder, fixed field specifications, decimal scaling, and metadata extraction. |
| `communication/crc.py` | CRC-16/CCITT-FALSE checksum calculator over request frame payloads. |
| `validation/validators.py` | Input field validators for VIN (17 chars), Serial (16 chars), Registration (12 chars), Tag ID (Hex), Axle Count, and GVW Decimal (`validate_gvw_decimal_entry`). |
| `ui/components/comm_panel.py` | Serial port and baud controls, control state locking, and Diagnostic Result Cards (PASS/FAIL/NO RESPONSE). |
| `ui/components/tag_form.py` | Form grid containing Entry boxes, Read/Write buttons, "Read All" sequence runner, and 5-second asynchronous request timeout manager (`pending_requests`). |
| `ui/components/log_panel.py` & `logger/log_console.py` | Rich console log displaying color-coded timestamps, raw TX/RX hex lines, paste-to-send capability, and structured JSON transaction records. |

---

## 2. Complete Implemented Feature Matrix & User Manual

### Feature 1: UART Communication
- **Overview**: Communicates with the RFID reader through a UART serial port.
- **User Instructions**:
  1. Select the serial port connected to the reader.
  2. Select the reader's configured baud rate.
  3. Click **Connect**.

### Feature 3: Non-Blocking Threaded Queue Architecture
- **Overview**: Multi-threaded read (`_read_loop`) and write (`tx_queue`) workers keep the GUI responsive at 60 FPS under heavy bus traffic.
- **User Instructions**: Operating commands are executed in background queues automatically. No manual thread management is required.

### Feature 4: Protocol Framing & Checksum
- **Overview**: Automatically calculates 16-bit **CRC-16/CCITT-FALSE** checksums for all Write SET (`0x29`) transmission frames.
- **User Instructions**: Click **Write** on any parameter; the application handles header packing, length calculation, CRC generation, and trailer framing automatically.

### Feature 5: Multi-Field Concurrent Request Tracking & Parameter Mapping
- **Overview**: Tracks pending requests by unique `param_id` (`0x00` Tag ID, `0x01` Serial, `0x02` VIN, `0x03` Axle, `0x04` Reg, `0x05` GVW, `0x06` TA Cert).
- **User Instructions**: Operators can press multiple Write or Read buttons rapidly; responses map to the correct field without collision.

### Feature 6: 5.0-Second Hard Timeout Cap & Auto-Cleanup
- **Overview**: Enforces a strict 5.0-second lifetime cap per request (`root.after(5000, ...)`).
- **User Instructions**: If a reader device does not respond within 5 seconds, the Diagnostic card displays Red **NO RESPONSE**, and the request is popped from memory.

### Feature 7: Real-Time Input Validation (Alphanumeric, Hex & Decimal)
- **Overview**: Filters entry inputs in real-time to prevent invalid characters.
- **User Instructions**: Type into VIN, Serial, Registration, or GVW Decimal fields; invalid non-decimal or non-alphanumeric characters are filtered out automatically. GVW entry accepts only valid decimal values (e.g. `45000.50`).

### Feature 8: Diagnostic Result Cards with Zero-Trailing-Space Formatting
- **Overview**: Screenshot-style visual card displaying transaction status (**PASS**, **FAIL**, **NO RESPONSE**, **Disconnected**).
- **User Instructions**: Watch the top-right Diagnostic card after any operation for instant visual confirmation.

### Feature 9: UI Control Locking on Connection
- **Overview**: Locks the serial port and baud rate dropdowns when connected to prevent accidental setting changes.
- **User Instructions**: Click **Connect** to lock controls; click **Disconnect** to unlock controls for editing.

### Feature 10: Empty and Missing Data Handling
- Empty and all-zero read values leave the field blank and display a failure instead of being treated as valid data.
- Error `0x07` clears a pending Tag ID and displays **No Tag / Data Unavailable**.

### Feature 11: Structured Console & JSON Audit Trail Logging
- **Overview**: Color-coded console log saving structured JSON records (`name`, `operation`, `command_sent`, `response_received`, `conversion`, `medium`).
- **User Instructions**: View logs directly in the bottom right console or inspect `activity.log` in the application directory.

---

## 3. Protocol Specification & Frame Formats

### Request & Response Frame Structures (`$` to `#`)

#### Read Command Frame (TX):
$$\texttt{24 11 01 <PARAM\_ID> 23}$$

> [!NOTE]
> Read command frames consist of 5 header/body bytes (Header `0x24`, ECU ID `0x11`, Length `0x01`, Parameter ID `0x00`..`0x06`) terminated by `#` (`0x23`). Read frames do **not** use CRC bytes.

#### Write SET Command Frame (TX):
$$\texttt{24 <ECU ID> <LEN> <TRANSMISSION ID> <PARAM\_ID> <PAYLOAD> <RESERVE> <CRC\_H> <CRC\_L> 23}$$

#### Positive Response Frame (RX):
$$\texttt{24 EF <LEN> <TAG\_BYTE> <PAYLOAD> <CRC\_H> <CRC\_L> 23}$$

---

### Field Specifications Table

| Field Name | Parameter ID | Response Tag | Data Type | Max Length | Conversion Type |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **Tag EPC ID** | `0x00` | `0x40` | Hex String | 24 hex chars | `hex as it is` |
| **Serial Reader Number** | `0x01` | `0x41` | Alphanumeric | 16 chars | `alphanumeric` |
| **Trailer VIN** | `0x02` | `0x42` | Alphanumeric | 17 chars | `alphanumeric` |
| **Axle Count** | `0x03` | `0x43` | UInt16 | 2 bytes | `numerical` |
| **Registration Number** | `0x04` | `0x44` | Alphanumeric | 12 chars | `alphanumeric` |
| **Gross Weight (GVW)** | `0x05` | `0x45` | UInt32 (Scaled x100) | 4 bytes | `decimal` |
| **TA Certification** | `0x06` | `0x46` | Hex String | 2 bytes | `hex as it is` |

---

### Negative Response Error Codes (`0x7F`)

When a command fails on hardware, the reader returns `24 EF <LEN> 7F <FAILED_CMD> <ERROR_CODE> <CRC> 23`:

| Error Code | Error Constant | Meaning |
| :---: | :--- | :--- |
| `0x00` | `AEPL_RFID_RESULT_OK` | Request processed successfully. |
| `0x01` | `AEPL_RFID_RESULT_INVALID_PARAMETER` | Invalid or NULL input parameter. |
| `0x02` | `AEPL_RFID_RESULT_INVALID_FRAME` | Invalid or malformed request frame. |
| `0x03` | `AEPL_RFID_RESULT_INVALID_ECU_ID` | Unsupported or incorrect ECU ID. |
| `0x04` | `AEPL_RFID_RESULT_INVALID_LENGTH` | Frame length mismatch. |
| `0x05` | `AEPL_RFID_RESULT_CRC_ERROR` | CRC-16 verification failed. |
| `0x06` | `AEPL_RFID_RESULT_UNSUPPORTED_COMMAND` | Command ID not supported. |
| `0x07` | `AEPL_RFID_RESULT_DATA_UNAVAILABLE` | Requested parameter unavailable. |
| `0x08` | `AEPL_RFID_RESULT_TX_FAILED` | Transmission error. |

---

## 4. UART Setup

Connect the reader to the computer over a serial port, select that port and the baud rate configured on the reader, then click **Connect**. If the port is not listed, reconnect the reader or refresh the available ports.

---

## 5. Operational, Feature & Technical Q&A

### Q1: Why was a trailing space added to the Diagnostic status hex response when writing VIN, while ASCII showed without space?
- **Root Cause**: For fixed-length string fields like VIN (17 chars), the reader payload binary buffer included padding null bytes (`\x00`) or space bytes (`\x20`). While `decoded_val` in the form used `.rstrip("\x00").strip()` to strip ASCII whitespace, `data_bytes.hex(" ").upper()` generated hex for all payload bytes including trailing `20` / space bytes.
- **Solution**: `_parse_uart_response` was updated to perform `clean_payload_bytes = data_bytes.rstrip(b"\x00\x20\r\n ")` for alphanumeric fields before computing `payload_hex_spaced`, and `show_pass(payload_hex)` strips outer whitespace. As a result, both ASCII form text and Diagnostic PASS cards show clean, zero-trailing-space output.

---

### Q2: How does the application work in depth (system architecture & data flow)?
- **Architecture Overview**:
  1. `RFIDApp` manages Tkinter's root window and schedules `update_gui()` every 50ms.
  2. `update_gui()` calls `reader.get_raw_batch()` to retrieve binary chunks from non-blocking queues into `rx_buffer`.
  3. Scans `rx_buffer` for frame start (`$`/`0x24`) and frame end (`#`/`0x23`).
  4. Parses frame length, tag byte (`0x40`..`0x46`), and status in `_parse_uart_response`.
  5. Matches parameter ID against `pending_requests`, pops request tracking, updates Form Entry box, updates Diagnostic PASS/FAIL result card, and appends expandable JSON logs.

---

### Q8: How does UI Control Locking work when connected vs. disconnected?
- **When Connected**: `_set_comm_controls_state(True)` automatically sets **Medium**, **COM Port / Channel**, and **Baud Rate / Bitrate** dropdowns to `state="disabled"`. Connect button is disabled; Disconnect button is enabled.
- **When Disconnected**: `_set_comm_controls_state(False)` restores dropdowns to `state="readonly"`. Connect button is enabled; Disconnect button is disabled.

---

### Q9: What happens when a Write command is fired, data is written on the tag, but the device returns no response?
- `write_field()` registers `pending_requests[param_id]` and starts a 5-second timer.
- If the hardware writes data but fails to send a response frame back, `pending_requests` remains active until 5.0 seconds elapse.
- At the 5.0-second mark, `_handle_request_timeout()` pops `pending_requests[param_id]`, logs `TIMEOUT`, and sets the Diagnostic Status card to Red **NO RESPONSE**.
- If the reader responds with command byte `0x29` (`24 EF <LEN> 29 <FIELD_ID> ...`), `_parse_uart_response` normalizes `0x29` to field ID `0x40+field_id` and marks it **PASS** immediately.

---

### Q10: What if a command is stuck in pending requests and never gives a response?
- **Hard Lifetime Cap**: Every request has a strict 5.0-second maximum lifespan enforced by Tkinter's `root.after(5000, ...)`.
- At 5.0 seconds, `_handle_request_timeout()` pops the request from `pending_requests`. It is impossible for a request to linger in memory indefinitely.
- Clicking **Disconnect** or **Clear Form** calls `clear_pending_requests()`, instantly clearing all pending requests.

---

### Q11: What happens when a Write command gets an immediate response?
1. User clicks **Write** $\rightarrow$ Request registered in `pending_requests[0x02]` and 5-second timer scheduled.
2. Hardware responds 20ms later.
3. `_parse_uart_response()` finds match in `pending_requests[0x02]`, pops `pending_requests[0x02]` immediately, updates Entry field, sets PASS card, and appends JSON log.
4. When 5-second timer fires later, it checks `if 0x02 in pending_requests` (FALSE, already popped) and exits silently without altering the PASS card.

---

### Q12: What happens if multiple Read/Write buttons are pressed rapidly one after another? How are responses mapped to exact commands?
- **Unique Parameter Dictionary Keys**: Each parameter has a distinct ID (`0x00` Tag ID, `0x01` Serial, `0x02` VIN, `0x03` Axle, `0x04` Reg, `0x05` GVW, `0x06` Cert).
- Pressing Write Serial, Write VIN, and Write Registration creates separate entries in `pending_requests[0x01]`, `pending_requests[0x02]`, and `pending_requests[0x04]` simultaneously.
- When response frames return (Tag `0x41`, `0x42`, `0x44`), `_parse_uart_response` looks up the exact matching `param_id` key, retrieves the exact `Command Sent` hex for that specific field, updates the correct entry box, and logs the paired JSON record.
- **FIFO Queueing**: `tx_queue` processes outgoing messages sequentially in First-In, First-Out order.

---

### Q13: How do I change the serial COM port?
1. Click **Disconnect** in the Communication Settings panel.
2. The **COM Port** dropdown unlocks automatically (`state="readonly"`).
3. Select the newly connected COM port (e.g. `COM4`).
4. Click **Connect** to establish communication over the selected port.

---

### Q14: What if COM port access is denied or another application is using the port?
- Serial ports on Windows can only be opened by **one application at a time**.
- If PuTTY, Tera Term, Arduino IDE Serial Monitor, or another utility is open on that COM port, the connection attempt will fail and log `Failed to connect to COMx`.
- Close all other serial monitoring tools and click **Connect** again.

---

### Q15: What happens if I paste a raw Hex frame directly into the log console window?
- Focus the Log Console window and press `Ctrl+V` with any hex string in your clipboard (e.g., `24 11 01 02 C1 B2 23` or `24110102C1B223`).
- `_handle_paste_to_log()` intercepts the event, strips `0x` prefixes and spaces, validates even-length hex bytes, transmits the raw binary payload over UART, and logs `UART TX (hex)` to the console.

---

### Q16: Why is there no Write button for Tag EPC ID?
- Tag EPC ID (`0x00`) is a **factory read-only identifier** stored on the RFID transponder chip memory bank.
- It cannot be modified via standard ECU `SET` commands. Therefore, the Tag ID field row only includes a **Read** button.

---

### Q17: What if an operator types an incomplete or invalid VIN/Serial into the entry box?
- **Real-Time Key Validation**: Form Entry boxes feature real-time key input validators (`validate_vin_entry`, `validate_serial_entry`, etc.) that restrict lowercase letters and special characters as you type.
- **Fixed Padding**: When **Write** is clicked, `build_write_transmission_frame()` automatically pads string values with null bytes (`\x00`) to match the fixed protocol byte length (17 for VIN, 16 for Serial, 12 for Registration).

---

### Q19: How do I export transaction logs for quality control or audit reports?
- Every transaction automatically writes to the log console with expandable JSON objects storing `name`, `operation`, `command_sent`, `response_received`, `conversion`, and `medium`.
- All activity is also logged to `activity.log` in the application directory for automated auditing and file archival.

---

### Q20: What happens if the USB cable is physically unplugged while connected?
- The serial reader catches the I/O exception when the hardware is removed.
- `_handle_disconnect()` executes automatically, closes handles, fires `on_disconnect_callback()`, and safely updates the UI to **Disconnected** (Gray card) while unlocking the dropdown controls.

---

### Q22: Why does 'Read All' dispatch commands with a 500ms delay instead of all at once?
- Microcontrollers and passive RFID transponder chips require a brief RF charge/processing period between consecutive parameter reads.
- Dispatching commands spaced 500ms apart ensures 100% transmission reliability and avoids buffer overflow on the ECU.

---

### Q23: How do I perform a batch 'Read All' operation across multiple tag fields?
- Click the **Read All** button at the bottom of the Tag Data Fields form.
- The application automatically queues and dispatches Read commands for all 7 parameters (`Tag ID`, `Serial Number`, `VIN`, `Axle Count`, `Registration No.`, `GVW`, `TA Certification`) spaced 500ms apart.
- Watch each field Entry box populate and the Diagnostic PASS card update in real-time as each response arrives.

---

### Q24: How does the application handle duplicate or stale log entries?
- Each outgoing request creates a fresh timestamp and JSON transaction entry.
- Late response frames arriving after a 5-second timeout has already expired are identified as late responses (`UART RX Ignored (Late response received after timeout...)`) and logged without overwriting active pending requests or breaking current UI state.

---

### Q25: How do I clear the form fields and reset the reader status?
- Click the **Clear Form** button at the bottom of the form container.
- `clear_fields()` resets all entry values, restores gray placeholder text (`00000000`, `17-digit VIN`, etc.), clears any active pending request timers via `clear_pending_requests()`, and logs `Form cleared`.

---

### Q26: What visual indicators confirm that a communication channel is connected and healthy?
- **Diagnostic Result Card**: Displays a Green status bar, a checkmark/circle icon, and the connected serial port and baud rate.
- **Control Lock**: Port and baud rate dropdowns become grayed out/locked, and the **Connect** button changes to disabled while **Disconnect** becomes active.

---

### Q27: How does Gross Weight (GVW/GCW) decimal validation work?
- **Entry Validation (`validate_gvw_decimal_entry`)**: The GVW Entry box permits typing digits and at most **one decimal point (`.`)**, e.g. `45000.50`, `12500.75`, or `5000.0`.
- **Character Filtering**: Alphabetic letters, special symbols, negative signs, or extra dots are blocked instantly as you type.

---

### Q28: How is decimal Gross Weight encoded into Write frames and decoded from Response frames?
- **Write Transmission**: `build_write_transmission_frame()` parses the float value (e.g. `45000.50`), multiplies by 100 to convert to a 4-byte scaled integer (`4500050` = `0x0044B00A`), and builds the 0x29 SET frame.
- **Read Response Decoding**: `_parse_uart_response()` unpacks the 4-byte Big-Endian payload (`4500050`), divides by 100.0, and formats the output string as `45000.50` in the Form Entry box and Diagnostic PASS card.

---

### Q29: What happens if an operator enters a whole integer for Gross Weight (e.g. 45000)?
- The application parses `45000` as `45000.00` (`4500000` scaled integer byte payload), maintaining consistent 2-decimal-place formatting (`45000.00`) across all Read and Write transactions.

---

### Q30: What are the numerical bounds for decimal Gross Weight values?
- Supports decimal weights up to **4,29,49,67,295 kg** (representing the maximum 32-bit unsigned integer `4294967295` when scaled by 100).

---

## 6. Summary & Status

The RFID Communicator application supports serial UART communication with the RFID reader.
