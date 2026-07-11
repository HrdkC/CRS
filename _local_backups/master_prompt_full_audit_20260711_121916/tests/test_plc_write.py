from pycomm3 import (
    LogixDriver
)

PLC_IP = "172.20.56.169"


def build_test_array():

    data = []

    for i in range(500):

        data.append(
            float(i)
        )

    return data


def main():

    print(
        "Connecting..."
    )

    with LogixDriver(
        PLC_IP
    ) as plc:

        print(
            "Connected"
        )

        recipe_code = (
            "GT_TEST_001"
        )

        recipe_data = (
            build_test_array()
        )

        print(
            "Writing Recipe Code..."
        )

        result = plc.write(

            (
                "CRS_Recipe_Code",
                recipe_code
            )

        )

        print(
            result
        )

        print(
            "Writing Recipe Array..."
        )

        result = plc.write(

            (
                "CRS_Recipe_Data{500}",
                recipe_data
            )

        )

        print(
            result
        )

        print(
            "Reading Back..."
        )

        code = plc.read(
            "CRS_Recipe_Code"
        )

        first_value = plc.read(
            "CRS_Recipe_Data[0]"
        )

        last_value = plc.read(
            "CRS_Recipe_Data[499]"
        )

        first_ten = plc.read(
            "CRS_Recipe_Data{10}"
        )

        print(
            "Recipe Code:",
            code.value
        )

        print(
            "First Value:",
            first_value.value
        )

        print(
            "Last Value:",
            last_value.value
        )

        print(
            "First 10 Values:"
        )

        print(
            first_ten.value
        )

        print(
            "DONE"
        )


if __name__ == "__main__":

    main()