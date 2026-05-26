import sqlite3

def initalize_database():
    connection= sqlite3.connect('freelance.db')
   
    with open('schema.sql') as f:
        #Executes the commands within the #schema.
        connection.executescript(f.read())
        
    connection.commit()
    connection.close()
    print("Database created successfully!")

if __name__=="__main__":
    initalize_database()