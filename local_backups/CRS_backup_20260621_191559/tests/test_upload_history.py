from database.upload_history_manager import (
    UploadHistoryManager
)

history = (

    UploadHistoryManager
    .get_history()

)

for row in history:

    print(
        dict(row)
    )