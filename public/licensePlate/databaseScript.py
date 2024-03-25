import mysql.connector
import uuid
import json
import logging

def add2Database(data_to_insert):
    print("add2database")
    logging.basicConfig(filename="newfile.log",
                    format='%(asctime)s %(message)s',
                    filemode='a')
    # Creating an object
    logger = logging.getLogger()
    
    # Setting the threshold of logger to DEBUG
    logger.setLevel(logging.DEBUG)
    logger.debug("Adding to the log file")
    logger.debug("Log File Index to send to database: %s", str(data_to_insert[0]))
    logger.debug("Log File ValidPlate to send to database: %s", str(data_to_insert[1]))
    logger.debug("Log File Timestamp to send to database: %s", str(data_to_insert[2]))
    # Generate a random UUID (version 4)
    random_id = uuid.uuid4()

    # Convert UUID to string
    random_id_str = str(random_id)

    # Establish connection
    connection = mysql.connector.connect(
        host="localhost",
        user="alex",
        password="Steelers12!"
    )

    # Create a cursor object
    cursor = connection.cursor()

    # # Execute SQL command to create database
    # cursor.execute("CREATE DATABASE licensePlate")

    # Select the database
    cursor.execute("USE licensePlate")

    # # Execute SQL command to create table
    # cursor.execute("""
    #     CREATE TABLE foundPlates (
    #         ID INT AUTO_INCREMENT PRIMARY KEY,
    #         Name VARCHAR(255),
    #         LicensePlate VARCHAR(255),
    #         Timestamp DATE
    #     )
    # """)

    insert_query = "INSERT INTO foundPlates (Name, LicensePlate, Timestamp) VALUES (%s, %s, %s)"
    # data_to_insert = ('Alex', '9AH824', '2024-02-18')
    cursor.execute(insert_query, data_to_insert)

    # Commit changes
    connection.commit()

    # Define the SELECT query
    select_query = "SELECT * FROM foundPlates"

    # Execute the SELECT query
    cursor.execute(select_query)

    # Fetch all rows from the result set
    rows = cursor.fetchall()

    # Display the contents of the table
    for row in rows:
        print(row)


    # Close cursor and connection
    cursor.close()
    connection.close()

    # def getValidPlates():
    #     validPlate = []
    #     userNames = []
    #     doorDataJson = open('doorData.json')
    #     data = json.load(doorDataJson)
    #     for i in data['validLicensePlates']:
    #         validPlate.append(data['validLicensePlates'][i])
    #         userNames.append(i)
    #     doorDataJson.close()
    #     # print('validPlate = ', validPlate)
    #     # print("userNames = ", userNames)
    #     return validPlate, userNames

    # print(getValidPlates()[0])
    # print(getValidPlates()[1])