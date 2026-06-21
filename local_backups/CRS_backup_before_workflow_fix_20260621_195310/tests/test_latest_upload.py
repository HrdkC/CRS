from database.upload_history_manager import (
    UploadHistoryManager
)

row = (

    UploadHistoryManager
    .get_latest_upload(

        "P15KM"

    )

)

print(
    dict(row)
)