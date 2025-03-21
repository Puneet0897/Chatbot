import os, requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
#from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
# from langchain.vectorstores.azuresearch import AzureSearch
from helpers.utils import get_custom_fields_normal, get_custom_fields_wordcloud, get_custom_fields_cache
from langchain.vectorstores.azuresearch import AzureSearch
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient,IndexDocumentsBatch
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader, UnstructuredPowerPointLoader, UnstructuredWordDocumentLoader, UnstructuredFileLoader, WebBaseLoader
import pandas as pd
import glob
from configuration.config import *
from log.log import logger
import json
import html
import uuid
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
# from langchain.vectorstores.azuresearch import AzureSearch
# from helpers.cache_helper import get_custom_fields

import nltk
nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger_eng')


# Function to generate unique document IDs and UserIDs
def generate_id():
    return str(uuid.uuid4())

def blob_name_from_file_page(filename):
    return os.path.basename(filename)

def upload_blobs(filename,category_of_docs):
    blob_service = BlobServiceClient.from_connection_string(blob_connect_str)
    blob_container = blob_service.get_container_client(AZURE_STORAGE_CONTAINER)
    if not blob_container.exists():
        blob_container.create_container()

    blob_name = blob_name_from_file_page(filename)
    with open(filename,"rb") as data:
        blob_container.upload_blob(blob_name, data, overwrite=True,metadata={"category":category_of_docs})

def save_text_file(text_path, data, category_of_docs):
    text_list = []
    for content in data:
        text_list.append(content.page_content)

    logger.info(text_path)
    with open(text_path, 'w', encoding='utf-8') as f:
        for line in text_list:
            f.write(f"{line}\n")

    upload_blobs(text_path,category_of_docs)

def load_site_map(base_url):
    response = requests.get(base_url)
    html_content = response.text

    soup = BeautifulSoup(html_content, 'lxml')

    urls = []
    for link in soup.find_all('a'):
        href = link.get('href')
        if href is not None:
            if href.startswith('http'):
                    urls.append(href)
            else:
                urls.append(base_url+href)

    return urls


def ingest_cache(question,metadata):
    if len(question) > 0:
        vectorstore = AzureSearch(
                    azure_search_endpoint=vector_store_address,  # change index by Puneet
                    azure_search_key=vector_store_password,
                    index_name=AZURE_COGNITIVE_SEARCH_INDEX_NAME_ROLE_BASED,
                    embedding_function=embeddings.embed_query,
                    fields=get_custom_fields_cache()
                )
        vectorstore.add_texts(texts=[question], metadatas=[metadata])

def ingest_wordCloud(documents):
    if len(documents) > 0:
        # embeddings = OpenAIEmbeddings(deployment="embedding-model", chunk_size=1, max_retries=10)
        vectorstore = AzureSearch(
                    azure_search_endpoint=vector_store_address,  # change index by Puneet
                    azure_search_key=vector_store_password,
                    index_name=AZURE_COGNITIVE_SEARCH_INDEX_NAME_ROLE_BASED,
                    embedding_function=embeddings.embed_query,
                    fields=get_custom_fields_wordcloud()
                )
        vectorstore.add_documents(documents=documents)

def ingest(documents):
    if len(documents) > 0:
        # embeddings = OpenAIEmbeddings(deployment="embedding-model", chunk_size=1, max_retries=10)
        vectorstore = AzureSearch(
                    azure_search_endpoint=vector_store_address,  # change index by Puneet
                    azure_search_key=vector_store_password,
                    index_name=AZURE_COGNITIVE_SEARCH_INDEX_NAME_ROLE_BASED,
                    embedding_function=embeddings.embed_query,
                    fields=get_custom_fields_normal()
                )
        vectorstore.add_documents(documents=documents)

def upload_to_vectorstore(file_path, category_of_docs, folder_path, categoryName,email):
    print("Entered upload_to_vectorstore METHODc: ")
    print(f"-----category_of_docs ------ {category_of_docs}")
    logger.info(f"-----category_of_docs ------ {category_of_docs}")
    upload_blobs(file_path, category_of_docs)
    file_type = os.path.splitext(file_path)[1].lower()
    allTopic_filtered = []
    logger.info(f"type of file is {file_type}")

    #adding document id and user
    doc_id = generate_id()
    user_name  = email
    doc_name =  os.path.basename(file_path)
    
    def populate_allTopic_filtered(metadata):
        for entry in metadata:
            topic_objects = entry['topics_with_frequency']
            for item in topic_objects:
                topic, count = item.split('||')
                allTopic_filtered.append({'text': topic, 'value': int(count)})
    
    if file_type == ".pdf":
        logger.info("Loading PDF file------------")
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        recursive_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=400)
        texts = recursive_splitter.split_documents(pages)
        if categoryName == "KNOWLEDGE_BOT_WITH_WORDCLOUD":
            extracted_topics = [extract_topic_with_reference(t) for t in texts]
            metadata = []
            for t, topics in zip(texts, extracted_topics):
                t.metadata["source"] = f"{t.metadata['source']}/page-{t.metadata['page']}"
                t.metadata["category"]= category_of_docs
                t.metadata["pageNumber"] = t.metadata['page']
                t.metadata["topics"] = topics['topics']
                t.metadata["topics_with_frequency"] = topics['topics_frequency']
                t.metadata["topics_with_paragraph"] = html.unescape(topics['topics_with_paragraph'])
                t.metadata["doc_id"] = doc_id
                t.metadata["user_name"] = user_name
                t.metadata["acl"] = [user_name]
                # t.doc_id = doc_id
                # t.user_name = user_name
                # t.acl =[user_name]
                
                metadata.append(t.metadata)
            
            print("upload_to_vectorstore -- > allTopic_filtered --> meta --> pdf", metadata)
            populate_allTopic_filtered(metadata)
            ingest_wordCloud(texts)


        else:
            for t in texts:
                print("****************************",t)
                t.metadata["source"] = f"{t.metadata['source']}/page-{t.metadata['page']}"
                t.metadata["category"]= category_of_docs
                t.metadata["doc_id"] = doc_id
                t.metadata["user_name"] = user_name
                t.metadata["acl"] = [user_name]
                # t.doc_id = doc_id
                # t.user_name = user_name
                # t.acl =[user_name]
                # t.doc_id = doc_id

            
            ingest(texts)

    elif file_type == ".pptx":
        print("Loading PowerPoint file------------")
        logger.info("Loading PowerPoint file------------")
        loader = UnstructuredPowerPointLoader(file_path)
        data = loader.load()
        print(f"Data {data}")
        text_path = file_path.replace(".pptx", ".txt").replace(".ppt", ".txt")
        save_text_file(text_path, data, category_of_docs)
        recursive_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=400)
        texts = recursive_splitter.split_documents(data)
        if categoryName == "KNOWLEDGE_BOT_WITH_WORDCLOUD":
            extracted_topics = [extract_topic_with_reference(t) for t in texts]
            metadata = []
            for t, topics in zip(texts, extracted_topics):
                t.metadata["source"] = f"{t.metadata['source']}/page-0"
                t.metadata["category"]= category_of_docs
                t.metadata["pageNumber"] = 0
                t.metadata["topics"] = topics['topics']
                t.metadata["topics_with_frequency"] = topics['topics_frequency']
                t.metadata["topics_with_paragraph"] = html.unescape(topics['topics_with_paragraph'])
                t.metadata["doc_id"] = doc_id
                t.metadata["user_name"] = user_name
                t.metadata["acl"] = [user_name]
                metadata.append(t.metadata)
            
            populate_allTopic_filtered(metadata)
            ingest_wordCloud(texts)

        else:
            for t in texts:
                t.metadata["source"] = f"{t.metadata['source']}/page-0"
                t.metadata["category"]= category_of_docs
                t.metadata["doc_id"] = doc_id
                t.metadata["user_name"] = user_name
                t.metadata["acl"] = [user_name]

            ingest(texts)

    elif file_type == ".docx":
        logger.info("Loading doc file------------")
        loader = UnstructuredWordDocumentLoader(file_path)
        data = loader.load()
        text_path = file_path.replace(".docx", ".txt").replace(".doc", ".txt")
        save_text_file(text_path, data, category_of_docs)
        recursive_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=400)
        texts = recursive_splitter.split_documents(data)
        if categoryName == "KNOWLEDGE_BOT_WITH_WORDCLOUD":
            extracted_topics = [extract_topic_with_reference(t) for t in texts]
            metadata = []
            for t, topics in zip(texts, extracted_topics):
                t.metadata["source"] = f"{t.metadata['source']}/page-0"
                t.metadata["category"]= category_of_docs
                t.metadata["pageNumber"] = 0
                t.metadata["topics"] = topics['topics']
                t.metadata["topics_with_frequency"] = topics['topics_frequency']
                t.metadata["topics_with_paragraph"] = html.unescape(topics['topics_with_paragraph'])
                t.metadata["doc_id"] = doc_id
                t.metadata["user_name"] = user_name
                t.metadata["acl"] = [user_name]
                metadata.append(t.metadata)
            
            populate_allTopic_filtered(metadata)
            ingest_wordCloud(texts)
            
        else:
            for t in texts:
                t.metadata["source"] = f"{t.metadata['source']}/page-0"
                t.metadata["category"]= category_of_docs
                t.metadata["doc_id"] = doc_id
                t.metadata["user_name"] = user_name
                t.metadata["acl"] = [user_name]

            ingest(texts)

    elif file_type == ".txt":
        logger.info("Loading text file------------")
        loader = UnstructuredFileLoader(file_path)
        data = loader.load()
        recursive_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=400)
        texts = recursive_splitter.split_documents(data)
        if categoryName == "KNOWLEDGE_BOT_WITH_WORDCLOUD":
            extracted_topics = [extract_topic_with_reference(t) for t in texts]
            metadata = []
            for t, topics in zip(texts, extracted_topics):
                    t.metadata["source"] = f"{t.metadata['source']}/page-0"
                    t.metadata["category"]= category_of_docs
                    t.metadata["pageNumber"] = 0
                    t.metadata["topics"] = topics['topics']
                    t.metadata["topics_with_frequency"] = topics['topics_frequency']
                    t.metadata["topics_with_paragraph"] = html.unescape(topics['topics_with_paragraph'])
                    t.metadata["doc_id"] = doc_id
                    t.metadata["user_name"] = user_name
                    t.metadata["acl"] = [user_name]
                    
                    metadata.append(t.metadata)
            
            populate_allTopic_filtered(metadata)
            ingest_wordCloud(texts)
           
        else:
            for t in texts:
                print("chunk",t)
                t.metadata["source"] = f"{t.metadata['source']}/page-0"
                t.metadata["category"]= category_of_docs
                t.metadata["doc_id"] = doc_id
                t.metadata["user_name"] = user_name
                t.metadata["acl"] = [user_name]

            ingest(texts)

    elif file_type == ".csv" or file_type == ".xlsx":
        if file_type == ".csv":
            logger.info("Loading CSV file")
            df = pd.read_csv(file_path)
            csv_text = df.to_csv(index=False, sep=",")
        else:
            logger.info("Loading Excel file")
            df = pd.read_excel(file_path, engine="openpyxl")
            csv_text = df.to_csv(index=False, sep=",")
        text_path = file_path.replace(".xlsx", ".txt").replace(".csv", ".txt")
        print(f"  text_path = {text_path}")
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(f"{csv_text}")
        upload_blobs(text_path, category_of_docs)
        loader = UnstructuredFileLoader(text_path)
        data = loader.load()
        recursive_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=400)
        texts = recursive_splitter.split_documents(data)
        print(f" texts = {texts}")
        if categoryName == "KNOWLEDGE_BOT_WITH_WORDCLOUD":
            extracted_topics = [extract_topic_with_reference(t) for t in texts]
            metadata = []
            for t, topics in zip(texts, extracted_topics):
                    print(f"t.metadata = {t.metadata}")
                    t.metadata["source"] = f"{t.metadata['source']}/page-0"
                    t.metadata["category"]= category_of_docs
                    t.metadata["pageNumber"] = 0
                    t.metadata["topics"] = topics['topics']
                    t.metadata["topics_with_frequency"] = topics['topics_frequency']
                    t.metadata["topics_with_paragraph"] = html.unescape(topics['topics_with_paragraph'])
                    t.metadata["doc_id"] = doc_id
                    t.metadata["user_name"] = user_name
                    t.metadata["acl"] = [user_name]
                    metadata.append(t.metadata)

            populate_allTopic_filtered(metadata)    
            ingest_wordCloud(texts)

        else:
            for t in texts:
                t.metadata["source"] = f"{t.metadata['source']}/page-0"
                t.metadata["category"]= category_of_docs
                t.metadata["doc_id"] = doc_id
                t.metadata["user_name"] = user_name
                t.metadata["acl"] = [user_name]

            ingest(texts)

    else:
        pass
    
    #adding information into database (added by Puneet)
    acl_name = f'["{user_name}"]'
    conn = SQLOperation('KnowledgeBotDB').get_connection()
    cursor = conn.cursor()
    print(doc_id, user_name, doc_name, "ACTIVE", user_name)
    cursor.execute('''INSERT INTO RoleBasedDocuments (doc_id, user_name, doc_name, status, updated_by,acl) 
    VALUES (%s, %s, %s, %s, %s,%s)''', 
    (doc_id, user_name, doc_name, "ACTIVE", user_name,acl_name))
    conn.commit()
    cursor.close()
    conn.close()

    print("DATA INSERTION COMPLETED IN database")

    print("upload_to_vectorstore -- > allTopic_filtered", allTopic_filtered)

    return allTopic_filtered


def get_unique_urls(all_urls):
    unique_urls = set()

    for url in all_urls:
        parsed_url = urlparse(url)._replace(fragment='')
        unique_urls.add(parsed_url.geturl())

    return list(unique_urls)


def upload_url_to_vectorstore(base_url,category_of_docs, categoryName,email):
    doc_id = generate_id() # generating document id , later on will use in vector database
    user_name = email
    doc_name = base_url

    all_urls = get_unique_urls(list(set(load_site_map(base_url))))
    allTopic_filtered = []

    def populate_allTopic_filtered(metadata):
        for entry in metadata:
            topic_objects = entry['topics_with_frequency']
            for item in topic_objects:
                topic, count = item.split('||')
                allTopic_filtered.append({'text': topic, 'value': int(count)})

    for site in all_urls:
        logger.info(site)
        logger.info("="*15)
        loader = WebBaseLoader(site)
        data = loader.load()
        # logger.info(data)
        recursive_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=400)
        texts = recursive_splitter.split_documents(data)
        if(categoryName=="KNOWLEDGE_BOT_WITH_WORDCLOUD"):
            
            extracted_topics = [extract_topic_with_reference(t) for t in texts]
            metadata = []
            for t, topics in zip(texts, extracted_topics):
                    t.metadata["source"] = f"{t.metadata['source']}/page-{t.metadata['page']}"
                    t.metadata["category"]= category_of_docs
                    t.metadata["pageNumber"] = t.metadata['page']
                    t.metadata["topics"] = topics['topics']
                    t.metadata["topics_with_frequency"] = topics['topics_frequency']
                    t.metadata["topics_with_paragraph"] = html.unescape(topics['topics_with_paragraph'])
                    t.metadata["doc_id"] = doc_id
                    t.metadata["user_name"] = user_name
                    t.metadata["acl"] = [user_name]
                    metadata.append(t.metadata)

            populate_allTopic_filtered(metadata)    
            ingest_wordCloud(texts)

        else:
            for t in texts:
                t.metadata["source"] = f"{t.metadata['source']}/page-{t.metadata['page']}"
                t.metadata["category"]= category_of_docs
                t.metadata["doc_id"] = doc_id
                t.metadata["user_name"] = user_name
                t.metadata["acl"] = [user_name]

            ingest(texts)
    #adding information into database (added by Puneet)
    conn = SQLOperation('KnowledgeBotDB').get_connection()
    cursor = conn.cursor()
    print(doc_id, user_name, doc_name, "ACTIVE", user_name)
    cursor.execute('''INSERT INTO RoleBasedDocuments (doc_id, user_name, doc_name, status, updated_by) 
                  VALUES (%s, %s, %s, %s, %s)''', 
               (doc_id, user_name, doc_name, "ACTIVE", user_name))
    conn.commit()
    cursor.close()
    conn.close()

    print("DATA INSERTION COMPLETED IN database")

    return allTopic_filtered
        
def remove_blobs(metadata):
    blob_service = BlobServiceClient.from_connection_string(blob_connect_str)
    blob_container = blob_service.get_container_client(AZURE_STORAGE_CONTAINER)
    if blob_container.exists():
        blob_list = blob_container.list_blobs()
        for blob in blob_list:
            blob_client = blob_container.get_blob_client(blob.name)
            blob_props = blob_client.get_blob_properties()
            blob_category = blob_props.metadata.get("category", "")
            if blob_category == metadata["category"]:
                logger.info(f"\tRemoving blob {blob.name}")
                blob_container.delete_blob(blob.name)
                
def delete_documents_cache(client, bot_type):
    filter_query = f"category eq '{AZURE_ENV_NAME}_{bot_type}_cache' and type eq 'cache'"

    logger.info(f"Deleting documents with filter: {filter_query}")

    results = client.search(search_text="*", filter=filter_query, top=40)
    delete_ids = []
    for result in results:
        delete_ids.append({"id": result["id"]})
    logger.info(f"Deleting document with ID: {delete_ids}")
    client.delete_documents(delete_ids)
    
# def delete_documents(client, bot_type):
#     filter_query = f"category eq '{AZURE_ENV_NAME}_{bot_type}'"

#     logger.info(f"Deleting documents with filter: {filter_query}")

#     results = client.search(search_text="*", filter=filter_query, top=40)
#     delete_ids = []
#     for result in results:
#         delete_ids.append({"id": result["id"]})
#     logger.info(f"Deleting document with ID: {delete_ids}")
#     if len(delete_ids) > 0:
#         client.delete_documents(delete_ids)

def delete_documents_withdocid(doc_id):
    client = SearchClient(
        endpoint=vector_store_address,
        index_name=AZURE_COGNITIVE_SEARCH_INDEX_NAME_ROLE_BASED,
        credential=AzureKeyCredential(vector_store_password)
    )
    filter_query = f"doc_id eq '{doc_id}'"

    logger.info(f"Deleting documents with filter: {filter_query}")

    results = client.search(search_text="*", filter=filter_query, top=40)
    print("id results",results)
    delete_ids = []
    for result in results:
        delete_ids.append({"id": result["id"]})
    logger.info(f"Deleting document with ID: {delete_ids}")
    client.delete_documents(delete_ids)
    
def delete_documents(client, bot_type):
    filter_query = f"category eq '{AZURE_ENV_NAME}_{bot_type}'"

    logger.info(f"Deleting documents with filter: {filter_query}")

    results = client.search(search_text="*", filter=filter_query, top=40)
    delete_ids = []
    for result in results:
        delete_ids.append({"id": result["id"]})
    logger.info(f"Deleting document with ID: {delete_ids}")
    if len(delete_ids) > 0:
        client.delete_documents(delete_ids)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_FILE_EXTENSIONS

def upload_data(data_path,category,folder_path, categoryName,email):
    print("Entered upload_data method")
    print(data_path,category,folder_path, categoryName)
    topicsExtracted = []
    for filename in glob.glob(data_path):
        print(f"Processing '{filename}'")
        logger.info(f"Processing '{filename}'")
        print(f"-------agrs_category ------ {category}")
        logger.info(f"-------agrs_category ------ {category}")
        category_of_docs = category
        topicsExtracted= upload_to_vectorstore(filename, category_of_docs,folder_path,categoryName,email)
    return topicsExtracted


def extract_topic_with_reference(topicData):
    textEndd = topicData.page_content
    
    prompt_format="Create a unified array of objects with key of array as 'topics' that includes the top 10 main topics, their respective frequencies within the entire page content, and the entire paragraphs where these topics are found. Each object in the array should contain three properties: 'topic' representing the main topic which should not be more than 3 words, 'frequency' denoting its occurrence frequency, and 'paragraph' providing the entire paragraph where the topic appears. Ensure the response is presented in JSON format, and the paragraph text doesn't contain double quotes and that the extraction process is applicable to any uploaded document. Also ensure that 'paragraph' never contains multiple elements and it is never a list. Please generate the response as a dictionary class and do not add python code in the response."
    
    prompt_template = f"""<|im_start|>
        {textEndd}
        {prompt_format}
        <|im_end|>
        """
    response = openai.ChatCompletion.create(
            engine=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
            prompt=prompt_template,
            temperature=0,
            max_tokens=4096,
            n=1,
            stop=["<|im_end|>", "<|im_start|>"]
        )
    
    topic_dict = response.choices[0].text
    print("*"*25)
    print("extract_topic_with_reference" , topic_dict)
    print("*"*25)
    logger.info(f"topic_dict: {topic_dict}")
    topic_dict = json.loads(topic_dict)
    
    topics =[]
    frequency_list = []
    topic_paragraph_list = []

    for item in topic_dict['topics']:
        topic_paragraph_list.append(f"{item['topic']}||{item['paragraph']}")
        topics.append(item['topic'])
        frequency_list.append(f"{item['topic']}||{item['frequency']}")
        

    result = '|||'.join(topic_paragraph_list)
    return {"topics":topics, "topics_frequency": frequency_list, "topics_with_paragraph":html.unescape(result)}

def extract_paragraph(topic_with_paragraph, user_input):
    sections = topic_with_paragraph.split("|||")
    result = [section.split("||") for section in sections]
    filtered_data = [item for item in result if user_input in  item[0]]
    if filtered_data:
     return filtered_data[0][1]
    else:
     return ""

def get_similar_embeddings(user_input,user_email):
    user_name = user_email
    vectorstore = AzureSearch(
                    azure_search_endpoint=vector_store_address,  # change index by Puneet
                    azure_search_key=vector_store_password,
                    index_name=AZURE_COGNITIVE_SEARCH_INDEX_NAME_ROLE_BASED,
                    embedding_function=embeddings.embed_query,
                    fields=get_custom_fields_wordcloud()
                )
    filters = f"topics/any(t: t eq '{user_name}') " #changes by Puneet , '{user_name}' , and user_name eq '{user_name}'
    query_results = vectorstore.similarity_search_with_relevance_scores(user_input, k=5, filters=filters)

    response_data = []
    if query_results is not None:
        id = 1
        for item in query_results:
            if item[1] > 0.7:
                metadata = item[0].metadata
                result_item = {
                    'id': id,
                    'score': item[1],
                    'metadata': {
                        'Category': metadata.get('category', ''),
                        'Topic': metadata.get('topics', ''),
                        'Summary': item[0].page_content,
                        'filename': metadata.get('source', ''),
                        'topic_with_paragraph': extract_paragraph(metadata.get('topics_with_paragraph', ''), user_input),
                    }
                }
                response_data.append(result_item)
            id += 1

    return response_data

