import re, os
from pathlib import Path
import openai, traceback
from typing import List
from langchain.llms import AzureOpenAI
from log.log import logger
import pymssql


class NewAzureOpenAI(AzureOpenAI):
    stop: List[str] = None

    @property
    def _invocation_params(self):
        params = super()._invocation_params
        # fix InvalidRequestError: logprobs, best_of and echo parameters are not available on gpt-35-turbo model.
        params.pop('logprobs', None)
        params.pop('best_of', None)
        params.pop('echo', None)
        # params['stop'] = self.stop
        return params

def is_url(path):
    url_regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https:// or ftp:// or ftps://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return bool(url_regex.match(path))

def get_filename(path):
    if is_url(path):
        return path
    else:
        path = Path(str("/".join(path.split("/")[:-1])))
        return str(os.path.basename(path))

def has_sources(text):
    pattern = r'\[(.*?)\]'
    match = re.findall(pattern, text)
    logger.info(f"Sources present in answer are {match}")
    return match

def get_chat_history_as_text(history, include_last_turn=True, approx_max_tokens=1000):
    history_text = ""
    for h in reversed(history if include_last_turn else history[:-1]):
        history_text = """<|im_start|>user""" + "\n" + h[
            "user"] + "\n" + """<|im_end|>""" + "\n" + """<|im_start|>assistant""" + "\n" + (
                           h.get("bot") + """<|im_end|>""" if h.get("bot") else "") + "\n" + history_text
        if len(history_text) > approx_max_tokens * 4:
            break
    return history_text

# def openai_completion(deployment_name,prompt,temperature,max_tokens,n,stop):
#     llm = NewAzureOpenAI(deployment_name=deployment_name, temperature=temperature,n=n, max_tokens=max_tokens, request_timeout=40, max_retries=300)
#     completion = llm.generate(prompts=[prompt], stop=stop)
#     return completion.generations[0][0].text

def openai_completion(deployment_name, prompt, temperature, max_tokens,n, stop):
    try:
        logger.info('openai_completion')
        completion = openai.ChatCompletion.create( # Change the function Completion to ChatCompletion
            engine = deployment_name,
            messages = [
                {'role': 'system', 'content': prompt}
            ],
            max_tokens = max_tokens,
            temperature = temperature,
            n = n,
            stop = stop
        )
        logger.info(f"Final Answer : {completion.choices[0].message['content']}")
        return completion.choices[0].message['content']
    except Exception as e:
        logger.error(f"Error in openai_completion: {e}")
        return ""

def get_followup_questions_only(follow_up_q):
    pattern = r"(?i)\b(?:what|who|where|when|why|how|which|is|are|am|do|does|did|has|have|had|can|could|may|might|shall|should|will|would)\b.*\?"

    # Extract questions using regular expression
    questions = re.findall(pattern, follow_up_q)
    follow_up_questions = ""
    if len(questions) > 3:
        questions = questions[:3]
    for que in questions:
        follow_up_questions += " <<" + que + ">> "

    return follow_up_questions

def answer_with_sources(include_all_sources,answer,pinecone_sources):
    if include_all_sources:
        answer = re.sub(r"<<.*?>>", "", answer)
        if not has_sources(answer):
            logger.info("Including all pinecone sources")
            for source in pinecone_sources:
                answer += " [" + source + "] "
        else:
            sources = has_sources(answer)
            for srcs in sources:
                if srcs not in pinecone_sources:
                    answer = answer.replace("[" + srcs + "]", "")
    else:
        sources = has_sources(answer)
        for srcs in sources:
            if srcs not in pinecone_sources:
                answer = answer.replace("[" + srcs + "]", "")
    return answer

def list_to_html_table(list_of_lists):
    # Create the HTML table
    html_table = """<style>
        table {
            color: black;
            font-family: arial, sans-serif;
            border-collapse: collapse;
            max-width: 100%;            
            white-space: nowrap;
            overflow-x: auto;
            display: block;
            background: inherit;
        }
        td, th{
            border: 1px solid black;
            text-align: left;
            padding: 8px;
        }
        tr:nth-child(even) {
            background-color: #dddddd;
        }
        tr:nth-child(odd){
            background-color: white;
        }

        </style>
        <table>"""
    # Loop through the sublists
    for i, sublist in enumerate(list_of_lists):
        # Create a table row
        html_table += "<tr>"
        # Loop through the elements of the sublist
        for element in sublist:
            # Create a table header or a table data cell depending on the index
            if i == 0:
                html_table += f"<th>{element}</th>"
            else:
                html_table += f"<td>{element}</td>"
        # Close the table row
        html_table += "</tr>"
        # Close the HTML table
    html_table += "</table>"
    # Return the HTML table using markdown syntax
    return f"{html_table}"

def execute_sql_query(response,conn):
    logger.info(f"Response {response}")
    match = re.findall(r'"([^"]*)"', response)
    logger.info(f"Match is {match}")
    if match:
        query = match[0]
    else:
        query = ""
        answer = "I regret to inform you that I am unable to offer a reply to your prompt. Try to be more precise in your query."
    # cursor = conn.cursor()
    logger.info(f"Query is {query}")
    if len(query) > 0:
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
        

        except Exception as e:
            print(f"Error occurred: {e}")
        
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            output = cursor.fetchall()
            output.insert(0, [column[0] for column in cursor.description])
            answer = query + "\n\n\n" + list_to_html_table(output)
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(stack_trace)
            print("tracker ********************** ",stack_trace)
            answer = "Note: I regret to inform you that I am unable to offer a reply to your prompt. Try to be more precise in your query."
    return answer