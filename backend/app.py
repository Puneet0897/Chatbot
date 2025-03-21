import os
import mimetypes
import time
from time import sleep
import logging
from log.log import logger
import shutil
import base64
import json
import traceback
import asyncio
from io import BytesIO
# import nltk
# nltk.download('punkt')
import sys
from flask import Flask, request, jsonify,send_from_directory 
# from azure.identity import DefaultAzureCredential
from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from azure.storage.blob import BlobServiceClient
import pandas as pd 
from db import extract_db_schema,SQLOperation
from configuration.config import *
from helpers.data_management import *

from http import HTTPStatus

from callcenter_analytics.utils import convert_audio_to_text, analyse_transcript

from approaches.respondreadentity import respond_react
from langchain.vectorstores.azuresearch import AzureSearch
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from flask_cors import CORS 
from pathlib import Path
#from dashapp import create_dash_app
# from plot_graphs import create_dash_app
from helpers.chatstore import *



blob_client = BlobServiceClient.from_connection_string(blob_connect_str)
blob_container = blob_client.get_container_client(AZURE_STORAGE_CONTAINER)


chat_approaches = {
    "rrr": ChatReadRetrieveReadApproach()
}

# extract db schema
db_schema, conn = extract_db_schema()
logger.info(db_schema)
print(db_schema)

app = Flask(__name__)
CORS(app)
#create_dash_app(app)

# dash_app = create_dash_app(app)



@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)



@app.route("/content", methods=["GET"])
def content_file():
    path = request.args.get('path', '').strip()  # Strip any leading/trailing spaces
    download = request.args.get("download")

    if not path:
        logger.error("Path parameter is missing in the request.")
        return jsonify({"error": "Path parameter is required."}), 400

    
    
    file_type = os.path.splitext(path)[1].lower()
    logger.info(f"Requested path: {path}")

    if download == "false":
        if file_type == ".pdf":
            file_path = Path(path).name
        else:
            file_path = Path(path).name
    else:
        file_path = path

    logger.info(f"Final blob path to retrieve: {file_path}")

    try:
        blob_client = blob_container.get_blob_client(file_path)
        blob = blob_client.download_blob()
        logger.info(f"Successfully retrieved blfilenameob for file: {file_path}")
    except Exception as e:
        logger.error(f"Error retrieving blob: {e}")
        return jsonify({"error": "File not found."}), 404

    mime_type = blob.properties["content_settings"]["content_type"]
    if mime_type == "application/octet-stream":
        mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    
    disposition_type = "inline" if download == "false" else "attachment"
    logger.info(f"Setting content disposition: {disposition_type}; filename={file_path}")

    return blob.readall(), 200, {
        "Content-Type": mime_type,
        "Content-Disposition": f"{disposition_type}; filename={file_path}"
    }


@app.route("/fetch_topics", methods=["POST"])
def fetch_topics():
    data = request.get_json()
    user_email = request.json["email"]
    user_query = data['query_text']
    result = get_similar_embeddings(user_query,user_email)
    return jsonify(result)



@app.route("/chat", methods=["POST"])
def chat():
    approach = request.json["approach"] 
    bot_type = request.json["bot_type"]
    user_query = request.json ['history'][-1]["user"]
    user_name = request.json["username"]
    user_email = request.json["email"]
    conversationId= request.json["conversationId"]
    try:
        impl = chat_approaches.get(approach)
        if not impl:
            return jsonify({"error": "unknown approach"}), 400
        response = impl.run(request.json["history"], request.json.get(
            "overrides") or {}, AZURE_ENV_NAME, db_schema, conn, bot_type,user_email)
        print("response data",response["answer"])
        save_message(user_query,user_name,user_email,conversationId,response,bot_type)
        return jsonify(response)
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(stack_trace)
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversation', methods=['GET'])
def get_conversation():
    user_email = request.args.get('user_email')
    bot_type = request.args.get('bot_type')
    conversation_id = request.args.get('conversation_id')
    
    if not user_email or not bot_type:
        return jsonify({'error': 'user_email and bot_type parameters are required.'}), 400
    
    try:
       conversations = get_specific_conversation(user_email,bot_type,conversation_id)   
       return jsonify(conversations)
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': 'An error occurred while fetching conversation topics.'}), 500
    
@app.route('/api/conversation_topics', methods=['GET'])
def get_conversation_topics():
    user_email = request.args.get('user_email')
    bot_type = request.args.get('bot_type')
    
    if not user_email or not bot_type:
        return jsonify({'error': 'user_email and bot_type parameters are required.'}), 400
    
    try:
       
       conversations = get_conversation_topicsdata(user_email,bot_type)
       return jsonify(conversations)
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': 'An error occurred while fetching conversation topics.'}), 500

# Database connection function
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
        return None

# DELETE route for deleting a conversation
@app.route('/api/delete_conversation/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):

    try:
        delete_conversation_data(conversation_id)
        
        return jsonify({"message": f"Conversation {conversation_id} and all related data deleted successfully"}), 200

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": f"An error occurred while deleting the conversation: {str(e)}"}), 500

@app.route("/upload", methods=["POST"])
def upload():
    bot_type = request.form['bot_type']
    email = request.form['email']
    if(bot_type=="KNOWLEDGE_BOT_WITH_CACHE"):
        bot_type="KNOWLEDGE_BOT"

    logger.info(f"Uploading bot type {bot_type}")
    isdelete = False
    # Generate a unique folder name using the current time
    folder_name = str(int(time.time()))
    folder_path = os.path.join(UPLOAD_FOLDER, folder_name)
    # extracted_topics=upload_data(final_path, AZURE_ENV_NAME + "_" + bot_type, folder_path, bot_type)
    urls_data = []
    if 'Urls' in request.form:
        urls = request.form["Urls"]
        logger.info(f"---URLS : {urls}")
        urls_data = urls.split(";")
    if 'file' not in request.files and len(urls_data) == 0:
        return jsonify({'error': 'No file provided'})
    if len(request.files.getlist('file')) == 0 and len(urls_data) == 0:
        return jsonify({'error': 'No file selected'})
    for file in request.files.getlist('file'):
        logger.info(f"Uploading file {file.filename} to {folder_name}")
        # Create the folder if it doesn't exist
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        isdelete = True
        file_path = os.path.join(folder_path, file.filename)
        if file and allowed_file(file.filename):
            file.save(file_path)
            logger.info(f"Uploaded file to {file_path}")
    final_path = folder_path + "/*"
    extracted_topics=upload_data(final_path, AZURE_ENV_NAME + "_" + bot_type, folder_path, bot_type,email)
    if urls_data:
        logger.info(f"URLs are: {urls_data}")
        for url in urls_data:
            extracted_topics=upload_url_to_vectorstore(url, AZURE_ENV_NAME + "_" + bot_type,email)

    if isdelete:
        shutil.rmtree(folder_path)
    return {"success": True, "topics": extracted_topics }



@app.route("/delete/<bot_type>", methods=["GET"])
def delete_vectorstore_index(bot_type):
    logger.info(f"Deleting bot type {bot_type}")

    if bot_type == "KNOWLEDGE_BOT_WITH_CACHE":
        bot_type = "KNOWLEDGE_BOT"
        logger.info(f"---Deleting bot type {bot_type}")
        cache_search_client = SearchClient(
            endpoint=vector_store_address,
            index_name=AZURE_COGNITIVE_SEARCH_CACHE_INDEX_NAME,
            credential=AzureKeyCredential(vector_store_password)
        )
        delete_documents_cache(cache_search_client, bot_type)

        # Deleting records from SQLite database
        conn = SQLOperation('KnowledgeBotDB').get_connection()
        cursor = conn.cursor()
        cursor.execute('''DELETE FROM vectorstore_cache WHERE category=?''', (AZURE_ENV_NAME + "_" + "KNOWLEDGE_BOT_WITH_CACHE"+"_cache"))
        conn.commit()
        cursor.close()
        
    search_client = SearchClient(
        endpoint=vector_store_address,
        index_name=AZURE_COGNITIVE_SEARCH_INDEX_NAME_ROLE_BASED,
        credential=AzureKeyCredential(vector_store_password)
    )
    delete_documents(search_client, bot_type)
    remove_blobs(metadata={"category": AZURE_ENV_NAME + "_" + bot_type})

    return {"success": True}





@app.route('/analyse_transcript', methods=['POST'])
def analyse_trans():
    try:
        print("Request",request.data)
        fileNameToAnalyse=os.path.join('static',request.data.decode())
        # Call the analyse_transcript() method to process the transcript data
        print("filenametoanalyse",fileNameToAnalyse)
        analytics_response = analyse_transcript(fileNameToAnalyse)

        # Return the analytics_response as a JSON response
        return jsonify(analytics_response), 200

    except Exception as e:
        # In case of any errors, return an error message with the appropriate status code
        return jsonify({'error': str(e)}), 500


@app.route('/transcribe', methods=['POST'])
def transcribeAudio():
    try:
        print("Request",request.data)
        fileNameToTranscribe=request.data.decode()
        print("Working dir",os.getcwd())
        outputfile = os.path.join(os.getcwd(),'static', fileNameToTranscribe.split(".")[0] + ".txt")
        if not os.path.exists(outputfile):
            convert_audio_to_text(fileNameToTranscribe, outputfile)
        else:
            print("Output file {} already exists, so do not call conversion".format(outputfile))
            sleep(5)
        return jsonify({'status':'Transcribed'}), 200
    except Exception as e:
        return jsonify({'status': str(e)}), 500


@app.route('/uploadAudio', methods=['POST'])
def upload_audio():
    try:
        # Check if any files were uploaded
        if 'audioFile' not in request.files:
            return jsonify({'error': 'No audio files provided'}), 400

        audio_files = request.files.getlist('audioFile')

        # Validate file names and upload files to Azure Blob Storage
        filenames = []
        for audio_file in audio_files:
            if audio_file.filename == '':
                return jsonify({'error': 'Invalid audio file'}), 400

            container_client = blob_client.get_container_client("audiofiles")  # Specify the "audiofiles" container
            blob_client_local = container_client.get_blob_client(blob=audio_file.filename)  # Local blob client for each file
            blob_client_local.upload_blob(audio_file.read(), overwrite=True)  # Upload the file, overwrite if it exists
            filenames.append(audio_file.filename)

        return jsonify({'message': 'Audio files uploaded successfully', 'filenames': filenames}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/get_documents", methods=["GET"])
def get_documents():
    user_name = request.args.get('user_email')
    # print("**********user_name**********",user_name)

    if not user_name:
        return jsonify({'error': 'user_name parameter is required.'}), 400

    try:
        # Get the unique document names for the user
        conn = get_connection()
        cursor = conn.cursor()
        # Query to select unique document names for the given user_name
        # Query to select unique document names for the given user_name
        query = '''SELECT DISTINCT doc_name 
                        FROM RoleBasedDocuments 
                        WHERE acl LIKE %s 
                        AND status = 'ACTIVE' '''
        params = ('%' + user_name + '%',)

        # Print the full query for debugging (with proper string formatting)
        formatted_query = query.replace("%s", f"'{params[0]}'")  
        # print("Executing Query:", formatted_query)
        # Execute the query
        cursor.execute(query, params)

        # Fetch all results
        documents = cursor.fetchall()
        # print(documents)
        
        # If no documents found, return a message
        if not documents:
            return jsonify({'message': 'No documents found for the user.'}), 404
        
        # Extract doc_name from the results
        document_names = [doc[0] for doc in documents]
        
        # Close the connection
        cursor.close()
        return jsonify({'documents': document_names}), 200
    
    except Exception as e:
        logger.error(f"Error fetching documents: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching documents.'}), 500


    
@app.route("/multi_delete_documents", methods=["POST"])
def multi_delete_documents():
    data = request.get_json()

    # Extracting user_name and documents list
    user_name = data.get("user_name")
    documents = data.get("documents", [])

    if not user_name or not documents:
        return jsonify({'error': 'user_name and documents list are required.'}), 400

    try:
        conn = SQLOperation('oraindb').get_connection()
        cursor = conn.cursor()

        for doc in documents:
            query = "SELECT acl, doc_id FROM RoleBasedDocuments WHERE doc_name = %s"
            print("Executing query:", query % repr(doc))  # Print query for debugging
            cursor.execute(query, (doc,))
            results = cursor.fetchall()  # Fetch all matching rows

            if not results:
                logger.info(f"No records found for document: {doc}")
                continue  # Skip to next document

            for result in results:
                acl_users, doc_id = result[0], result[1]  # Extract ACL and doc_id
                print(f"Processing Document: {doc}, Doc ID: {doc_id}, ACL: {acl_users}")

                try:
                    acl_users = json.loads(acl_users) if acl_users else []
                except json.JSONDecodeError:
                    acl_users = acl_users.split(",") if acl_users else []  # Handle non-JSON ACL cases

                if user_name in acl_users:
                    if len(acl_users) > 1:
                        # Remove only the specified user from ACL
                        acl_users.remove(user_name)
                        updated_acl = json.dumps(acl_users)
                        update_query = "UPDATE RoleBasedDocuments SET acl = %s WHERE doc_id = %s"
                        print("Executing query:", update_query % (repr(updated_acl), repr(doc_id)))
                        cursor.execute(update_query, (updated_acl, doc_id))
                        logger.info(f"Removed {user_name} from ACL for {doc}.")
                    elif len(acl_users) == 1 and acl_users[0] == user_name:
                        # Only one user in ACL, deactivate document
                        update_query = "UPDATE RoleBasedDocuments SET status = 'INACTIVE' WHERE doc_id = %s"
                        print("Executing query:", update_query % repr(doc_id))
                        cursor.execute(update_query, (doc_id,))
                        logger.info(f"Deactivated document {doc}.")
                        delete_documents_withdocid(doc_id)
                else:
                    logger.info(f"User {user_name} not found in ACL for {doc}. Skipping update.")

        conn.commit()
        return jsonify({'message': 'Documents processed successfully.'}), 200

    except Exception as e:
        logger.error(f"Error while processing documents: {e}")
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("Database connection closed.")

        
@app.route("/single_delete_documents", methods=["POST"])
def single_delete_documents():
    data = request.get_json()
    
    # Extract user_name and documents list
    user_name = data.get("user_name")
    documents = data.get("documents", [])

    if not user_name or not documents:
        return jsonify({'error': 'user_name and documents list are required.'}), 400

    messages = []  # Initialize messages list to store response messages

    try:
        conn = get_connection()
        if not conn:
            print("Database connection failed. Exiting function.")
            return jsonify({'error': 'Database connection failed.'}), 500
        
        cursor = conn.cursor()

        for doc in documents:
            query = "SELECT acl, doc_id FROM RoleBasedDocuments WHERE doc_name = %s"
            print("Executing query:", query % repr(doc))

            cursor.execute(query, (doc,))
            results = cursor.fetchall()  # Fetch all matching rows
            print(results, "results")

            if not results:
                msg = f"No records found for document: {doc}"
                print(msg)
                messages.append(msg)
                continue  # Skip to next document if no results found

            for result in results:
                acl_users, doc_id = result[0], result[1]  # Extract ACL and doc_id
                print(f"Processing Document: {doc}, Doc ID: {doc_id}, ACL: {acl_users}")

                try:
                    acl_users = json.loads(acl_users) if acl_users else []
                except json.JSONDecodeError:
                    acl_users = acl_users.split(",") if acl_users else []  # Handle non-JSON ACL cases

                if user_name in acl_users:
                    if len(acl_users) > 1:
                        # Remove the user from ACL and update the record
                        acl_users.remove(user_name)
                        updated_acl = json.dumps(acl_users)
                        update_query = "UPDATE RoleBasedDocuments SET acl = %s WHERE doc_id = %s"
                        print("Executing query:", update_query % (repr(updated_acl), repr(doc_id)))
                        cursor.execute(update_query, (updated_acl, doc_id))
                        msg = f"Removed {user_name} from ACL for {doc}."
                        print(msg)
                        messages.append(msg)
                    elif len(acl_users) == 1 and acl_users[0] == user_name:
                        # If only this user is in ACL, deactivate document
                        update_query = "UPDATE RoleBasedDocuments SET status = 'INACTIVE' WHERE doc_id = %s"
                        print("Executing query:", update_query % repr(doc_id))
                        cursor.execute(update_query, (doc_id,))
                        msg = f"Deactivated document {doc}."
                        print(msg)
                        messages.append(msg)
                        delete_documents_withdocid(doc_id)
                else:
                    msg = f"User {user_name} not found in ACL for {doc}. Skipping update."
                    print(msg)
                    messages.append(msg)

        conn.commit()
        print("Database updates committed successfully.")

    except Exception as e:
        print(f"Error while processing documents: {e}")
        return jsonify({'error': str(e)}), 500

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        print("Database connection closed.")

    return jsonify({'messages': messages}), 200

@app.route("/get_all_user_documents", methods=["POST"])
def get_all_user_documents():
    data = request.get_json()
    # user_name = data.get("user_name")

    # if not user_name:
    #     return jsonify({"error": "user_name is required."}), 400

    try:
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed."}), 500

        cursor = conn.cursor()
        query = "SELECT distinct doc_name FROM RoleBasedDocuments WHERE status = 'ACTIVE'"
        cursor.execute(query,)
        documents = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()

        return jsonify({"documents": documents}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/search_documents", methods=["POST"])
def search_documents():
    data = request.get_json()
    search_query = data.get("search_query", "").strip().lower()
    documents = data.get("documents", [])

    if not search_query:
        return jsonify({"error": "search_query is required."}), 400

    filtered_documents = [doc for doc in documents if search_query in doc.lower()]

    return jsonify({"filtered_documents": filtered_documents}), 200


@app.route("/get_users_with_access", methods=["POST"])
def get_users_with_access():
    data = request.get_json()
    doc_name = data.get("doc_name")
    print(doc_name,"DocName")

    if not doc_name:
        return jsonify({"error": "doc_name is required."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        cursor = conn.cursor()
        # Fetch document name from doc_id
        query = "SELECT doc_name, acl FROM RoleBasedDocuments WHERE doc_name = %s"
        cursor.execute(query, (doc_name,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"error": "No document found for the given doc_id."}), 404

        doc_name, acl = result
        acl_users = json.loads(acl) if acl else []

        cursor.close()
        conn.close()

        return jsonify({"users_with_access": acl_users}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/get_users_for_access", methods=["POST"])
def get_users_for_access():
    data = request.get_json()
    doc_name = data.get("doc_name")

    if not doc_name:
        return jsonify({"error": "doc_name is required."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        cursor = conn.cursor()

        # Fetch all distinct users
        cursor.execute("SELECT DISTINCT user_name FROM RoleBasedDocuments")  
        all_users = [row[0] for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return jsonify({
            "users_for_access": all_users
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_users_without_access", methods=["POST"])
def get_users_without_access():
    data = request.get_json()
    doc_name = data.get("doc_name")

    if not doc_name:
        return jsonify({"error": "doc_name is required."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        cursor = conn.cursor()

        # Fetch document name and ACL
        query = "SELECT doc_name, acl FROM RoleBasedDocuments WHERE doc_name = %s"
        cursor.execute(query, (doc_name,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"error": "No document found for the given doc_name."}), 404

        doc_name, acl = result
        acl_users = json.loads(acl) if acl else []

        # Fetch all distinct users
        cursor.execute("SELECT DISTINCT user_name FROM rolebasedusers")  
        all_users = [row[0] for row in cursor.fetchall()]

        # Filter users who do NOT have access
        users_without_access = [user for user in all_users if user not in acl_users]

        cursor.close()
        conn.close()

        return jsonify({
            "users_without_access": users_without_access
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/grant_revoke_permission", methods=["POST"])
def grant_revoke_permission():
    data = request.get_json()
    user_list = data.get("user_list", [])
    doc_name = data.get("doc_name")
    permission = data.get("permission")

    if not user_list or not doc_name or not permission:
        return jsonify({"error": "user_list, doc_name, and permission are required."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    cursor = conn.cursor()

    # Fetch document name corresponding to doc_id
    query = "SELECT doc_id FROM RoleBasedDocuments WHERE doc_name = %s"
    cursor.execute(query, (doc_name,))
    doc_id_list = [row[0] for row in cursor.fetchall()]

    if not doc_id_list:
        return jsonify({"error": "No document found with the given doc_name."}), 404

    try:
        search_client = SearchClient(
            endpoint=vector_store_address,
            index_name=AZURE_COGNITIVE_SEARCH_INDEX_NAME_ROLE_BASED,
            credential=AzureKeyCredential(vector_store_password),
        )

        for doc_id in doc_id_list:
            filter_query = f"doc_id eq '{doc_id}'"
            results = list(search_client.search(search_text="*", filter=filter_query, top=40))

            if not results:
                continue  # Skip this doc_id if no results found

            # Process permissions update for all users in user_list
            for result in results:
                for user in user_list:
                    if permission == "revoke":
                        if user in result["acl"]:
                            result["acl"].remove(user)
                    else:  # Grant permission
                        if user not in result["acl"]:
                            result["acl"].append(user)

            # Upload only once after processing all users
            search_client.upload_documents(results)

        # Update database with the last modified ACL (only if any document was found)
        if results:
            update_query = "UPDATE RoleBasedDocuments SET acl = %s WHERE doc_name = %s"
            cursor.execute(update_query, (json.dumps(results[0]["acl"]), doc_name))
            conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Permission updated successfully."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route("/get_all_users", methods=["GET"])
def get_all_users():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed."}), 500

    try:
        cursor = conn.cursor()

        # Fetch all distinct users
        cursor.execute("SELECT DISTINCT user_name FROM rolebasedusers")  
        all_users = [row[0] for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return jsonify({
            "all_users": all_users
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# if len(sys.argv) > 1:
#     app_port_no = int(sys.argv[1])
# else:
app_port_no = 5000

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=app_port_no)
   




