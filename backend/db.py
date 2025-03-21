
from configuration.config import SQLOperation

from log.log import logger

def extract_db_schema():
    temp_fk = '''
        SELECT f.name AS foreign_key_name, OBJECT_NAME(f.parent_object_id) AS table_name  
       ,COL_NAME(fc.parent_object_id, fc.parent_column_id) AS constraint_column_name  
       ,OBJECT_NAME (f.referenced_object_id) AS referenced_object  
       ,COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS referenced_column_name  
       ,f.is_disabled, f.is_not_trusted
       ,f.delete_referential_action_desc  
       ,f.update_referential_action_desc  
        FROM sys.foreign_keys AS f  
        INNER JOIN sys.foreign_key_columns AS fc   
           ON f.object_id = fc.constraint_object_id    
        WHERE f.parent_object_id = OBJECT_ID('{}')
            '''
    temp_pk = '''
        SELECT
        tc.CONSTRAINT_NAME, ccu.COLUMN_NAME
    FROM
        INFORMATION_SCHEMA.TABLE_CONSTRAINTS AS tc
        JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE AS ccu ON ccu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
    WHERE
        tc.TABLE_NAME = '{}'
        AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
    '''
    schema_dict = dict()
    schema_string = '\n'
    
    logger.info("Establishing connection to the database.")
    conn = SQLOperation('oraindb').get_connection()
    
    if not conn:
        logger.error("Connection object is None.")
        return None
    
    cursor = conn.cursor()
    
    try:
        # Query to get all tables
        logger.info("Fetching all table names from sys.tables.")
        cursor.execute("SELECT name FROM sys.tables")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            table_schema = []
            logger.info(f"Processing table: {table_name}")

            # Query to get columns
            logger.info(f"Fetching columns for table: {table_name}.")
            cursor.execute(f"SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'")
            schema = cursor.fetchall()

            # Query to get foreign keys
            logger.info(f"Fetching foreign keys for table: {table_name}.")
            cursor.execute(f"SELECT * FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_NAME IN (SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_NAME = '{table_name}')")
            foreign_keys = cursor.fetchall()

            # Query to get primary keys
            logger.info(f"Fetching primary keys for table: {table_name}.")
            cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_NAME = '{table_name}' AND CONSTRAINT_NAME LIKE '%PK%'")
            primary_keys_cursor = cursor.fetchall()
            primary_keys = [key[0] for key in primary_keys_cursor]

            for column in schema:
                column_name = column[3]
                data_type = column[7]
                is_null = 'NOT NULL' if column[6] == 'NO' else 'NULL'
                if column_name in primary_keys:
                    table_schema.append(f'{column_name} {data_type} PRIMARY_KEY'.upper())
                else:
                    table_schema.append(f'{column_name} {data_type} {is_null}'.upper())

            for fk in foreign_keys:
                fk_string = f'FOREIGN KEY {fk[2]} REFERENCES {fk[3]} {fk[4]}'.upper()
                table_schema.append(fk_string)

            table_schema_str = ",\n".join(table_schema)
            final_table_schema = f'CREATE TABLE {table_name}(\n{table_schema_str}\n);'

            schema_string += final_table_schema + "\n\n"
            schema_dict[table_name] = final_table_schema
        
        logger.info("Schema extraction completed successfully.")
        return schema_string, conn

    except Exception as e:
        logger.error(f"Error occurred while extracting schema: {e}")
        return None, conn
