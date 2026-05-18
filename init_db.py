import sqlite3

def initalize_database():
#'freelance.db' adında bir dosya oluşturur ve ona bağlanır.
    connection= sqlite3.connect('freelance.db')
   
    with open('schema.sql') as f:
        #schema içindeki komutları çalıştırır.
        connection.executescript(f.read())
        
    connection.commit()
    connection.close()
    print("Database created successfully!")

if __name__=="__main__":
    initalize_database()