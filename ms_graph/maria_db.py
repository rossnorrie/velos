import mysql.connector
from mysql.connector import errorcode
import json

class MariaDBManager:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.conn = None
        self.cursor = None

    def connect(self, use_database=False):
        """
        Establish connection to the MariaDB server.
        Optionally skip the database when connecting (use_database=False).
        """
        try:
            if use_database:
                # Connect using the specified database
                self.conn = mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=self.database
                )
            else:
                # Connect without specifying a database
                self.conn = mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password
                )
            self.cursor = self.conn.cursor()
            print(f"Connected to MariaDB {'with' if use_database else 'without'} database.")
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            if err.errno == errorcode.ER_BAD_DB_ERROR:
                print(f"Database '{self.database}' does not exist.")
            elif err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Invalid username or password.")
            else:
                print(f"Error connecting to MariaDB: {err}")
            return False
        return True

    def create_database(self):
        """Create the database if it does not exist."""
        try:
            if not self.cursor:
                print("Cursor is not initialized. Can't create the database.")
                return False

            # Execute database creation query
            self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            print(f"Database '{self.database}' created or already exists.")
        except mysql.connector.Error as err:
            print(f"Failed to create the database: {err}")
            return False
        return True

    def reconnect_with_database(self):
        """Reconnect to the MariaDB after the database is created."""
        self.close()  # Close the existing connection
        return self.connect(use_database=True)

    def create_key_value_table(self, table_name='user_data'):
        """
        Create a key-value table for storing user data with a baseline date.
        :param table_name: Name of the table to create.
        """
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id VARCHAR(255),
            `key` VARCHAR(255),
            `value` VARCHAR(255),
            baseline DATETIME,
            datestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id, `key`, baseline)
        );
        """

        # Queries to create the suggested indexes
        create_indexes = [
            # Index on `datestamp` (optional, based on query needs)
            f"CREATE INDEX idx_datestamp ON {table_name} (datestamp);",

            # Index on `id` and `key`
            f"CREATE INDEX idx_id_key ON {table_name} (id, `key`);",

            # Index on `id` and `baseline`
            f"CREATE INDEX idx_id_baseline ON {table_name} (id, baseline);",

            # Index on `key` and `baseline`
            f"CREATE INDEX idx_key_baseline ON {table_name} (`key`, baseline);",

            # Index on `baseline` and `datestamp` (if needed)
            f"CREATE INDEX idx_baseline_datestamp ON {table_name} (baseline, datestamp);",

            # Full-Text Index on `value`
            f"CREATE FULLTEXT INDEX idx_fulltext_value ON {table_name} (`value`);",

            # Regular Index on `key` (with prefix length if appropriate)
            f"CREATE INDEX idx_key ON {table_name} (`key`);",

            # Index with prefix length on `key` (optional)
            # f"CREATE INDEX idx_key_prefix ON {table_name} (`key`(100));",

            # Index on `baseline` (if not covered by other indexes)
            f"CREATE INDEX idx_baseline ON {table_name} (baseline);",

            # Uncomment this line if you want an additional unique index
            # f"CREATE UNIQUE INDEX idx_unique_id_key ON {table_name} (id, `key`);"
        ]

        try:
            # Create the table
            self.cursor.execute(create_table_query)

            # Create the indexes
            for index_query in create_indexes:
                try:
                    self.cursor.execute(index_query)
                except mysql.connector.Error as err:
                    # Handle exceptions (e.g., index already exists)
                    pass  # You can log the error if needed

            #print(f"Table '{table_name}' and indexes created successfully.")
        except mysql.connector.Error as err:
            #print(f"Failed to create table or indexes for '{table_name}': {err}")
            return False
        return True

    def process_data_list(self, table, data_list, baseline, id=None):
        counter = 0
        for data_item in data_list:
            self.insert_or_update_data(table, data_item, baseline, id)
            counter = counter + 1
            progress = round(counter/len(data_list)*100)
            
            print(f"Table '{table}': '{counter}' of {len(data_list)} - {progress}%")
    
    def insert_or_update_data(self, table_name, data_list, baseline, id=None):
        """
        Insert or update multiple key-value pairs for a user.
        :param table_name: Name of the table.
        :param data_list: Can be a dictionary or a list of dictionaries.
        :param baseline: Baseline value.
        :param id: Optional ID value.
        """

        self.create_key_value_table(table_name)

        # Check if data_list is a dictionary or a list
        if isinstance(data_list, dict):
            data_list = [data_list]  # Convert single dict to list of dicts for consistency

        # Iterate over each dictionary in the list
        for data_item in data_list:
            # Ensure data_item is a dictionary
            if not isinstance(data_item, dict):
                print(f"Expected a dictionary but got {type(data_item)}: {data_item}")
                return False

            # Extract or use provided 'id'
            object_id = data_item.get('id') if not id else id

            # Ensure object_id and baseline are present
            if not object_id or not baseline:
                print(f"Missing required data (object_id or baseline) for data: {data_item}")
                return False

            query = f"""
            INSERT INTO {table_name} (id, `key`, `value`, baseline, datestamp)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON DUPLICATE KEY UPDATE `value`=VALUES(`value`), baseline=VALUES(baseline)
            """

            try:
                # Iterate over key-value pairs, excluding 'id'
                for key, value in data_item.items():
                    if key != 'id':
                        # Process dict values by making a recursive call
                        if isinstance(value, dict):
                            self.insert_or_update_data(f"{table_name}_{key}", value, baseline, object_id)
                        
                        # Process list values in a loop
                        elif isinstance(value, list):
                            for idx, val in enumerate(value, start=1):
                                generic_key = f"{key}_item_{idx}"  # Generate keys like 'key_item_1', 'key_item_2', etc.
                                val = val[:255] if isinstance(val, str) else val  # Trim value if it's a string
                                val = val if val is not None else 'N/A'  # Handle None values
                                # Insert each item of the list as a separate entry in the table
                                self.cursor.execute(query, (object_id, generic_key, val, baseline))
                        
                        # Process other value types directly
                        else:
                            value = value[:255] if isinstance(value, str) else value  # Trim value if necessary
                            value = value if value is not None else 'N/A'  # Handle None values
                            self.cursor.execute(query, (object_id, key, value, baseline))

                # Commit the transaction after processing all key-value pairs
                self.conn.commit()
                print(f"Inserted or updated data for object '{object_id}' in table '{table_name}'")

            except mysql.connector.Error as err:
                print(f"Failed to insert or update data for object '{object_id}': {err}")
                return False

        return True
        

    def close(self):
        """Close the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

# Example usage:
def db_connection(host="localhost", user="root", password="root", database="hc_graph"):
    """
    Establish a MariaDB connection, create the database if necessary, and return the manager.
    """
    manager = MariaDBManager(host=host, user=user, password=password, database=database)

    # Step 1: Connect without specifying the database to create it
    connected = manager.connect(use_database=False)

    if connected:
        # Step 2: Create the database if it does not exist
        if manager.create_database():
            # Step 3: Reconnect with the database now that it exists
            if not manager.reconnect_with_database():
                print("Failed to reconnect with the database.")
                return None
        else:
            print("Failed to create the database.")
            return None
    else:
        print("Failed to connect to the MariaDB server.")
        return None

    return manager