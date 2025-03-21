from langchain.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document
from langchain.llms import AzureOpenAI
from langchain.chat_models import ChatOpenAI
import os, re
from pathlib import Path
import openai
import json


def respond_react(keyValues,text,user_question):
    api_type = "azure"
    api_version = "2022-12-01"
    api_key = "5713a9f9be2e4c1a853d82e784676e66"
    api_base = "https://openaismartchatgpt.openai.azure.com/"

    openai.api_type = api_type
    openai.api_base = api_base
    openai.api_version = api_version
    openai.api_key = api_key

    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_API_VERSION"] = api_version

    prompt = f"""<|im_start|>system
    You are an assistant for retrieving information about reporting requirements for holding companies with foreign offices and answer the questions asked by the user,by precisely following the instructions given.\
    The document contains keyvalue pair and table, below is the format of table:\n
    Each row is separated by a new line, and cells within a row are separated by the '|' character. Rows are enclosed in '+' and '-' characters for borders. Ensure that the first row represents the table header, and the remaining rows contain data.
    Example Question and Response:
    Question: What is the effective starting date for edit no xxxx ?
    Response: yyyy
    
    Source:
    {keyValues, text}

    Question:
    {user_question}

    Response:
    <|im_end|>
    """
    


    # prompt = f"""<|im_start|>system
    # Generate concise Responses based on the extracted entities from the Source. 
    # Please provide Response in plain text format corresponding to the identified entities. 
    # Do not generate a response if the entities are not present in the extracted list.
    
    # Source:
    # {text}

    # Question:
    # {user_question}

    # Response:
    # <|im_end|>
    # """

    print("="*25)
    print("Prompt: \n",prompt)
    print("="*25)

    completion = openai.ChatCompletion.create(
    engine="container-poc-gpt4mini-model", 
    prompt=prompt, 
    temperature=0.2, 
    max_tokens=1024,
    stop=["<|im_end|>", "<|im_start|>","<|im_sep|>"])

    search = completion.choices[0].text 

    print("="*25)
    print("LLM Response: \n",search)
    print("="*25)

    result = ""

    if "Question:" in search:
      regex = r"Question:\n\s+.*\s*Response:\n\s*.*"
      subst = ""

      result = re.sub(regex, subst, search, 0, re.MULTILINE)
      result = re.sub(r"\s*", subst, result, 0, re.MULTILINE)

      print("="*25)
      print("Post Processing :", result)
      print("="*25)
    else:
      print("="*25)
      result = search
      print("Original Answer", search)
      print("="*25)

    return result

