# import pyodbc
import os
import openai
from langchain.embeddings import OpenAIEmbeddings
import platform
import pymssql
# upload data
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER") or "temp"
ALLOWED_FILE_EXTENSIONS = {'pdf', 'pptx', 'docx', 'txt', 'csv', 'xlsx'}

#Call Center analytics
# flask application port
call_center_app_port = int(os.environ.get("CALL_CENTER_APP_PORT") or "8000")
# flask application host
call_center_app_host = os.environ.get("CALL_CENTER_APP_HOST") or "https://orian-chat.graywave-6cb69e84.eastus.azurecontainerapps.io"
# Speech service endpoint
speech_endpoint = "eastus.api.cognitive.microsoft.com"
# Speech service subscription key
speech_subscription_key = "6c91d6d0e26f42f7a13a597073aea7bb"
# This should not change unless you switch to a new version of the Speech REST API.
SPEECH_TRANSCRIPTION_PATH = "/speechtotext/v3.0/transcriptions"
# Interval for transcription to complete
WAIT_SECONDS = 5
callanalytics_dbname = "CallCenterAnalyticsDB"
CALLANALYTICS_OPENAI_API_BASE = "https://openaismartchatgpt.openai.azure.com/"
CALLANALYTICS_OPENAI_API_KEY = "5713a9f9be2e4c1a853d82e784676e66"

AZURE_BLOB_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=xneytestbot6cbk;AccountKey=Zcp68ucy8+M3iIDY4tiRteYDZREN4J4DVkwccw8w2+jSLmjuvN5mLOW62k/jpCm/QowWrnFuULEW+AStYKH33g==;EndpointSuffix=core.windows.net"

# AZURE_BLOB_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=   ;AccountKey=Zcp68ucy8+M3iIDY4tiRteYDZREN4J4DVkwccw8w2+jSLmjuvN5mLOW62k/jpCm/QowWrnFuULEW+AStYKH33g==;EndpointSuffix=core.windows.net"
SSL_CERTIFICATE_SERVER_PEM_FILE_PATH = os.environ.get(
    "SSL_CERTIFICATE_SERVER_PEM_FILE_PATH") or "/home/xoriant_user/SSL/Latest/current/server.pem"

SSL_CERTIFICATE_PRIVATE_KEY_PEM_FILE_PATH = os.environ.get(
    "SSL_CERTIFICATE_PRIVATE_KEY_PEM_FILE_PATH") or "/home/xoriant_user/SSL/Latest/current/privatekey.pem"

blob_connect_str = AZURE_BLOB_CONNECTION_STRING

AZURE_STORAGE_ACCOUNT = os.environ.get(
    "AZURE_STORAGE_ACCOUNT") or "mystoragename"
AZURE_STORAGE_CONTAINER = os.environ.get(
    "AZURE_STORAGE_CONTAINER") or "content"
AZURE_ENV_NAME = AZURE_STORAGE_ACCOUNT[:5]

# GPT deployed models
AZURE_OPENAI_GPT_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_GPT_DEPLOYMENT") or "container-poc-gpt4mini-model"
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_CHATGPT_DEPLOYMENT") or "container-poc-gpt4mini-model"
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT") or "container-poc-embedding"
AZURE_OPENAI_CHATGPT_DEPLOYMENT_16K = os.environ.get(
    "AZURE_OPENAI_CHATGPT_DEPLOYMENT") or "gpt3516k"

api_base = os.environ.get("OPENAI_API_BASE") or "https://azure-open-ai-containerpoc.openai.azure.com/"

# OpenAI Credentials
api_type = "azure"
api_version = os.environ.get("OPENAI_API_VERSION") or "2024-05-01-preview"
api_key = os.environ.get("OPENAI_API_KEY") or "a14ee627c5e6475f8ca272e89efdbe82"
openai.api_type = api_type
openai.api_base = api_base
openai.api_version = api_version
openai.api_key = api_key
os.environ["OPENAI_API_KEY"] = api_key
os.environ["OPENAI_API_VERSION"] = api_version
os.environ["OPENAI_API_BASE"] = api_base


# GPT deployed models(comment code becauuse  API for LLM has changed)
# AZURE_OPENAI_GPT_DEPLOYMENT = os.environ.get(
#     "AZURE_OPENAI_GPT_DEPLOYMENT") or "capture2-gpt-4o-mini" #gpt-35-turbo"
# AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.environ.get(
#     "AZURE_OPENAI_CHATGPT_DEPLOYMENT") or   "capture2-gpt-4o-mini"#"gpt-35-turbo"
# AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.environ.get(
#     "AZURE_OPENAI_EMBEDDING_DEPLOYMENT") or "gptmodelembeddings"
# AZURE_OPENAI_CHATGPT_DEPLOYMENT_16K = os.environ.get(
#     "AZURE_OPENAI_CHATGPT_DEPLOYMENT") or "gpt3516k"

# api_base = os.environ.get("OPENAI_API_BASE") or "https://openaismartchatgpt.openai.azure.com/"


# # OpenAI Credentials
# api_type = "azure"
# api_version = os.environ.get("OPENAI_API_VERSION") or "2023-03-15-preview"  #"2022-12-01"
# api_key = os.environ.get("OPENAI_API_KEY") or "5713a9f9be2e4c1a853d82e784676e66"
# openai.api_type = api_type
# openai.api_base = api_base
# openai.api_version = api_version
# openai.api_key = api_key
# os.environ["OPENAI_API_KEY"] = api_key
# os.environ["OPENAI_API_VERSION"] = api_version
# os.environ["OPENAI_API_BASE"] = api_base


# Azure Pinecone
# pinecone_api_key = "b7e36068-aad0-497a-8212-d24c68f8cbd4"
# pinecone_env = "us-east-1"
# indexName = 'langchain-qa-openai'

# os.environ["PINECONE_API_KEY"] = pinecone_api_key


#Azure AI Search Credentials
vector_store_address = "https://orian.search.windows.net"
vector_store_password = "FQqwc9oRfvpaVe8X5yX1IHsA8Sw6aRW6CaxaQa0ZcSAzSeDYwMaE"
AZURE_COGNITIVE_SEARCH_INDEX_NAME = "orian-search"
AZURE_COGNITIVE_SEARCH_CACHE_INDEX_NAME = "orian-search-cache"
AZURE_COGNITIVE_SEARCH_API_VERSION = "2020-08-01"

#Role based service endpoint and API key  (added by Puneet)
vector_store_address_role_based = "https://rolebasedsearchservice.search.windows.net"
vector_store_password_role_based = "TyB3QPd20su1C86Z9bWbCYZl9X91VXWZ3Ij29G1gwkAzSeDh8phg"
AZURE_COGNITIVE_SEARCH_INDEX_NAME_ROLE_BASED = "rolebasedsearch"  

# OpenAIEmbeddings
embeddings = OpenAIEmbeddings(engine=AZURE_OPENAI_EMBEDDING_DEPLOYMENT, chunk_size=1)

# persona summary questions
persona_questions = {
    "CEOs_Questions": ["What is the main purpose or objective of this information from CEO's perspective?",
                       "How does this information aligns with our organization's overall goals and strategies?",
                       "What are this potential short-term and long-term impacts of the information on our organization's financial performance?",
                       "How does this inform our approach to innovation, product development, or market expansion?",
                       "What are the potential effects of this information on our brand positioning, marketing strategies, or customer experience?",
                       "Are there any implications or considerations for our international operations, global expansion, or geopolitical factors?",
                       "How does this information influence our strategic partnerships, mergers and acquisitions, or investment decisions?"],
    "CHROs_Questions": ["What is the main purpose or objective of this information from CHRO's perspective?",
                        "How does this information align with our organization's overall talent acquisition, retention, and development strategies?",
                        "How does this information inform our approach to employee engagement, organizational culture, or leadership development?",
                        "Are there any insights or best practices mentioned in this information that we can apply to our HR policies, diversity and inclusion initiatives, or employee well-being programs?",
                        "Does this information provide any insights into emerging HR technologies, remote work trends, or workforce planning strategies?",
                        "What are the potential implications for our talent acquisition efforts, succession planning, or performance management mentioned in this information?",
                        "How does this information influence our approach to employee training, skills development, or organizational restructuring?"],


}

# Azure SQL DB for Linux
# connection_string = 'Driver={ODBC Driver 17 for SQL Server};Server=tcp:xorchatdb.database.windows.net,1433;Database=ChatDB;Uid=azureuser;Pwd=Password123;Encrypt=No;TrustServerCertificate=no;Connection Timeout=30;'
# connection_string = 'Driver={SQL Server};Server=tcp:xorchatdb.database.windows.net,1433;Database=ChatDB;Uid=azureuser;Pwd=Password123;Encrypt=No;TrustServerCertificate=no;Connection Timeout=30;'


# sqlserver_ip = "40.75.12.102"
# sqlserver_ip = "127.0.0.1"
#sqlserver_ip = "20.186.173.187"
sqlserver_ip = "localhost"

# sqlserver_client = "SalesDB"
sqlserver_username = "sa"
sqlserver_password = "P#H3m5Y+*CsbZrk"
sqlserver_port = 1433

    
class SQLOperation():
    def __init__(self, sqlserver_client):
        self.server = sqlserver_ip
        self.db_name = sqlserver_client
        self.username = sqlserver_username
        self.password = sqlserver_password
        self.port = sqlserver_port

    def get_connection(self):
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


        # connection_string = 'Driver={ODBC Driver 17 for SQL Server};Server=tcp:' + self.server + ',' + str(
        #      self.port) + ';Database=' + self.db_name + ';Uid=' + self.username + ';Pwd=' + self.password + ';Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=30;'

        #connection_string = 'Driver={ODBC Driver 17 for SQL Server};Server=' + self.server + ',' + str(self.port) + ';Database=' + self.db_name + ';UserId=' + self.username + ';Password=' + self.password + ';Encrypt=no;TrustServerCertificate=no;Connection Timeout=30;;'
       
       
        # connection_string = 'Driver={SQL Server};Server=tcp:' + self.server + ',' + str(
        #   self.port) + ';Database=' + self.db_name + ';Uid=' + self.username + ';Pwd=' + self.password + ';Encrypt=No;TrustServerCertificate=no;Connection Timeout=30;'
        


        # connection_string = 'Driver={ODBC Driver 17 for SQL Server};Server=tcp:' + self.server + ',' + str(
        #    self.port) + ';Database=' + self.db_name + ';Uid=' + self.username + ';Pwd=' + self.password + ';Encrypt=No;TrustServerCertificate=no;Connection Timeout=30;'

        # print("Connection string: {}".format(connection_string))
        # connection = pyodbc.connect(connection_string)
        # return connection
