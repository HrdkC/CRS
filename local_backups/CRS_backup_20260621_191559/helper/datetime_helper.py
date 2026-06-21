from datetime import datetime, timedelta


def utc_to_ist(timestamp_string):

    if not timestamp_string:

        return None

    try:

        utc_time = datetime.strptime(

            timestamp_string,

            "%Y-%m-%d %H:%M:%S"

        )

        return (

            utc_time +

            timedelta(
                hours=5,
                minutes=30
            )

        ).strftime(

            "%Y-%m-%d %H:%M:%S"

        )

    except Exception:

        return timestamp_string