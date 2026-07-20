"""Standard CRS PLC test tag definitions.

These definitions are used by CRS support scripts to register/verify the
standard controller-scope test tags used for recipe buffer trials.

Important: these scripts do not create tags inside Studio 5000 by themselves.
Create/import the PLC tags in Logix Designer first, then register/verify them in
CRS with the scripts in the scripts folder.
"""

FIRST_STAGE_PAYLOAD_SIZE = 500
SECOND_STAGE_PAYLOAD_SIZE = 150
PAYLOAD_SIZE = SECOND_STAGE_PAYLOAD_SIZE  # deprecated compatibility alias

CRS_STANDARD_TEST_TAGS = [
    {
        "purpose": "RECIPE_DATA",
        "tag_name": "CRS_Recipe_Data",
        "tag_type": "REAL",
        "is_array": 1,
        "array_size": PAYLOAD_SIZE,
        "array_start_index": 0,
        "array_end_index": PAYLOAD_SIZE - 1,
        "initial_value": "REAL[150] all 0.0",
        "description": "CRS source recipe buffer. CRS writes/restores selected DB recipe here before PLC download.",
    },
    {
        "purpose": "TEST_RECIPE_DATA",
        "tag_name": "CRS_Test_Recipe_Data",
        "tag_type": "REAL",
        "is_array": 1,
        "array_size": PAYLOAD_SIZE,
        "array_start_index": 0,
        "array_end_index": PAYLOAD_SIZE - 1,
        "initial_value": "REAL[150] all 0.0",
        "description": "PLC destination/source test recipe buffer. Download writes here; Upload reads here.",
    },
    {
        "purpose": "RECIPE_CODE",
        "tag_name": "CRS_Recipe_Code",
        "tag_type": "STRING",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "blank string",
        "description": "Selected CRS recipe code for operator/PLC visibility.",
    },
    {
        "purpose": "DOWNLOAD_ENABLE",
        "tag_name": "CRS_Download_Enable",
        "tag_type": "BOOL",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "0 / FALSE",
        "description": "PLC/maintenance permissive. Must be TRUE before CRS Download To PLC.",
    },
    {
        "purpose": "MACHINE_IN_MANUAL",
        "tag_name": "CRS_Test_Machine_In_Manual",
        "tag_type": "BOOL",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "0 / FALSE",
        "description": "Temporary CRS manual-mode permissive for test only. Set TRUE only in safe manual/test condition.",
    },
    {
        "purpose": "DOWNLOAD_REQUEST",
        "tag_name": "CRS_Download_Request",
        "tag_type": "BOOL",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "0 / FALSE",
        "description": "CRS sets this TRUE during Download To PLC handshake.",
    },
    {
        "purpose": "DOWNLOAD_COMPLETE",
        "tag_name": "CRS_Download_Complete",
        "tag_type": "BOOL",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "0 / FALSE",
        "description": "PLC/test handshake complete bit. CRS waits for this during Download To PLC.",
    },
    {
        "purpose": "DOWNLOAD_ACK",
        "tag_name": "CRS_Download_Ack",
        "tag_type": "BOOL",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "0 / FALSE",
        "description": "Optional CRS acknowledgement bit after download handshake.",
    },
    {
        "purpose": "DOWNLOAD_BUSY",
        "tag_name": "CRS_Download_Busy",
        "tag_type": "BOOL",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "0 / FALSE",
        "description": "Optional PLC/test busy bit for download handshake diagnostics.",
    },
    {
        "purpose": "DOWNLOAD_ERROR",
        "tag_name": "CRS_Download_Error",
        "tag_type": "BOOL",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "0 / FALSE",
        "description": "Optional PLC/test error bit for download handshake diagnostics.",
    },
    {
        "purpose": "DOWNLOAD_RESULT",
        "tag_name": "CRS_Download_Result",
        "tag_type": "DINT",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "0",
        "description": "Optional numeric result code. 1 can be used for test success.",
    },
    {
        "purpose": "DOWNLOAD_OS",
        "tag_name": "CRS_Download_OS",
        "tag_type": "BOOL",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "0 / FALSE",
        "description": "Optional one-shot/storage bit if PLC ladder is added later.",
    },
    {
        "purpose": "LAST_DOWNLOAD_TIME",
        "tag_name": "CRS_Last_Download_Time",
        "tag_type": "STRING",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "blank string",
        "description": "Optional last download timestamp string written by CRS/PLC test logic.",
    },
    {
        "purpose": "LAST_DOWNLOAD_USER",
        "tag_name": "CRS_Last_Download_User",
        "tag_type": "STRING",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "blank string",
        "description": "Optional last download username string written by CRS/PLC test logic.",
    },
    {
        "purpose": "TEST_RECIPE_NO",
        "tag_name": "CRS_Test_Recipe_No",
        "tag_type": "DINT",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "0",
        "description": "Optional simple test recipe number tag, matching existing P15 FS test setup.",
    },
    {
        "purpose": "TEST_LENGTH",
        "tag_name": "CRS_Test_Length",
        "tag_type": "REAL",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "0.0",
        "description": "Optional simple test length tag, matching existing P15 FS test setup.",
    },
    {
        "purpose": "TEST_WIDTH",
        "tag_name": "CRS_Test_Width",
        "tag_type": "REAL",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "0.0",
        "description": "Optional simple test width tag, matching existing P15 FS test setup.",
    },
    {
        "purpose": "TEST_SPEED",
        "tag_name": "CRS_Test_Speed",
        "tag_type": "REAL",
        "is_array": 0,
        "array_size": None,
        "array_start_index": None,
        "array_end_index": None,
        "initial_value": "0.0",
        "description": "Optional simple test speed tag, matching existing P15 FS test setup.",
    },
]

REQUIRED_FOR_BUFFER_OPERATIONS = [
    "RECIPE_DATA",
    "TEST_RECIPE_DATA",
    "RECIPE_CODE",
    "DOWNLOAD_ENABLE",
    "MACHINE_IN_MANUAL",
    "DOWNLOAD_REQUEST",
    "DOWNLOAD_COMPLETE",
]

OPTIONAL_HANDSHAKE_TAGS = [
    "DOWNLOAD_ACK",
    "DOWNLOAD_BUSY",
    "DOWNLOAD_ERROR",
    "DOWNLOAD_RESULT",
    "DOWNLOAD_OS",
    "LAST_DOWNLOAD_TIME",
    "LAST_DOWNLOAD_USER",
]


def payload_size_for_stage(stage_type):
    stage = str(stage_type or "").strip().upper().replace(" ", "_")
    if stage in {"FIRST_STAGE", "FIRSTSTAGE", "FS"}:
        return FIRST_STAGE_PAYLOAD_SIZE
    if stage in {"SECOND_STAGE", "SECONDSTAGE", "SS"}:
        return SECOND_STAGE_PAYLOAD_SIZE
    raise ValueError("Stage type must be FIRST_STAGE/FS or SECOND_STAGE/SS.")


def get_tag_definitions(include_optional=True, stage_type="SECOND_STAGE"):
    payload_size = payload_size_for_stage(stage_type)
    source = CRS_STANDARD_TEST_TAGS
    if not include_optional:
        required = set(REQUIRED_FOR_BUFFER_OPERATIONS)
        source = [tag for tag in source if tag["purpose"] in required]

    definitions = []
    for original in source:
        tag = dict(original)
        if tag["purpose"] in {"RECIPE_DATA", "TEST_RECIPE_DATA"}:
            tag["array_size"] = payload_size
            tag["array_start_index"] = 0
            tag["array_end_index"] = payload_size - 1
            tag["initial_value"] = f"REAL[{payload_size}] all 0.0"
        definitions.append(tag)
    return definitions
