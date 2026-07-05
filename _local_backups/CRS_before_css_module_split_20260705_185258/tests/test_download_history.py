from database.download_history_manager import (
    DownloadHistoryManager
)

download_id = (
    DownloadHistoryManager
    .create_download_record(

        plc_name="P15KM",

        recipe_code="GT7107",

        recipe_version=1,

        downloaded_by="admin"

    )
)

print(
    "Download ID:",
    download_id
)

DownloadHistoryManager.complete_download_record(

    download_id,

    "Test Success"
)

history = (
    DownloadHistoryManager
    .get_history()
)

for row in history:

    print(
        dict(row)
    )