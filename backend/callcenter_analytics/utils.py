from langchain.llms import AzureOpenAI
from typing import List
import azure.cognitiveservices.speech as speechsdk
from callcenter_analytics.rest_helper import send_get, send_post
from datetime import datetime
import uuid
from http import HTTPStatus
from time import sleep, time
import os
import ast
import openai
from log.log import logger

from configuration.config import WAIT_SECONDS, SPEECH_TRANSCRIPTION_PATH, speech_endpoint, speech_subscription_key, call_center_app_host, call_center_app_port, SQLOperation, callanalytics_dbname, CALLANALYTICS_OPENAI_API_BASE, CALLANALYTICS_OPENAI_API_KEY


class NewAzureOpenAI(AzureOpenAI):
    stop: List[str] = None

    @property
    def _invocation_params(self):
        params = super()._invocation_params
        # fix InvalidRequestError: logprobs, best_of and echo parameters are not available on "gpt-35-turbo" model.
        params.pop('logprobs', None)
        params.pop('best_of', None)
        params.pop('echo', None)
        # params['stop'] = self.stop
        return params

def fetchAgentCustomerValues():
    sql_db = SQLOperation('oraindb')
    connection = sql_db.get_connection()
    cursor = connection.cursor()
    
    cursor.execute("select AgentConfusion, AgentKnowledge, CustomerSentimentAtStartOfCall, CustomerSentimentAtEndOfCall, CustomerSatisfaction, IssueStatus from CallAnalyticsCache")
    values = cursor.fetchall()  # Fetch all rows
    
    if values:
        first_row = values[0]  # Get the first row (tuple)
        # print("First row values:", first_row)
    else:
        print("No data found.")
    
    cursor.close()
    connection.close()
    return first_row if values else None


def customized_answers(choice):
    if choice.lower().startswith("answer: "):
        return choice[8:]
    return choice

def get_chat_text(file_name):
    open_fd = open(file_name, "r")
    chat_text = open_fd.read()
    return chat_text

def get_response(llm, question, text, output_format,aspects):
#     for value in values:
    prompt = f"""<|im_start|>
    Your task is to read the call center conversation text between the customer and \
    agent and answer the questions asked by the user.\
    The answers should be based on the following guidelines.\
    You will be given a list of aspects delimeted with ''. Your task is to understand the conversation and \
    find in which aspect does the conversation fall.Do not add you own aspects.\
    The status of issue should be from list delimited with ``\
    The questions are present in the following text , delimited by triple backticks. \
    Perform sentiment analysis based on the questions asked.\
    Be precise on answering questions related to ratings.\
    Do not rephrase your answers.\
    Rate agent's confusion on a scale of 1 to 10.\
    Rate agent's knowledge to satisfy customer on a scale of 1 to 10.\
    Rate customer's satisfaction on a scale of 1 to 10.\
    Rate customer's sentiment at the start of the call on a scale of 1 to 10.\
    Rate customer's sentiment at the end of the call on a scale of 1 to 10.\
    Return response strictly  as a json dictionary with the following format ```{output_format}``` \
    If answer not found, please specify the answer as UNKNOWN.
    Do not include response other than json response.\

    Question: ```{question}``` \
    Aspects:''{aspects}''\
    IssueStatus:``{"InProgress" , "Resolved" ,"UnResovled"}``
    {text}

    <|im_end|>
    """
    print("inside get response")
    try:
        completion = llm.generate(prompts = [prompt],stop=["<|im_end|>", "<|im_start|>"])
        print(completion)
    except Exception as e:
        print("exception",e)
#     print(completion.generations[0][0].text)
    return (customized_answers(completion.generations[0][0].text.strip()))

def analyse_transcript(file_name):
    old_api_key = os.environ["OPENAI_API_KEY"]
    old_api_base = os.environ["OPENAI_API_BASE"]
    try:
        # absolute path to search all text files inside a specific folder
        # path = r'/static/results.txt'
        # static_folder_path = os.path.join(os.getcwd(), 'static')
        # path = os.path.join(static_folder_path, 'results.txt')

        deployment_name="container-poc-gpt4mini-model"
        openai.api_base = CALLANALYTICS_OPENAI_API_BASE
        openai.api_key = CALLANALYTICS_OPENAI_API_KEY
        os.environ["OPENAI_API_BASE"] = CALLANALYTICS_OPENAI_API_BASE
        os.environ["OPENAI_API_KEY"] = CALLANALYTICS_OPENAI_API_KEY
        llm = NewAzureOpenAI(deployment_name=deployment_name,temperature=0,max_tokens=1024,stop=["\n"],request_timeout=15,max_retries=5)
        sql_db = SQLOperation(callanalytics_dbname)
        connection = sql_db.get_connection()
        cursor = connection.cursor()

        db_col_names = "CallId, Issue, IssueDetails, CustomerName, CustomerLocation, AgentName, DeviceName, AgentConfusion, AgentKnowledge, CustomerSatisfaction,CustomerSentimentAtStartOfCall,CustomerSentimentAtEndOfCall,Aspects,IssueStatus"
        col_values = "?,?,?,?,?,?,?,?,?,?,?,?,?,?"

        #Need to put this in some config
        type_conv_list = ['AgentConfusion','AgentKnowledge','CustomerSatisfaction','CustomerSentimentAtStartOfCall','CustomerSentimentAtEndOfCall']


        analytics_response = []
        call_id = "CallAnalytics" + "_" + str(int(time()))
        chat_text = get_chat_text(file_name)

        try:
            print("inside try")
            question="What is the conversation about? What is the issue summary in 20 words? What is the customer name? What is the customer location? What is the agent name? What is the device name? What is the status of Issue?"
            output_format = {
                "Issue":"",
                "IssueSummary":"",
                "CustomerName":"",
                "CustomerLocation":"",
                "AgentName":"",
                "DeviceName":"",
                "AgentConfusion":"",
                "AgentKnowledge":"",
                "CustomerSatisfaction":"",
                "CustomerSentimentAtStartOfCall":"",
                "CustomerSentimentAtEndOfCall":"",
                "Aspect":"",
                "IssueStatus":""
            }
            aspects={
                "ServiceOutage",
                "Internet",
                "Network",
                "Billing",
                "EquipmentMalfunction",
                "RoamingOrInternationalCalling",
                "Messaging",
                "CustomerService",
                "PlanOrPackage",
            }
            response = get_response(llm, question, chat_text, output_format, aspects)
            print("Response: {}".format(response))

            row_values = [call_id]
            response_obj = ast.literal_eval(response)
            print("Response obj: {}".format(response_obj))
            analytics_response.append({
                    call_id:response_obj
            })
            for val in response_obj:
                dict_val = response_obj[val]
                if val in type_conv_list:
                    dict_val = int(dict_val)
                row_values.append(dict_val)
            cursor.execute("""INSERT INTO CallAnalytics (""" + db_col_names + """) VALUES (""" + col_values + """)""", tuple(row_values))
            cursor.execute("DELETE FROM CallAnalyticsCache")
            cursor.execute("""INSERT INTO CallAnalyticsCache (""" + db_col_names + """) VALUES (""" + col_values + """)""", tuple(row_values))
        except:
            pass

        connection.commit()
        connection.close()
        print("Analytics response :{}".format(analytics_response))
        openai.api_base = old_api_base
        openai.api_key = old_api_key
        os.environ["OPENAI_API_KEY"] = old_api_key
        os.environ["OPENAI_API_BASE"] = old_api_base
        logger.info("Analytics response: {}".format(analytics_response))
        return {"data": analytics_response}

    except Exception as e:

        openai.api_base = old_api_base
        openai.api_key = old_api_key
        os.environ["OPENAI_API_KEY"] = old_api_key
        os.environ["OPENAI_API_BASE"] = old_api_base
        print(f"An error occurred in 'analyse_transcript()': {str(e)}")
        return {"error": str(e)}

def get_transcription(transcription_uri):
    response = send_get(uri=transcription_uri, key="", expected_status_codes=[HTTPStatus.OK])
    logger.info("response Get transcription {}".format(response["json"]))
    return response["json"]

def get_transcription_files(transcription_id, user_config):
    uri = f"https://{user_config['speech_endpoint']}{SPEECH_TRANSCRIPTION_PATH}/{transcription_id}/files"
    response = send_get(uri=uri, key=user_config["speech_subscription_key"], expected_status_codes=[HTTPStatus.OK])
    logger.info("response Get transcription files {}".format(response["json"]))
    return response["json"]

def get_transcription_status(transcription_id, user_config) :
    uri = f"https://{user_config['speech_endpoint']}{SPEECH_TRANSCRIPTION_PATH}/{transcription_id}"
    response = send_get(uri=uri, key=user_config["speech_subscription_key"], expected_status_codes=[HTTPStatus.OK])
    logger.info("Transcription status {}".format(response["json"]["status"]))
    if "failed" == response["json"]["status"].lower() :
        raise Exception(f"Unable to transcribe audio input. Response:{os.linesep}{response['text']}")
    else :
        return "succeeded" == response["json"]["status"].lower()

def get_transcription_uri(transcription_files):
    value = next(filter(lambda value: "transcription" == value["kind"].lower(), transcription_files["values"]), None)
    logger.info("value is {}".format(value))
    if value is None :
        raise Exception (f"Unable to parse response from Get Transcription Files API:{os.linesep}{transcription_files['text']}")
    return value["links"]["contentUrl"]

def wait_for_transcription(transcription_id, user_config) :
    done = False
    while not done :
        print(f"Waiting {WAIT_SECONDS} seconds for transcription to complete.")
        sleep(WAIT_SECONDS)
        done = get_transcription_status(transcription_id, user_config=user_config)

def create_transcription(user_config):
    uri = f"https://{user_config['speech_endpoint']}{SPEECH_TRANSCRIPTION_PATH}"
    print("Create Transcription uri",uri)
    # Create Transcription API JSON request sample and schema:
    # https://westus.dev.cognitive.microsoft.com/docs/services/speech-to-text-api-v3-0/operations/CreateTranscription
    # Notes:
    # - locale and displayName are required.
    # - diarizationEnabled should only be used with mono audio input.
    content = {
        "contentUrls" : [user_config["input_audio_url"]],
        "properties" : {
            "diarizationEnabled" : not user_config["use_stereo_audio"],
            "timeToLive" : "PT30M"
        },
        "locale" : user_config["locale"],
        "displayName" : f"call_center_{datetime.now()}"
    }
    print("Content",content)

    response = send_post(uri=uri, content=content, key=user_config["speech_subscription_key"], expected_status_codes=[HTTPStatus.CREATED])
    
    # Create Transcription API JSON response sample and schema:
    # https://westus.dev.cognitive.microsoft.com/docs/services/speech-to-text-api-v3-0/operations/CreateTranscription
    transcription_uri = response["json"]["self"]
    # The transcription ID is at the end of the transcription URI.
    transcription_id = transcription_uri.split("/")[-1];
    # Verify the transcription ID is a valid GUID.
    try :
        uuid.UUID(transcription_id)
        logger.info("Transcription id is {}".format(transcription_id))
        return transcription_id
    except ValueError:
        raise Exception(f"Unable to parse response from Create Transcription API:{os.linesep}{response['text']}")

def refine_transcript(transcript):
    refined_transcript = ""
    refined_transcript_html = "<html><head><meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" /><meta http-equiv=\"Content-Style-Type\" content=\"text/css\" /></head>"
    previous_speaker = 1
    speaker_index = 0
    row_colors = ["#0078d4", "#aa3456"]
    row_color_index = 0
    refined_transcript_html += "<body style=\"font-family:'Times New Roman'; font-size:12pt\">"
    refined_transcript_html += "<table>"
    for recognized_phrase in transcript:
        speaker = recognized_phrase["speaker"]
        print("Speaker", speaker)
        nBest = recognized_phrase["nBest"]
        if speaker != previous_speaker or speaker_index == 0:
            if speaker_index != 0:
                refined_transcript += "\n"
                refined_transcript_html += "</td></tr>"
                row_color_index += 1
            if speaker == 1:
                speaker_text = "Customer: "
            else:
                speaker_text = "Agent: "
            refined_transcript += speaker_text
            refined_transcript_html += "<tr style=\"color:" + row_colors[row_color_index % 2] + ";\">"
            refined_transcript_html += "<td width=\"80px\"><b>" + speaker_text + "</b></td><td>"
            previous_speaker = speaker
        for chat in nBest:
            print(chat["display"])
            refined_transcript += chat["display"]
            refined_transcript_html += chat["display"]
        speaker_index += 1
    refined_transcript_html += "</table>"
    refined_transcript_html += '</body>'
    refined_transcript_html += "</html>"
    return refined_transcript, refined_transcript_html

def convert_audio_to_text(input_audio_file,outputfile):
    
    # We are using mono so set use_stereo_audio value to False
    # The audio is of type with only one channel
    user_config = {
        "speech_endpoint": speech_endpoint,
        "speech_subscription_key": speech_subscription_key,
        "input_audio_url": 'https://xneytestbot6cbk.blob.core.windows.net/audiofiles/'+ input_audio_file,
        "use_stereo_audio": False,
        "locale": "en-US"
    }
    print("User_config :{}".format(user_config))
    transcription_id = create_transcription(user_config)
    wait_for_transcription(transcription_id, user_config)
    print(f"Transcription ID: {transcription_id}")
    transcription_files = get_transcription_files(transcription_id, user_config)
    print("Transcription files: {}".format(transcription_files))
    transcription_uri = get_transcription_uri(transcription_files)
    print(f"Transcription URI: {transcription_uri}")
    transcription = get_transcription(transcription_uri)
    transcription["recognizedPhrases"] = sorted(transcription["recognizedPhrases"], key=lambda phrase : phrase["offsetInTicks"])
    
    refined_transcript, refined_transcript_html = refine_transcript(transcription["recognizedPhrases"])
    output_file = open(outputfile, "w")
    output_file.write(refined_transcript)
    output_file.close()
    
    output_file_html = open(os.path.join(os.getcwd(),'static', input_audio_file.split(".")[0] + ".html"), "w")
    output_file_html.write(refined_transcript_html)
    output_file_html.close()

    ### Equivalent code using SDK is as below (Commented on purpose as we are using API v 3.0 to get speaker Id)
    '''
    print("Inside convert audio to text")
    speech_config = speechsdk.SpeechConfig(subscription="6c91d6d0e26f42f7a13a597073aea7bb", region="eastus")
    audio_config = speechsdk.audio.AudioConfig(filename=input_audio_file)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    done = False
    print("Inside convert audio to text after")
    # Set up the output file for the transcript
    output_file = open(outputfile, "w")

    def stop_cb(evt):
        """callback that signals to stop continuous recognition upon receiving an event `evt`"""
        print('CLOSING on {}'.format(evt))
        # Close the output file and stop the continuous recognition session
        output_file.close()
        speech_recognizer.stop_continuous_recognition()
        print("Transcript saved in file:", outputfile)
        nonlocal done
        done = True

    def recognized_cb(evt: speechsdk.SpeechRecognitionEventArgs):
        # print('Event  result:', evt.result)
        # print('\tSpeaker ID={}'.format(evt.result.speaker_id))
        if speechsdk.ResultReason.RecognizedSpeech == evt.result.reason :
            print('RECOGNIZED:', evt.result.text)
            output_file.write(evt.result.text)
            output_file.flush()

    # Connect callbacks to the events fired by the speech recognizer
    speech_recognizer.recognized.connect(recognized_cb)

    # Stop continuous recognition on either session stopped or canceled events
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    # Start continuous speech recognition
    speech_recognizer.start_continuous_recognition()
    while not done:
        pass
    '''

