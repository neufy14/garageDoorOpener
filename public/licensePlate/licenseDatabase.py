import mysql.connector

# Establish connection
connection = mysql.connector.connect(
    host="your_host",
    user="your_username",
    password="your_password"
)
# Create a cursor object
cursor = connection.cursor()

# Execute SQL command to create database
cursor.execute("CREATE DATABASE my_database")

# Select the database
cursor.execute("USE my_database")

# Execute SQL command to create table
cursor.execute("""
    CREATE TABLE my_table (
        id INT AUTO_INCREMENT PRIMARY KEY,
        column1 VARCHAR(255),
        column2 VARCHAR(255),
        column3 INT,
        column4 DATE
    )
""")

# Commit changes
connection.commit()

# Close cursor and connection
cursor.close()
connection.close()