from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores.azuresearch import AzureSearch
from helpers.data_management import ingest_cache
from helpers.utils import get_custom_fields_cache
import openai
import os
from typing import List
import numpy as np
import time
from datetime import datetime
import re
from pathlib import Path
from log.log import logger
from configuration.config import *
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SimpleField
)

import sys
sys.path.append("..")
from db import SQLOperation

Config={
    # "indexName": "gpt-data-index",
    "type":"cache",
    # "category":"cache_envname",
    "top_k":1
}

# OpenAIEmbeddings
embeddings = OpenAIEmbeddings(engine=AZURE_OPENAI_EMBEDDING_DEPLOYMENT, chunk_size=1)

def vectorstore_search(question,bot_type):
    user_name = 'sharma_pu@xoriant.com'
    vectorstore = AzureSearch(
                        azure_search_endpoint=vector_store_address,
                        azure_search_key=vector_store_password,
                        index_name=AZURE_COGNITIVE_SEARCH_CACHE_INDEX_NAME,
                        embedding_function=embeddings.embed_query,          
                        fields=get_custom_fields_cache()
                    )
    # similar_doc = vectorstore.similarity_search_with_relevance_scores(question, k=Config["top_k"], filter={"type":Config["type"],"category":AZURE_ENV_NAME+"_"+bot_type+"_cache"})
    category = AZURE_ENV_NAME+"_"+bot_type+"_cache"
    config_type = Config["type"]

    #change by Puneet
    similar_doc = vectorstore.similarity_search_with_relevance_scores(question, k=Config["top_k"], filters=f"type eq '{config_type}' and acl/any(t: t eq '{user_name}' and category eq '{category}'")
    # similar_doc=docsearch.similarity_search_with_score(question, k=Config["top_k"],filter={"type":Config["type"],"category":AZURE_ENV_NAME+"_"+bot_type+"_cache"})

    if similar_doc:
        similarity_score=similar_doc[0][1]
        # for src in similar_doc:
        #     similarity_score=src[1]
        
        if similarity_score>0.95:
            matched_question=similar_doc[0][0].page_content
            matched_id=int(similar_doc[0][0].metadata['question_id'])
            logger.info(f"---Matched question : {matched_question}")
            print("---Matched question : ",matched_question)
            return (matched_id,matched_question,similarity_score)
        
        else:
            logger.info(f"---similarity_score below threshold : {similarity_score}" )
            logger.info(f"---Most similar question with low similarity score : {similar_doc[0][0].page_content}")
            print("---similarity_score below threshold : ",similarity_score )
            print("---Most similar question with low similarity score : ",similar_doc[0][0].page_content)            
        
    return None

def get_question_id():
    conn = SQLOperation('KnowledgeBotDB').get_connection()
    cursor = conn.cursor()
    result = cursor.execute("select max(id) from dbo.vectorstore_cache")
    question_id = result.fetchone()[0]
    cursor.close()
    conn.close()
    print("Question id: {}".format(question_id))
    return question_id

# Function to insert a new question and answer into the cache
def insert_to_cache(rephrased_question,answer,bot_type):
    try:
        rephrased_question=rephrased_question.lower()
        datetime_now = datetime.now()
        conn = SQLOperation('KnowledgeBotDB').get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO vectorstore_cache (question, answer, Timestamp, category) VALUES (?, ?, ?, ?)", (rephrased_question, answer, datetime_now,AZURE_ENV_NAME+"_"+bot_type+"_cache"))
        conn.commit()
        cursor.close()
        conn.close()
        question_id = get_question_id()
        metadata={"type":Config["type"],"category":AZURE_ENV_NAME+"_"+bot_type +"_cache","question_id":question_id}
        ingest_cache(rephrased_question, metadata)
    except Exception as e:
        print(str(e))

# Function to retrieve an answer from the cache based on similarity
def retrieve_from_cache(question,bot_type):
    question=question.lower()
    logger.info(f"---REPHRASED QUESTION: {question}")

    print("---REPHRASED QUESTION: ",question)
    results=vectorstore_search(question,bot_type)
    
    if results :
        (matched_id,matched_question,similarity_score)=results
        conn = SQLOperation('KnowledgeBotDB').get_connection()
        cursor = conn.cursor()
#         print("matched_id ",matched_id, int(matched_id))
        cursor.execute("SELECT question, answer FROM vectorstore_cache WHERE id=?", (int(matched_id),))
        record = cursor.fetchone()
        cursor.close()
#         print("Record from Sqlite : ",record)
        if record:
            logger.info(f"---similarity_score : {similarity_score}")
            print("---similarity_score : ",similarity_score)
            prev_question, prev_answer = record
            return prev_answer

    return None