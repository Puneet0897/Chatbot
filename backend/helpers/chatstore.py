import re
import pymssql

def get_connection():
    server = 'orian-server.database.windows.net'
    database = 'oraindb'
    username = 'orain'
    password = 'P#H3m5Y+*CsbZrk'
    try:
        conn = pymssql.connect(
            server=server,
            database=database,
            user=username,
            password=password,
            port=1433,
            login_timeout=300, 
            timeout=300 
        )
        print("Connection successful!")
        return conn

    except Exception as e:
        print(f"Error occurred: {e}")

def find_pattern(text):
    # Extract citations
    citation_pattern = r'\[.*?\]'
    citations = re.findall(citation_pattern, text)
    
    # Extract follow-up questions
    follow_up_pattern = r"<<([^>>]+)>>"
    follow_up_questions = re.findall(follow_up_pattern, text)
    
    return citations, follow_up_questions

def save_message(user_query, user_name, user_email, conversationId, response, bot_type):
    # Get the full answer text
    answer = response["answer"]
    
    # Extract citations and follow-up questions
    citations, follow_up_questions = find_pattern(answer)
    
    # Remove citations and follow-up questions from the answer text
    answer_cleaned = re.sub(r'\[.*?\]', '', answer)  # Remove citations
    answer_cleaned = re.sub(r"<<([^>>]+)>>", '', answer_cleaned)  # Remove follow-up questions
    
    # Trim any excess whitespace
    answer_cleaned = answer_cleaned.strip()
    
    result = {
        "user_query": user_query,
        "user_name": user_name,
        "user_email": user_email,
        "conversationId": conversationId,
        "bot_type": bot_type,
        "cleaned_answer": answer_cleaned,
        "citations": citations,
        "follow_up_questions": follow_up_questions,
    }
    
    print(result)
    
    # Insert data into the database
    insert_data_into_db(result)

def insert_data_into_db(data):
    # Establish a connection to the database
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Insert into Users table if the user does not exist
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM ChatConversations.Users WHERE email = %s)
            BEGIN
                INSERT INTO ChatConversations.Users (username, email)
                VALUES (%s, %s)
            END
        """, (data['user_email'], data['user_name'], data['user_email']))
        
        # Insert into BotTypes table if the bot type does not exist
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM ChatConversations.BotTypes WHERE type_name = %s)
            BEGIN
                INSERT INTO ChatConversations.BotTypes (type_name)
                VALUES (%s)
            END
        """, (data['bot_type'], data['bot_type']))
        
        # Insert into Conversations table if the conversation does not exist
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM ChatConversations.Conversations WHERE conversation_id = %s)
            BEGIN
                INSERT INTO ChatConversations.Conversations (conversation_id, email, username, bot_type)
                VALUES (%s, %s, %s, %s)
            END
        """, (data['conversationId'], data['conversationId'], data['user_email'], data['user_name'], data['bot_type']))
        
        # Insert into Messages table for the user query
        cursor.execute("""
            INSERT INTO ChatConversations.Messages (conversation_id, role, content)
            VALUES (%s, 'user', %s)
        """, (data['conversationId'], data['user_query']))
        
        # Insert into Messages table for the bot response and get the message_id
        cursor.execute("""
            INSERT INTO ChatConversations.Messages (conversation_id, role, content)
            OUTPUT INSERTED.message_id
            VALUES (%s, 'assistant', %s)
        """, (data['conversationId'], data['cleaned_answer']))
        message_id = cursor.fetchone()[0]
        
        # Insert into Citations table
        for citation in data['citations']:
            cursor.execute("""
                INSERT INTO ChatConversations.Citations (message_id, citation_text)
                VALUES (%s, %s)
            """, (message_id, citation))
        
        # Insert into FollowupQuestions table
        for i, question in enumerate(data['follow_up_questions']):
            cursor.execute("""
                INSERT INTO ChatConversations.FollowupQuestions (message_id, question_text, question_order)
                VALUES (%s, %s, %s)
            """, (message_id, question, i + 1))
        
        # Commit the transaction
        conn.commit()
    
    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    
    finally:
        # Close the connection
        cursor.close()
        conn.close()

def get_specific_conversation(user_email, bot_type, conversation_id):
    try:
        # Establish database connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Fetch the conversation record to verify user_email and bot_type
        query = """
            SELECT conversation_id, created_at
            FROM ChatConversations.Conversations
            WHERE conversation_id = %s AND email = %s AND bot_type = %s
        """
        cursor.execute(query, (conversation_id, user_email, bot_type))
        conversation_record = cursor.fetchone()
        
        if not conversation_record:
            return {'error': 'Conversation not found or unauthorized access.'}
        
        # Fetch messages for this conversation
        message_query = """
            SELECT message_id, role, content, created_at
            FROM ChatConversations.Messages
            WHERE conversation_id = %s
            ORDER BY created_at
        """
        cursor.execute(message_query, (conversation_id,))
        messages = []
        for msg_row in cursor.fetchall():
            message_id = msg_row[0]
            role = msg_row[1]
            content = msg_row[2]
            message_created_at = msg_row[3]
            
            # Fetch citations for this message
            citation_query = """
                SELECT citation_id, citation_text, created_at
                FROM ChatConversations.Citations
                WHERE message_id = %s
            """
            cursor.execute(citation_query, (message_id,))
            citations = []
            for cit_row in cursor.fetchall():
                citations.append({
                    'citation_id': cit_row[0],
                    'citation_text': cit_row[1],
                    'created_at': str(cit_row[2])
                })
            
            # Fetch follow-up questions for this message
            followup_query = """
                SELECT question_id, question_text, question_order, is_asked, created_at
                FROM ChatConversations.FollowupQuestions
                WHERE message_id = %s
            """
            cursor.execute(followup_query, (message_id,))
            followups = []
            for fu_row in cursor.fetchall():
                followups.append({
                    'question_id': fu_row[0],
                    'question_text': fu_row[1],
                    'question_order': fu_row[2],
                    'is_asked': bool(fu_row[3]),
                    'created_at': str(fu_row[4])
                })
            
            messages.append({
                'message_id': message_id,
                'role': role,
                'content': content,
                'created_at': str(message_created_at),
                'citations': citations,
                'followup_questions': followups
            })
        
        # Structure the conversation data
        conversation_data = {
            'conversation_id': conversation_id,
            'created_at': str(conversation_record[1]),
            'messages': messages
        }
        
        cursor.close()
        conn.close()
        return conversation_data
    except Exception as e:
        print(f"An error occurred: {e}")
        return {'error': 'An error occurred while fetching conversation data.'} 

def get_conversation_topicsdata(user_email,bot_type):
    try:
        # Establish database connection   
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT c.conversation_id, c.created_at, m.content AS topic
            FROM ChatConversations.Conversations c
            LEFT JOIN (
                SELECT conversation_id, content
                FROM (
                    SELECT conversation_id, content, ROW_NUMBER() OVER (PARTITION BY conversation_id ORDER BY created_at ASC) AS rn
                    FROM ChatConversations.Messages
                    WHERE role = 'user'
                ) sub
                WHERE rn = 1
            ) m ON c.conversation_id = m.conversation_id
            WHERE c.email = %s AND c.bot_type = %s
        """
        cursor.execute(query, (user_email, bot_type))
        
        conversations = []
        for row in cursor.fetchall():
            conversations.append({
                'conversation_id': row[0],
                'created_at': str(row[1]),
                'topic': row[2]
            })
             
        cursor.close()
        conn.close()
        return conversations
    except Exception as e:
        print(f"An error occurred: {e}")
        return ({'error': 'An error occurred while fetching conversation topics.'}) 

def delete_conversation_data(conversation_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Start a transaction
        conn.autocommit(False)

        # Step 1: Delete citations associated with the conversation
        cursor.execute("""
            DELETE FROM ChatConversations.Citations
            WHERE message_id IN (
                SELECT message_id
                FROM ChatConversations.Messages
                WHERE conversation_id = %s
            )
        """, (conversation_id,))

        # Step 2: Delete follow-up questions associated with the conversation
        cursor.execute("""
            DELETE FROM ChatConversations.FollowupQuestions
            WHERE message_id IN (
                SELECT message_id
                FROM ChatConversations.Messages
                WHERE conversation_id = %s
            )
        """, (conversation_id,))

        # Step 3: Delete messages associated with the conversation
        cursor.execute("""
            DELETE FROM ChatConversations.Messages
            WHERE conversation_id = %s
        """, (conversation_id,))

        # Step 4: Delete the conversation itself
        cursor.execute("""
            DELETE FROM ChatConversations.Conversations
            WHERE conversation_id = %s
        """, (conversation_id,))

        # Commit the transaction
        conn.commit()

        # Return a success message
        return ({"message": f"Conversation {conversation_id} and all related data deleted successfully"}), 200

    except Exception as e:
        # Rollback the transaction in case of an error
        conn.rollback()
        print(f"An error occurred: {e}")
        return ({"error": f"An error occurred while deleting the conversation: {str(e)}"}), 500

    finally:
        # Close the cursor and connection
        cursor.close()
        conn.close() 
        