from drivers import database
import time
from pprint import pprint

# SHOW ONE HOW ONE CLIENT CAN HAVE UPDATES SIMULATED FOR 1 SECOND
for reading in database.fetch_reading_set("../sensitive/modbus_data.db", "2024-10-01 04:45:00"):
    pprint(reading[2])
    time.sleep(1)