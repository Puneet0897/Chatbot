from configuration.config import *

# azure_with_pinecone - FAQ, Policy
FAQ_config = {
    "top":6,
    "pinecone_threshold": 0.75,
    "include_all_sources": True,

    "query_model": AZURE_OPENAI_GPT_DEPLOYMENT,
    "query_temperature":0.0,
    "query_max_tokens":32,
    "query_n":1,
    "query_stop":["\n"],

    "chat_model": AZURE_OPENAI_CHATGPT_DEPLOYMENT,
    "chat_temperature":0.7,
    "chat_max_tokens":1024,
    "chat_n":1,
    "chat_stop":["<|im_end|>", "<|im_start|>"],

    "followup_model": AZURE_OPENAI_CHATGPT_DEPLOYMENT,
    "followup_temperature":0.8,
    "followup_max_tokens":1024,
    "followup_n":1,
    "followup_stop":["<|im_end|>", "<|im_start|>"],

    "query_prompt_template": """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base.
    Generate a search query based on the conversation and the new question. 
    Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
    Do not include any text inside [] or <<>> in the search query terms.
    If the question is not in English, translate the question to English before generating the search query.

Chat History:
{chat_history}

Question:
{question}

Search query:
""",

    "chat_prompt_template": """<|im_start|>system
    Be brief in your answers.
    Answer ONLY with the facts listed in the list of sources below. If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below. If asking a clarifying question to the user would help, ask the question.
    For tabular information return it as an html table. Do not return markdown format.
    Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brakets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
    Sources:
    {sources}
    <|im_end|>
    {chat_history}
    """,

    "follow_up_questions_prompt_template": """<|im_start|>system
    Generate only and only three follow up questions based on the context given below.
    Context:
    {answer}
    <|im_end|>
    """
}

# SmartGPT_Xorinat - Security Bot
Security_config = {
    "top":6,
    "pinecone_threshold": 0.0,
    "include_all_sources": False,

    "query_model": AZURE_OPENAI_GPT_DEPLOYMENT,
    "query_temperature":0.0,
    "query_max_tokens":32,
    "query_n":1,
    "query_stop":["\n"],

    "chat_model": AZURE_OPENAI_CHATGPT_DEPLOYMENT,
    "chat_temperature":0.7,
    "chat_max_tokens":1024,
    "chat_n":1,
    "chat_stop":["<|im_end|>", "<|im_start|>"],

    "followup_model": AZURE_OPENAI_CHATGPT_DEPLOYMENT,
    "followup_temperature":0.8,
    "followup_max_tokens":1024,
    "followup_n":1,
    "followup_stop":["<|im_end|>", "<|im_start|>"],

    "query_prompt_template": """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base.
    Generate a search query based on the conversation and the new question. 
    Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
    Do not include any text inside [] or <<>> in the search query terms.
    If the question is not in English, translate the question to English before generating the search query.

Chat History:
{chat_history}

Question:
{question}

Search query:
""",

    "chat_prompt_template": """<|im_start|>system
Be brief in your answers. Always be polite and don't answer in negative way. Instead of saying I do not have any sources use your own knowledge base and answer.
Answer the question using the sources and your own knowledge as well never limit yourself to the sources given below. If asking a clarifying question to the user would help, ask the question.
For tabular information return it as an html table. Do not return markdown format.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brakets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].
Sources:
{sources}
<|im_end|>
{chat_history}
""",

    "follow_up_questions_prompt_template": """<|im_start|>system
    Generate only and only three follow up questions based on the context given below.
    Context:
    {answer}
    <|im_end|>
    """
}
