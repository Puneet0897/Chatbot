import os
import mimetypes
import time
from time import sleep
import logging
from log.log import logger
import shutil
import base64
from fastapi.responses import JSONResponse
import json
import uvicorn
from typing import List
import traceback
from fastapi import HTTPException
import asyncio
from io import BytesIO
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import PyPDF2
import sys
from flask import Flask, request, jsonify
# from azure.identity import DefaultAzureCredential
from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from azure.storage.blob import BlobServiceClient
import pandas as pd
from db import extract_db_schema,SQLOperation
from configuration.config import *
from helpers.data_management import *
from pred_analysis import *
from http import HTTPStatus
from azure_ocr import ocr_ASLogger as log
from sales_recommendation.sales_recommendation import get_email, get_farmer_profile, get_product, search_documents
from azure_ocr.ocr_functions import get_ocr_text, final_response, format_final_response
from persona_summary import run_persona_summary
from callcenter_analytics.utils import convert_audio_to_text, analyse_transcript
from Trading.trade import TradingBot
from azure_ocr.ocr_AzureDocumentAi import analyze_general_documents
from approaches.respondreadentity import respond_react
from langchain.vectorstores.azuresearch import AzureSearch
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request


with open('configuration/config_entity_extraction.json') as f:
    config = json.load(f)

blob_client = BlobServiceClient.from_connection_string(blob_connect_str)
blob_container = blob_client.get_container_client(AZURE_STORAGE_CONTAINER)


chat_approaches = { 
    "rrr": ChatReadRetrieveReadApproach()
}

# extract db schema
db_schema, conn = extract_db_schema()


app = FastAPI()

# CORS middleware (optional, depending on your needs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to restrict allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# @app.get("/")
# async def root():
#     return {"message": "Welcome to the FastAPI application"}


@app.post("/ask")
async def ask(request: Request):
    try:
        # Extract JSON data asynchronously
        json_data = await request.json()
        bot_type = json_data.get("bot_type")
        logger.info(f"Ask bot type {bot_type}")
        filename = json_data.get("filename")
        logger.info(f"PYTHON ASK-> {filename}")

        # Check for chat approach implementation
        impl = chat_approaches.get("rrr")
        if not impl:
            return JSONResponse(content={"error": "unknown approach"}, status_code=400)

        # Download the blob from Azure
        blob = blob_container.get_blob_client(filename).download_blob()
        file_type = os.path.splitext(filename)[1].lower()

        # Handle text file
        if file_type == ".txt":
            blob_data = blob.readall().decode('utf-8')

        # Handle PDF file
        elif file_type == ".pdf":
            pages = []
            blob_to_read = BytesIO(blob.readall())
            pdf_reader = PyPDF2.PdfReader(blob_to_read)
            for page in pdf_reader.pages:
                pages.append(page.extract_text())
            blob_data = " ".join(pages)

        # Run the chat approach implementation
        r = impl.ask_run(blob_data, bot_type)
        return JSONResponse(content=r)

    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(stack_trace)
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/persona_summary")
async def persona_summary(request: Request):
    try:
        # Extract JSON data asynchronously
        json_data = await request.json()
        bot_type = json_data.get("bot_type")
        filename = json_data.get("filename")
        
        # Download the blob from Azure
        blob = blob_container.get_blob_client(filename).download_blob()
        file_type = os.path.splitext(filename)[1].lower()

        # Handle text file
        if file_type == ".txt":
            blob_data = blob.readall().decode('utf-8')

        # Handle PDF file
        elif file_type == ".pdf":
            pages = []
            blob_to_read = BytesIO(blob.readall())
            pdf_reader = PyPDF2.PdfReader(blob_to_read)
            for page in pdf_reader.pages:
                pages.append(page.extract_text())
            blob_data = " ".join(pages)

        # Call the persona summary processing function
        r = run_persona_summary(blob_data, bot_type)
        return JSONResponse(content=r)

    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(stack_trace)
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/get_cpu_utilization")
async def cpu_utilization(request: Request):
    try:
        json_data = await request.json()
        start_date = json_data["startDate"]
        end_date = json_data["endDate"]

        start_date += ' 00:00:00'
        end_date += ' 00:00:00'

        logger.info(f"start_date is {start_date}, end_date is {end_date}")

        df = pd.read_csv(r'predictive_analysis/CPU_Data.csv')
        df['Datetime'] = pd.to_datetime(df['Datetime'])
        predictions, df = forecast_range(df, start_date, end_date)
        timestamps = [timestamp for timestamp, _ in predictions]
        cpu_util = [prediction for _, prediction in predictions]
        buffer = get_graph_image(timestamps, cpu_util)
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        data_uri = 'data:image/png;base64,' + image_data

        return JSONResponse({
            "data_uri": data_uri
        })
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(stack_trace)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/fetch_topics")
async def fetch_topics(request: Request):
    try:
        json_data = await request.json()
        user_query = json_data['query_text']
        result = get_similar_embeddings(user_query)
        return JSONResponse(result)
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(stack_trace)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/entity_extraction")
def entity_extraction(file_data: UploadFile = File(...), doc_type: str = Form(...)):
    logger.info('Main module Initialized.')
    st_time = time.time()
    try:
        logger.info(st_time)

        if not file_data:
            raise HTTPException(status_code=400, detail='Could not upload the file for extraction')

        if doc_type == 'template_free':
            output_response = analyze_general_documents(file_data)
            return JSONResponse(output_response)
        else:
            ocr_text = get_ocr_text(file_data)
            response, key_value_response = final_response(doc_type, config, ocr_text)
            formatted_final_response = format_final_response(response, key_value_response)
            logger.info(f"Total Time is : {time.time() - st_time}")
            return JSONResponse(formatted_final_response)
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(stack_trace)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(request: Request):
    try:
        json_data = await request.json()
        approach = json_data["approach"]
        bot_type = json_data["bot_type"]

        impl = chat_approaches.get(approach)
        if not impl:
            raise HTTPException(status_code=400, detail="unknown approach")
        r = impl.run(json_data["history"], json_data["overrides"] or {}, AZURE_ENV_NAME, db_schema, conn, bot_type)
        return JSONResponse(r)
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(stack_trace)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload(bot_type: str = Form(...), files: List[UploadFile] = File(None), urls: str = Form(None)):
    try:
        if bot_type == "KNOWLEDGE_BOT_WITH_CACHE":
            bot_type = "KNOWLEDGE_BOT"

        logger.info(f"Uploading bot type {bot_type}")
        isdelete = False
        folder_name = str(int(time.time()))
        folder_path = os.path.join(UPLOAD_FOLDER, folder_name)
        urls_data = urls.split(";") if urls else []

        if not files and not urls_data:
            raise HTTPException(status_code=400, detail='No file provided')

        for file in files:
            logger.info(f"Uploading file {file.filename} to {folder_name}")
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            isdelete = True
            file_path = os.path.join(folder_path, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

        final_path = folder_path + "/*"
        extracted_topics = upload_data(final_path, AZURE_ENV_NAME + "_" + bot_type, folder_path, bot_type)

        if urls_data:
            logger.info(f"URLs are: {urls_data}")
            for url in urls_data:
                extracted_topics = upload_url_to_vectorstore(url, AZURE_ENV_NAME + "_" + bot_type)

        if isdelete:
            shutil.rmtree(folder_path)
        
        return {"success": True, "topics": extracted_topics}
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(stack_trace)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/delete/{bot_type}")
async def delete_vectorstore_index(bot_type: str):
    try:
        if bot_type == "KNOWLEDGE_BOT_WITH_CACHE":
            bot_type = "KNOWLEDGE_BOT"
            cache_search_client = SearchClient(
                endpoint=vector_store_address,
                index_name=AZURE_COGNITIVE_SEARCH_CACHE_INDEX_NAME,
                credential=AzureKeyCredential(vector_store_password)
            )
            delete_documents_cache(cache_search_client, bot_type)

        search_client = SearchClient(
            endpoint=vector_store_address,
            index_name=AZURE_COGNITIVE_SEARCH_INDEX_NAME_ROLE_BASED,
            credential=AzureKeyCredential(vector_store_password)
        )
        delete_documents(search_client, bot_type)
        remove_blobs(metadata={"category": AZURE_ENV_NAME + "_" + bot_type})

        return {"success": True}
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(stack_trace)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_files/{bot_type}")
async def get_files(bot_type: str):
    try:
        blob_list = blob_container.list_blobs()
        blob_files = []
        for blob in blob_list:
            blob_client = blob_container.get_blob_client(blob.name)
            blob_props = blob_client.get_blob_properties()
            blob_category = blob_props.metadata.get("category", "")
            if blob_category == (AZURE_ENV_NAME + "_" + bot_type):
                blob_files.append(blob.name)
        logger.info(blob_files)

        return JSONResponse({
            'data': blob_files
        })
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(stack_trace)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get_profile")
async def get_profile(request: Request):
    try:
        json_data = await request.json()
        farmer_id = json_data["cus_id"]
        logger.info(farmer_id)
        profile = get_farmer_profile(farmer_id)
        return JSONResponse(profile)
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(stack_trace)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sales_recommendation")
async def sales_recommendation(request: Request):
    try:
        data = await request.json()
        problems = data["problem_input"]
        filtered_results = search_documents(AZURE_ENV_NAME, problems)
        product_recommended = get_product(filtered_results, problems)
        recommendation_email = get_email(filtered_results, problems)

        result = json.loads(product_recommended)
        result["email"] = recommendation_email
        logger.info(f"Sales recommendation generated: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in sales_recommendation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/analyse_transcript')
async def analyse_trans(request: Request):
    try:
        file_name_to_analyse = os.path.join('static', request.body.decode())
        analytics_response = analyse_transcript(file_name_to_analyse)
        logger.info(f"Transcript analysis completed for: {file_name_to_analyse}")
        return JSONResponse(content=analytics_response)
    except Exception as e:
        logger.error(f"Error in analyse_transcript: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/transcribe')
async def transcribe_audio(request: Request):
    try:
        file_name_to_transcribe = request.body.decode()
        output_file = os.path.join('static', f"{file_name_to_transcribe.split('.')[0]}.txt")

        if not os.path.exists(output_file):
            convert_audio_to_text(file_name_to_transcribe, output_file)
            logger.info(f"Transcribed audio file: {file_name_to_transcribe}")
        else:
            logger.info(f"Output file {output_file} already exists, skipping conversion.")
            sleep(5)

        return JSONResponse(content={'status': 'Transcribed'})
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/uploadAudio')
async def upload_audio(request: Request):
    try:
        if 'audioFile' not in request.files:
            raise HTTPException(status_code=400, detail='No audio files provided')

        audio_files = request.files.getlist('audioFile')
        filenames = []

        for audio_file in audio_files:
            if audio_file.filename == '':
                raise HTTPException(status_code=400, detail='Invalid audio file')

            save_path = os.path.join('static', audio_file.filename)
            audio_file.save(save_path)
            filenames.append(audio_file.filename)
            logger.info(f"Uploaded audio file: {audio_file.filename}")

        return JSONResponse(content={'message': 'Audio files uploaded successfully', 'filenames': filenames})
    except Exception as e:
        logger.error(f"Error in uploadAudio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trade")
async def trade(request: Request):
    data = await request.json()
    trading_bot = TradingBot()
    response = trading_bot.process_query(data["history"][0]['user'])
    logger.info(f"Trade query processed: {data['history'][0]['user']}")
    return JSONResponse(content=response)

@app.post("/get_trader_info")
async def get_trader_info():
    trading_bot = TradingBot()
    account_info = trading_bot.get_account_info()
    logger.info("Fetched trader account information.")
    return JSONResponse(content=account_info)

@app.post("/get_trader_assets")
async def get_trader_assets():
    trading_bot = TradingBot()
    trader_assets = trading_bot.get_user_stock_info()
    logger.info("Fetched trader assets.")
    return JSONResponse(content=trader_assets)

@app.post("/get_trader_recent_orders")
async def get_trader_recent_orders():
    trading_bot = TradingBot()
    trader_recent_orders = trading_bot.get_recent_orders()
    logger.info("Fetched trader recent orders.")
    return JSONResponse(content=trader_recent_orders)

@app.post('/portfolio')
async def get_portfolio_data():
    trading_bot = TradingBot()
    portfolio_data = await trading_bot.get_portfolio()  # Call the async method
    logger.info("Fetched portfolio data.")
    return JSONResponse(content=portfolio_data) 

@app.post('/find_entity')
async def get_find_entity(request: Request):
    try:
        data = await request.json()
        key_values = data["keyValues"]
        entities_data = data["entities_data"]
        question = data["question"]
        response = respond_react(key_values, entities_data, question)
        logger.info(f"Entity found for question: {question}")
        return JSONResponse(content={'answer': response})
    except Exception as e:
        logger.error(f"Error in find_entity: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))  


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

