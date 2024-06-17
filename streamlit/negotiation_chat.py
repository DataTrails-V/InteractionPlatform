
import streamlit as st
from openai import OpenAI
from datetime import datetime
import json
import pandas as pd
import os
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google.oauth2.service_account import Credentials
import uuid
import tempfile

# Initialize the OpenAI client (replace 'your-api-key' with your actual OpenAI API key)
client = OpenAI(api_key=os.getenv('API_KEY'))


# Load secrets from Streamlit
client_secret = st.secrets["client_secret"]

    
def save_data_to_excel(df, filename='SurveyData.xlsx'):
    """Save DataFrame to an Excel file and upload it to Google Drive."""
    # Setup Google Drive
    #g_login = GoogleAuth()
    #g_login.LoadClientConfigFile("streamlit/client_secret.json")
    # Create a temporary file to store client secret
    # with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
    #     temp_file.write(client_secret)
    #     temp_file_path = temp_file.name
    
    # g_login.LoadClientConfigFile(temp_file_path)
    # g_login.LocalWebserverAuth()
    # drive = GoogleDrive(g_login)
    
    # Authenticate using service account
    credentials = Credentials.from_service_account_info(client_secret)
    g_login = GoogleAuth()
    g_login.credentials = credentials
    drive = GoogleDrive(g_login)
    
    
    # Try to load the existing file from Google Drive
    file_list = drive.ListFile({'q': f"title='{filename}' and trashed=false"}).GetList()
    
    if file_list:
        # File exists, download it
        file_to_update = drive.CreateFile({'id': file_list[0]['id']})
        file_to_update.GetContentFile(filename)
        existing_df = pd.read_excel(filename)
        df = pd.concat([existing_df, df], ignore_index=True)
    else:
        # File does not exist, use the provided DataFrame directly
        df = df.copy()

    # Save DataFrame to Excel
    df.to_excel(filename, index=False)

    # Upload or update the file on Google Drive
    if file_list:
        file_to_update.SetContentFile(filename)
        file_to_update.Upload()  # Update the existing file
    else:
        file_to_create = drive.CreateFile({'title': filename})
        file_to_create.SetContentFile(filename)
        file_to_create.Upload()  # Upload as a new file

    return ""

scenarios_backgrounds = {
        "Work-Study Program": "You play the role of an advisor in a work-study program negotiation. You are negotiating how to distribute funds among fictitious candidates for a work-study program. We have $30,000 to distribute among Alice, Bob, and Carol. Our goal is to allocate these funds in a way that supports their participation in the work-study program effectively. Background Information: Alice is a high academic achiever and has moderate financial need. Bob has average academic performance and high financial need. Carol has good academic performance and low financial need.",
        "Selling a Company": "You play the role of a business partner in the process of selling a company. You and your partner end up getting an offer that pleases you both, namely $500,000, so now you face the enviable task of splitting up the money. You put twice as many hours into the firm’s start-up as your partner did, while he worked fulltime elsewhere to support his family. You, who are independently wealthy, were compensated nominally for your extra time. For you, the profit from the sale would be a nice bonus. For your partner, it would be a much-needed windfall.",
        "Bonus Allocation": "You play the role of an HR manager discussing bonus allocations. Youb and your negotiation partner have to allocate a bonus of $50,000 among three employees. The first employee exceeded the targets and took on additional responsibilities. The second employee showed great improvement and proactive behavior. The third employee performed solidly according to the role requirements."
    }
personality_type = {
        "Proportional": "You are a negotiation partner, which acts according to proportionality.",
        "Equal": "You are a negotiation partner, which acts according to equality.",
        "Default": "You are a negotiation partner."
        
    }  
def ask(question, chat_log=None, version = "", scenario="", personality = ""):
    """Function to ask a question to the AI model and get a response based on the scenario."""
    scenario_instructions = {
        "Work-Study Program": "Instruction1: You play the role of an advisor in a work-study program negotiation.  We are negotiating how to distribute funds among fictitious candidates for a work-study program. We have $30,000 to distribute among Alice, Bob, and Carol. Our goal is to allocate these funds in a way that supports their participation in the work-study program effectively. Background Information: Alice is a high academic achiever and has moderate financial need. Bob has verage academic performance and high financial need. Carol has good academic performance and low financial need.",
        "Selling a Company": "Instruction2: You play the role of a business partner in the process of selling a company. We end up getting an offer that pleases us both, namely $500000 , so now you face the enviable task of splitting up the money. Your partner put twice as many hours into the firm’s start-up as you did, while you worked fulltime elsewhere to support your family. Your partner, who is independently wealthy, was compensated nominally for her extra time. For THEM, the profit from the sale would be a nice bonus. For you, it would be a much-needed windfall.",
        "Bonus Allocation": "Instruction3: You play the role of an HR manager discussing bonus allocations. We have to allocate a bonus of $50000 among three employees. The first employee exceeded the targets and took on additional responsibilities. The second employee showed a great improvement and proactive behaviour. The third employee performed solidly according the role requirements" 
    }
   
    
    system_message = f"{personality_type[personality], scenario_instructions[scenario], 'Respond concisely in no more than three sentences.'}"

    messages = [{"role": "system", "content": system_message}]
    if chat_log:
        messages.extend(chat_log)
    messages.append({"role": "user", "content": question})
    
    response = client.chat.completions.create(
        model=version,
        messages=messages,
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    answer = response.choices[0].message.content
    return answer, messages

def save_data(data, filename_prefix):
    """Function to save data (chat logs or questionnaire responses) to a file."""
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    file_path = f'{filename_prefix}_{timestamp}.json'
    with open(file_path, 'w') as file:
        json.dump(data, file)
    return file_path

def main():
    if 'transformed' not in st.session_state:
        st.session_state.transformed = pd.DataFrame()
    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Go to", ["Home", "Questionnaire", "Negotiation 1", "Negotiation 2"])
    
    if selection == "Home":
        st.header('Fair Play: Assessing GPT Models in Simulated Negotiation Environments')
        st.write("""
            Dear Participant,

            Welcome to our interactive platform! This platform is designed to gather valuable insights into the performance of GPT models in negotiation scenarios. By analyzing your interactions, we aim to understand the fairness and behavior of AI in negotiation contexts, which will help inform future developments and improvements. Your participation is crucial, as it will provide essential data on how these AI models perform in simulated negotiations.

            **How to Participate**
            1. **Fill out the survey:** Start by completing a brief survey on the second page, which should take about 3 minutes. Your responses are crucial for understanding the context of each negotiation scenario. Please answer all questions as accurately and honestly as possible.
            2. **Choose a negotiation scenario:** After completing the survey, you'll be able to select from a list of suggested negotiation scenarios. Choose one that interests you or feels relevant. Background information about the chosen scenario, including your role, will be provided.
            3. **Engage with the chatbot:** Once you've selected a scenario, you can begin negotiating with the chatbot. Please limit the negotiation to no more than 6 rounds to ensure the process is concise and manageable.

            Please be assured that all information you provide will be kept confidential and used solely for research purposes. Your responses will be anonymized, and no personally identifiable information will be linked to your answers. Participation in this study is voluntary, and you may withdraw at any time without any consequences.

            This study is conducted by Veronika Tsishetska and Dr. Meltem Aksoy. If you have any questions or need further clarification, feel free to contact us at veronika.tsishetska@tu-dortmund.de and meltem.aksoy@tu-dortmund.de.

            Thank you for your time and valuable contribution.

            Sincerely,
            
            Veronika Tsishetska & Dr. Meltem Aksoy
            
            Data Science and Data Engineering
            Technical University Dortmund
        """)
    
    
    
        st.header('Consent for Participation and Data Collection Authorization')

        # Introductory Consent Information
        st.write("""
        Thank you for considering participation in our research study. In accordance with the General Data Protection Regulation (GDPR) and other relevant laws, we are committed to protecting and respecting your privacy. Please read the following important information concerning the collection and processing of your personal and interaction data.
        """)

        # Detailed Consent Information in an Expander
        with st.expander("Read Detailed Consent Information"):
            st.write("""
            **Purpose of Data Collection:**
            The purpose of collecting your data is to conduct a thorough and effective research study aimed at understanding the negotiation dynamics in AI-mediated environments. Your participation will involve various interactive tasks, and the data collected will be crucial for achieving the research objectives.

            **Nature of Data Collected:**
            We will collect data that may include, but is not limited to, your responses to surveys and questionnaires, details of your interactions with our digital tools, and any other inputs you provide during the study. This information will help us to analyze patterns, draw conclusions, and improve our models and tools.

            **How Your Data Will Be Used:**
            Your data will be analyzed to gain insights related to the research objectives. The findings may be shared with the academic community through publications, presentations, and reports. No personal data that could directly identify you will be used in any reports or publications.

            **Confidentiality and Security of Your Data:**
            All personal data collected during this study will be stored securely and accessed only by authorized members of the research team. We will take all necessary precautions to protect your data from unauthorized access, disclosure, alteration, or destruction.

            **Your Rights:**
            Participation in this study is voluntary, and you have the right to withdraw your consent at any time without consequence. Upon withdrawal, all personal data collected from you will be deleted from our records unless it has been anonymized and cannot be traced back to you. You also have rights to access your personal data, correct any inaccuracies, and request the deletion of your data under certain circumstances.
            """)

        # Initialize consent state if not already set
        if 'consent' not in st.session_state:
            st.session_state.consent = False

        # Consent Checkbox
        consent = st.checkbox("By checking this box, you confirm that you have read and understood this consent form and agree to participate in this research study. You consent to the collection, processing, and use of your personal and interaction data as outlined above, in accordance with GDPR and other applicable regulations.", value=st.session_state.consent)
        

        # Update session state when checkbox is interacted with
        if consent != st.session_state.consent:
            st.session_state.consent = consent

        if not st.session_state.consent:
            st.error("You must agree to the data collection to participate in this study.")

   
    
    

    elif selection == "Questionnaire":
        st.header("Questionnaire")
        st.write("Please fill out this brief survey to participate in the study.")

        # Demographic Questions
        data = {}
        age_options = ["18-20", "21-25", "26-30", "31-39", "40 and above"]
        age = st.selectbox("What is your age range?", age_options, key='age_range')
        gender = st.radio("What is your gender?", ["Male", "Female", "Other"], key='gender')
        academic_degree = st.selectbox("What is your highest academic degree?", ["Bachelor", "Master", "PhD", "Other"], key='academic_degree')
        mother_tongue = 'english'
        is_english = st.radio("Is English your mother tongue?", ["Yes", "No"], key='is_english')
        if is_english == "No":
            mother_tongue = st.text_input("What is your mother tongue?", key='mother_tongue')

        # Likert Scale Questions
        statements = [
            "I think people who are more hard-working should end up with more money.",
            "I think people should be rewarded in proportion to what they contribute.",
            "The effort a worker puts into a job ought to be reflected in the size of a raise they receive.",
            "It makes me happy when people are recognized on their merits.",
            "In a fair society, those who work hard should live with higher standards of living.",
            "I feel good when I see cheaters get caught and punished.",
            "The world would be a better place if everyone made the same amount of money.",
            "Our society would have fewer problems if people had the same income.",
            "I believe that everyone should be given the same amount of resources in life.",
            "I believe it would be ideal if everyone in society wound up with roughly the same amount of money.",
            "When people work together toward a common goal, they should share the rewards equally, even if some worked harder on it.",
            "I get upset when some people have a lot more money than others in my country."
        ]

        # Likert Scale Options as separate columns
              # Likert Scale Options as separate columns
        options = ["1 - Strongly Disagree", "2 - Disagree", "3 - Neutral", "4 - Agree", "5 - Strongly Agree"]

        data = {
            'Statement': statements,
            '1 - Strongly Disagree': [False, False, False, False, False, False, False, False, False, False, False, False],
            '2 - Disagree':[False, False, False, False, False, False, False, False, False, False, False, False],
            '3 - Neutral': [False, False, False, False, False, False, False, False, False, False, False, False],
            '4 - Agree': [False, False, False, False, False, False, False, False, False, False, False, False],
            '5 - Strongly Agree':[False, False, False, False, False, False, False, False, False, False, False, False],
        }

        checkbox_renderer = JsCode("""
                class CheckboxRenderer {
            init(params) {
                this.params = params;

                this.eGui = document.createElement('input');
                this.eGui.type = 'checkbox';
                this.eGui.checked = params.value;

                this.checkedHandler = this.checkedHandler.bind(this);
                this.eGui.addEventListener('click', this.checkedHandler);
            }

            checkedHandler(e) {
                let checked = e.target.checked;
                let colId = this.params.column.colId;
                let otherColumns = ['1 - Strongly Disagree', '2 - Disagree', '3 - Neutral', '4 - Agree', '5 - Strongly Agree'].filter(c => c !== colId);

                if (checked) {
                    // Uncheck all other checkboxes in the same row
                    otherColumns.forEach(c => {
                        this.params.node.setDataValue(c, false);
                    });
                }
                this.params.node.setDataValue(colId, checked);
            }

            getGui() {
                return this.eGui;
            }

            destroy() {
                this.eGui.removeEventListener('click', this.checkedHandler);
            }
        }

        """)

        df = pd.DataFrame(data)

        # Set up the grid options builder
        gb = GridOptionsBuilder.from_dataframe(df)
        # Configure columns with custom renderer
        for col_name in ['1 - Strongly Disagree', '2 - Disagree', '3 - Neutral', '4 - Agree', '5 - Strongly Agree']:
            gb.configure_column(col_name, editable=True, cellRenderer=checkbox_renderer)

        # Build grid options
        grid_options = gb.build()

        # Display the grid
        response = AgGrid(
            df,
            gridOptions=grid_options,
            allow_unsafe_jscode=True,
            update_mode='MODEL_CHANGED'
        )

        # Update DataFrame if there are changes
        if response:
             df = response['data']
        data = response['data']


        data['age'] = age
        data['gender'] = gender
        data['academic_degree'] = academic_degree
        data['mother_tongue'] = mother_tongue
        st.write("Please describe your understanding of the following concepts:")
        data['equality'] = st.text_area("What is your understanding of equality?", height=150)
        data['proportionality'] = st.text_area("What is your understanding of proportionality?", height=150)
        
        df = pd.DataFrame(data)
        transformed = pd.DataFrame(index=[0])
        
        # Transposing statements into separate columns with responses
        for i, row in df.iterrows():
            # Check each response column
            for col in ['1 - Strongly Disagree', '2 - Disagree', '3 - Neutral', '4 - Agree', '5 - Strongly Agree']:
                if row[col]:
                    # If the value is True, set the column name of the new DataFrame to the statement
                    # and the value to the name of the column where the value was True
                    transformed.loc[0, row['Statement']] = col.replace(" ", "_")
                    
        demographic_cols = ['age', 'gender', 'academic_degree', 'mother_tongue', 'equality', 'proportionality']
        for col in demographic_cols:
            transformed[col] = df[col][0]

        transformed.insert(0, 'ParticipantID', uuid.uuid4())
        # if st.button('Submit Responses', key='submit_survey'):
        #     print("Submitting the following data:", transformed) 
        #     file_path = save_data_to_excel(transformed, 'survey_responses.xlsx')
        #     st.success(f'Thank you for your responses!{file_path}')

        st.session_state.transformed = transformed
        if st.button('Submit', key='submit_resp'):
                st.success(f'Thank you for sharing your background information!') 

    if 'scenario' not in st.session_state:
        st.session_state.scenario = "Work-Study Program"  # Default scenario
    if 'personality' not in st.session_state:
        st.session_state.personality = "Default"  # Default personality
        


    
    elif selection == "Negotiation 1":
        st.header('Welcome to your first Negotiation Chatbot Session')
        st.write("""
            Please engage in a negotiation with this chatbot, powered by GPT-3.5 Turbo. Select the chatbot's personality and your preferred scenario. Start the negotiation by entering your message below, adhering to the role described in the selected scenario. After completing this session, proceed to the next page for a continuation with a GPT-4 Turbo chatbot.
        """)

        # Initialize chat log for Negotiation 1 if not present
        if 'chat_log_1' not in st.session_state:
            st.session_state.chat_log_1 = []

        # Setup and user selections for scenario and personality
        selected_scenario = st.selectbox("Choose a scenario to negotiate:", 
                                        ["Work-Study Program", "Selling a Company", "Bonus Allocation"], 
                                        index=0, key='scenario_select_1')
        selected_personality = st.selectbox("Select negotiation personality of GPT:", 
                                            ["Default", "Proportional", "Equal"], 
                                            index=0, key='personality_select_1')
        st.session_state.scenario = selected_scenario
        st.session_state.personality = selected_personality

        st.write("### Scenario Background")
        st.write(scenarios_backgrounds[selected_scenario])
        
        # Function to handle sending messages
        def send_message_1():
            user_input = st.session_state.user_input_1
            if user_input:
                model_response, updated_chat_log = ask(user_input, st.session_state.chat_log_1, "gpt-3.5-turbo", selected_scenario, selected_personality)
                st.session_state.chat_log_1.append({"role": "user", "content": user_input})
                st.session_state.chat_log_1.append({"role": "assistant", "content": model_response})
                save_data(st.session_state.chat_log_1, 'chat_log_1')
            st.session_state.user_input_1 = ""  # Reset input field

        interactions = len(st.session_state.chat_log_1)
        max_interactions = 12
        if interactions < max_interactions:
            user_input = st.text_input("Enter your message:", key="user_input_1")
            if st.button("Send", on_click=send_message_1):
                pass  # The send_message_1 function will handle everything
        else:
            st.warning("Maximum negotiation rounds reached. Please proceed to the next session.")

        for message in st.session_state.chat_log_1:
            if message['role'] == 'user':
                st.write("You:", message['content'])
            elif message['role'] == 'assistant':
                st.write("AI:", message['content'])
                
        st.session_state.transformed['Scenario'] = st.session_state.scenario
        st.session_state.transformed['GPT_Personality'] = st.session_state.personality
        st.session_state.transformed['Negotiation1'] = [json.dumps(st.session_state.chat_log_1)]

    elif selection == "Negotiation 2":
        st.header('Welcome to your second Negotiation Chatbot Session')
        st.write("""
            Continue your negotiation with this chatbot, analogous to the previous session. Use the same scenario you selected earlier, and negotiate according to your role. Don't forget to press submit negotiations after you have completely finished your negotiation with the chatbot!
        """)

        # Initialize chat log for Negotiation 2 if not present
        if 'chat_log_2' not in st.session_state:
            st.session_state.chat_log_2 = []

        # Retrieve scenario and personality from session state
        scenario = st.session_state.scenario
        personality = st.session_state.personality

        # Function to handle sending messages in Negotiation 2
        def send_message_2():
            user_input = st.session_state.user_input_2
            if user_input:
                model_response, updated_chat_log = ask(user_input, st.session_state.chat_log_2, "gpt-4-turbo", scenario, personality)
                st.session_state.chat_log_2.append({"role": "user", "content": user_input})
                st.session_state.chat_log_2.append({"role": "assistant", "content": model_response})
                save_data(st.session_state.chat_log_2, 'chat_log_2')
            st.session_state.user_input_2 = ""  # Reset input field

        interactions = len(st.session_state.chat_log_2)
        max_interactions = 12
        if interactions < max_interactions:
            user_input = st.text_input("Enter your message:", key="user_input_2")
            if st.button("Send", on_click=send_message_2):
                pass  # The send_message_2 function will handle everything
        else:
            st.warning("Maximum negotiation rounds reached. Your negotiation session is concluded.")

        for message in st.session_state.chat_log_2:
            if message['role'] == 'user':
                st.write("You:", message['content'])
            elif message['role'] == 'assistant':
                st.write("AI:", message['content'])
                
        st.session_state.transformed['Negotiation2'] = [json.dumps(st.session_state.chat_log_2)]
                    
        if st.button('Submit your negotiations', key='submit_neg'):
            #print("Submitting the following data:", transformed) 
            file_path = save_data_to_excel(st.session_state.transformed, 'survey_responses.xlsx')
            st.success(f'Thank you for your participation!{file_path}')        
    
if __name__ == "__main__":
    main()
