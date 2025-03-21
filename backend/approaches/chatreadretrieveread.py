import openai
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from approaches.approach import Approach
from text import nonewlines
from helpers.utils import get_custom_fields_normal, get_custom_fields_wordcloud
import os, time
import re, datetime, random
from helpers.chat import *
from configuration.prompts_chat_config import *
from configuration.config import *
import asyncio
from helpers.cache_helper import insert_to_cache, retrieve_from_cache
from log.log import logger
from langchain.vectorstores.azuresearch import AzureSearch
# from azure_ocr import ocr_ASLogger as log

class ChatReadRetrieveReadApproach(Approach):

    def __init__(self):

        self.set_of_que = None
        self.que_num = -1
        self.prev_intent = None
        self.positive = 0
        self.negative = 0
        self.negative_questions = []


    def run(self, history: list[dict], overrides: dict,AZURE_ENV_NAME,db_schema, conn, bot_type,user_email) -> any:
        user_name = user_email
        logger.info(f"Question asked:{ history[-1]['user']}")
        AZURE_ENV_NAME = AZURE_ENV_NAME + "_" + bot_type
        if bot_type == "FAQ" or bot_type == "POLICY" or bot_type == "KNOWLEDGE_BOT" or bot_type == "KNOWLEDGE_BOT_WITH_CACHE":
            logger.info(f"UI - {bot_type} Selected - FAQ")
            config = FAQ_config

        if bot_type == "SECURITY":
            logger.info(f"UI - {bot_type} Selected - SECURITY")
            config = Security_config


        top = config["top"]
        pinecone_threshold = config["pinecone_threshold"]
        include_all_sources = config["include_all_sources"]

        query_prompt = config["query_prompt_template"].format(
        chat_history=get_chat_history_as_text(history, include_last_turn=False), question=history[-1]["user"])
        start_time=time.time()
        rephrased_question = openai_completion(
            deployment_name=config["query_model"],
            prompt=query_prompt,
            temperature=config["query_temperature"],
            max_tokens=config["query_max_tokens"],
            n=config["query_n"],
            stop=config["query_stop"]).replace("<|im_end|>","")

        print("openai_completion rephrased_question",rephrased_question)
        print(f"Time consumed for rephrased_question: {time.time() - start_time}s")
        # log.logger.info("Time consumed for rephrased_question: {:.2f}s".format(time.time() - start_time))

        # logger.info("=" * 10)
        # ================================CACHE=======================================================
        if(bot_type=="KNOWLEDGE_BOT_WITH_CACHE"):
            start_time=time.time()
            answer_from_cache=retrieve_from_cache(rephrased_question,bot_type)
            # AZURE_ENV_NAME=AZURE_ENV_NAME+"_KNOWLEDGE_BOT"
            AZURE_ENV_NAME=AZURE_ENV_NAME[:-11]
            if(answer_from_cache):
                print("Time consuming answer: {:.2f}s".format(time.time() - start_time))
                print('\033[1m Answer from cache: \033[0m')
                # log.logger.info("Time consuming answer: {:.2f}s".format(time.time() - start_time))
                logger.info('Answer from cache: ')
                # return answer_from_cache
                return {"data_points": [], "answer": answer_from_cache,
                        "thoughts": f"Coming soon!!"}
 
        if(bot_type=="KNOWLEDGE_BOT_WITH_WORDCLOUD"):
            doc_search = AzureSearch(
                        azure_search_endpoint=vector_store_address,
                        azure_search_key=vector_store_password,
                        index_name=AZURE_COGNITIVE_SEARCH_INDEX_NAME_ROLE_BASED,
                        embedding_function=embeddings.embed_query,
                        fields=get_custom_fields_wordcloud()
                    )
        else:
            doc_search = AzureSearch(
                        azure_search_endpoint=vector_store_address,
                        azure_search_key=vector_store_password,
                        index_name=AZURE_COGNITIVE_SEARCH_INDEX_NAME_ROLE_BASED,
                        embedding_function=embeddings.embed_query,
                        fields=get_custom_fields_normal()
                    )
        filters=f"category eq '{AZURE_ENV_NAME}' and acl/any(t: t eq '{user_name}')"
        print("filters we have *********************************************",filters)
        r = doc_search.similarity_search_with_relevance_scores(rephrased_question, k=top,filters=filters )#change by Puneet
        print("r values *********************************",r)
        r = [src[0] for src in r if src[1] > pinecone_threshold]
        pinecone_sources = list(set([get_filename(data.metadata['source']) for data in r]))

        if r:
            results = [get_filename(doc.metadata['source']) + ": " + nonewlines(doc.page_content) for doc in r]
            content = "\n".join(results)

            chat_prompt = config["chat_prompt_template"].format(sources=content, chat_history=get_chat_history_as_text(history))
            print("*"*25)
            print(chat_prompt)
            print("*"*25)
            start_time=time.time()
            answer = openai_completion(
                deployment_name=config["chat_model"],
                prompt=chat_prompt,
                temperature=config["chat_temperature"],
                max_tokens=config["chat_max_tokens"],
                n=config["chat_n"],
                stop=config["chat_stop"])

            print("Time consumed in answer from gpt-turbo: {:.2f}s".format(time.time() - start_time))
            print("*"*25)
            print(type(answer))
            print(len(answer))
            print(answer)
            print("*"*25)
            # log.logger.log("Time consumed in answer from gpt-turbo: {:.2f}s".format(time.time() - start_time))
            logger.info(answer)

            follow_up_questions_prompt = config["follow_up_questions_prompt_template"].format(answer=answer)
            start_time=time.time()
            follow_up_q = openai_completion(
                deployment_name=config["followup_model"],
                prompt=follow_up_questions_prompt,
                temperature=config["followup_temperature"],
                max_tokens=config["followup_max_tokens"],
                n=config["followup_n"],
                stop=config["followup_stop"])

            follow_up_questions = get_followup_questions_only(follow_up_q)
            print("Time consumed in follow_up_questions: {:.2f}s".format(time.time() - start_time))
            # log.logger.info("Time consumed in follow_up_questions: {:.2f}s".format(time.time() - start_time))

            answer = answer_with_sources(include_all_sources, answer, pinecone_sources)

            # ================================CACHE=======================================================
            if(bot_type=="KNOWLEDGE_BOT_WITH_CACHE"):
                print("insert_to_cache")
                insert_to_cache(rephrased_question, answer,bot_type)
            # =======================================================================================

            return {"data_points": results, "answer": answer+follow_up_questions,
                    "thoughts": f"Searched for:<br>{rephrased_question}<br><br>Prompt:<br>" + chat_prompt.replace('\n', '<br>')}
        else:
            return {"data_points": [], "answer": "I regret to inform you that I am unable to offer a reply to your prompt.",
                    "thoughts": f"Coming soon!!"}

