# P15 CRS Test PLC Tags

Use these tags for both P15 FS PLC and P15 SS PLC. FS and SS are separate controllers, so the same controller-scope tag names are acceptable in both PLCs.

Important: pycomm3/CRS can read and write existing tags, but it cannot create new controller tags inside Studio 5000. Create/import these tags in Logix Designer first.

## Required test flow

1. Add/import the tags in Studio 5000 on the target controller.
2. Download or accept online edits as per your plant procedure.
3. Run `python scripts/register_p15_crs_test_tags.py --stage SS` to register the same tag purposes in CRS DB.
4. Run `python scripts/verify_p15_crs_test_tags_online.py --stage SS` to confirm CRS can read the tags online.
5. Open `/plc-tags/P15/SS?online_search=1&search=CRS_&array_only=0&bool_only=0` and confirm CRS tags are visible.

## Tag list

| Purpose | Tag | Type | Array | Description |
|---|---|---:|---:|---|
| RECIPE_DATA | `CRS_Recipe_Data` | REAL | 150 | CRS source recipe buffer. CRS writes/restores selected DB recipe here before PLC download. |
| TEST_RECIPE_DATA | `CRS_Test_Recipe_Data` | REAL | 150 | PLC destination/source test recipe buffer. Download writes here; Upload reads here. |
| RECIPE_CODE | `CRS_Recipe_Code` | STRING |  | Selected CRS recipe code for operator/PLC visibility. |
| DOWNLOAD_ENABLE | `CRS_Download_Enable` | BOOL |  | PLC/maintenance permissive. Must be TRUE before CRS Download To PLC. |
| MACHINE_IN_MANUAL | `CRS_Test_Machine_In_Manual` | BOOL |  | Temporary CRS manual-mode permissive for test only. Set TRUE only in safe manual/test condition. |
| DOWNLOAD_REQUEST | `CRS_Download_Request` | BOOL |  | CRS sets this TRUE during Download To PLC handshake. |
| DOWNLOAD_COMPLETE | `CRS_Download_Complete` | BOOL |  | PLC/test handshake complete bit. CRS waits for this during Download To PLC. |
| DOWNLOAD_ACK | `CRS_Download_Ack` | BOOL |  | Optional CRS acknowledgement bit after download handshake. |
| DOWNLOAD_BUSY | `CRS_Download_Busy` | BOOL |  | Optional PLC/test busy bit for download handshake diagnostics. |
| DOWNLOAD_ERROR | `CRS_Download_Error` | BOOL |  | Optional PLC/test error bit for download handshake diagnostics. |
| DOWNLOAD_RESULT | `CRS_Download_Result` | DINT |  | Optional numeric result code. 1 can be used for test success. |
| DOWNLOAD_OS | `CRS_Download_OS` | BOOL |  | Optional one-shot/storage bit if PLC ladder is added later. |
| LAST_DOWNLOAD_TIME | `CRS_Last_Download_Time` | STRING |  | Optional last download timestamp string written by CRS/PLC test logic. |
| LAST_DOWNLOAD_USER | `CRS_Last_Download_User` | STRING |  | Optional last download username string written by CRS/PLC test logic. |
| TEST_RECIPE_NO | `CRS_Test_Recipe_No` | DINT |  | Optional simple test recipe number tag, matching existing P15 FS test setup. |
| TEST_LENGTH | `CRS_Test_Length` | REAL |  | Optional simple test length tag, matching existing P15 FS test setup. |
| TEST_WIDTH | `CRS_Test_Width` | REAL |  | Optional simple test width tag, matching existing P15 FS test setup. |
| TEST_SPEED | `CRS_Test_Speed` | REAL |  | Optional simple test speed tag, matching existing P15 FS test setup. |
