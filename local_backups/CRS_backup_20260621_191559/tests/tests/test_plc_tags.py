from database.plc_tag_manager import (
    PLCTagManager
)


def main():

    machine_id = 1
    stage_id = 1

    test_tags = [

        (
            "CRS_Recipe_Code",
            "RECIPE_CODE"
        ),

        (
            "CRS_Recipe_Data",
            "RECIPE_DATA"
        ),

        (
            "CRS_Download_Request",
            "DOWNLOAD_REQUEST"
        ),

        (
            "CRS_Download_Ack",
            "DOWNLOAD_ACK"
        ),

        (
            "CRS_Download_Complete",
            "DOWNLOAD_COMPLETE"
        ),

        (
            "CRS_Download_Result",
            "DOWNLOAD_RESULT"
        ),

        (
            "CRS_Download_Enable",
            "DOWNLOAD_ENABLE"
        ),

        (
            "CRS_Last_Download_User",
            "LAST_DOWNLOAD_USER"
        ),

        (
            "CRS_Last_Download_Time",
            "LAST_DOWNLOAD_TIME"
        ),

        (
            "CRS_Machine_Manual",
            "MACHINE_MANUAL"
        ),

        (
            "CRS_Running_Recipe_Code",
            "RUNNING_RECIPE"
        )

    ]

    for tag_name, tag_type in test_tags:

        try:

            PLCTagManager.create_tag(

                machine_id=machine_id,

                stage_id=stage_id,

                tag_name=tag_name,

                tag_type=tag_type,

                description=tag_type,

                created_by="system"

            )

            print(
                f"Created : {tag_type}"
            )

        except Exception as ex:

            print(
                f"Skipped : {tag_type}"
            )

    print()

    print(
        "Testing Tag Lookup"
    )

    print()

    tag = (
        PLCTagManager.get_tag_by_type(

            machine_id,

            stage_id,

            "RECIPE_DATA"

        )
    )

    print(
        tag
    )


if __name__ == "__main__":

    main()