import openai
import os
from azure.storage.blob import BlobServiceClient
from langchain.embeddings import OpenAIEmbeddings
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SimpleField
)
from azure.identity import DefaultAzureCredential
from configuration.config import AZURE_OPENAI_EMBEDDING_DEPLOYMENT

def get_custom_fields_cache():
    embeddings = OpenAIEmbeddings(engine=AZURE_OPENAI_EMBEDDING_DEPLOYMENT, chunk_size=1, max_retries=10)
    embedding_function = embeddings.embed_query

    cache_fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SimpleField(
            name="doc_id",
            type=SearchFieldDataType.String,
            filterable=True,
            searchable=True,
        ),
        SimpleField(
            name="user_name",
            type=SearchFieldDataType.String,
            filterable=True,
            searchable=True,
        ),
        SimpleField(
            name="acl",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String), 
            filterable=True,
            searchable=True
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=len(embedding_function("Text")),
            vector_search_configuration="default",
        ),
        SearchableField(
            name="metadata",
            type=SearchFieldDataType.String,
            searchable=True,
        ),
        SearchField(
            name="type",
            type=SearchFieldDataType.String,
            filterable=True,
            searchable=True
        ),
        SimpleField(
            name="category",
            type=SearchFieldDataType.String,
            filterable=True,
            searchable=True
        ),
        SimpleField(
            name="question_id",
            type=SearchFieldDataType.Int32,
            filterable=True,
            searchable=True
        )
    ]
    
    return cache_fields

def get_custom_fields_wordcloud():

    fields = get_custom_fields_normal()
    fields.extend(get_custom_fields_extra())
    
    return fields 

def get_custom_fields_normal():

    embeddings = OpenAIEmbeddings(engine=AZURE_OPENAI_EMBEDDING_DEPLOYMENT, chunk_size=1, max_retries=10)
    embedding_function = embeddings.embed_query

    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SimpleField(
            name="doc_id",
            type=SearchFieldDataType.String,
            filterable=True,
            searchable=True,
        ),
        SimpleField(
            name="user_name",
            type=SearchFieldDataType.String,
            filterable=True,
            searchable=True,
        ),
        SimpleField(
            name="acl",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String), 
            filterable=True,
            searchable=True
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=len(embedding_function("Text")),
            vector_search_configuration="default",
        ),
        SearchableField(
            name="metadata",
            type=SearchFieldDataType.String,
            searchable=True,
        ),
        SimpleField(
            name="source",
            type=SearchFieldDataType.String,
            filterable=True,
            searchable=True
        ),
        SimpleField(
            name="category",
            type=SearchFieldDataType.String,
            filterable=True,
            searchable=True
        )
    ]

    return fields

def get_custom_fields_extra():

    fields_wordcloud = [
        
        SimpleField(
            name="pageNumber",
            type=SearchFieldDataType.Int32,
            filterable=True,
            searchable=True
        ),
        SimpleField(
            name="topics",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String), 
            filterable=True,
            searchable=True
        ),
        SimpleField(
            name="topics_with_frequency",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            searchable=True
        ),
        SimpleField(
            name="topics_with_paragraph",
            type=SearchFieldDataType.String,
            filterable=True,
            searchable=True
        )
    ]

    return fields_wordcloud