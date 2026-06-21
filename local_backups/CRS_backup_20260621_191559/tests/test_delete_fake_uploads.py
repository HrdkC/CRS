from database.database import get_connection

conn = get_connection()

cursor = conn.cursor()

cursor.execute("""

DELETE FROM recipe_upload_history

WHERE recipe_code='PLC_P15KM_TEST'

""")

conn.commit()

print(

    "Deleted Rows:",

    cursor.rowcount

)

conn.close()