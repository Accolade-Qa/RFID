"""EZCAD laser controller error definitions and exceptions."""

EZCAD_ERROR_MESSAGES = {
    0: "Success (LMC1_ERR_SUCCESS)",
    1: "EZCAD software is already running. Please close it first. (LMC1_ERR_EZCADRUN)",
    2: "EZCAD.CFG configuration file not found. (LMC1_ERR_NOFINDCFGFILE)",
    3: "Failed to open LMC1 control board. (LMC1_ERR_FAILEDOPEN)",
    4: "No valid LMC1 device detected / USB disconnected. (LMC1_ERR_NODEVICE)",
    5: "LMC1 hardware version mismatch or error. (LMC1_ERR_HARDVER)",
    6: "Device configuration error. (LMC1_ERR_DEVCFG)",
    7: "Stop or alarm signal active. (LMC1_ERR_STOPSIGNAL)",
    8: "User aborted operation. (LMC1_ERR_USERSTOP)",
    9: "Marking error: fiber laser controller unsupported or error. (LMC1_ERR_UNKNOW)",
    10: "Communication timeout with laser controller. (LMC1_ERR_OUTTIME)",
    11: "Laser controller not initialized. (LMC1_ERR_NOINITIAL)",
    12: "Failed to read or parse EZD template file. (LMC1_ERR_READFILE)",
    13: "Owner window handle is null or controller absent. (LMC1_ERR_OWENWNDNULL)",
    14: "Specified font not found in system or EzCAD. (LMC1_ERR_NOFINDENT)",
    15: "Invalid laser pen number. (LMC1_ERR_PENNO)",
    16: "Target object is not a text entity. (LMC1_ERR_NOTEXT)",
    17: "Failed to save file. (LMC1_ERR_SAVEFILE)",
    18: "Object with specified name not found in template. (LMC1_ERR_NOFINDENT)",
    19: "Operation not allowed in current state. (LMC1_ERR_STATUE)",
}


class EZCADError(Exception):
    """Exception raised for EZCAD controller or DLL errors."""

    def __init__(self, code: int, operation: str = "", details: str = ""):
        self.code = code
        self.operation = operation
        msg = EZCAD_ERROR_MESSAGES.get(code, f"Unknown error code {code}")
        full_msg = f"{operation} failed [Error {code}]: {msg}"
        if details:
            full_msg += f" ({details})"
        super().__init__(full_msg)
