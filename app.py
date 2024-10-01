import streamlit as st
from openai import OpenAI
from dotenv import dotenv_values 
import json
from pathlib import Path

env = dotenv_values('.env')
openai_client = OpenAI(api_key=env['OPEN_API_KEY'])

#dodanie przeliczników cenowych, 1 token = 1 sylaba
model_pricings = {
    'gpt-4o':{
        'input_tokens' : 5.00 / 1_000_000, #per token
        'output_tokens' : 15.00 / 1_000_000 #per token
    },
    'gpt-4o-mini':{
        'input_tokens' : 0.150 / 1_000_000, #per token
        'output_tokens' : 0.600 / 1_000_000 #per token
    }
}
#dodanie zmiennych związanych z kosztami
MODEL = 'gpt-4o'
USD_TO_PLN = 3.87
PRICING = model_pricings[MODEL]

#
# CHATBOT OPENAI
#

#funkcja generująca odpowiedzi od OpenAI z wbudowaną pamięcią
def get_chatbot_reply(user_prompt, memory):
    #opisz charakter OpenAI
    messages = [
            {
                'role' : 'system',
                'content' : st.session_state['chatbot_personality']
            },
        ]
    #dodaj wszystkie wiadomości do czatu
    for message in memory:
        messages.append({
            'role' : message['role'],
            'content' : message['content']
        })

    #dodaj najnowszą wiadomość użytkownika
    messages.append({
        'role' : 'user',
        'content' : user_prompt
    })

    #łączenie z modelem gpt
    response = openai_client.chat.completions.create(
        model = MODEL,
        messages = messages
    )

    #koszty korzystania z OpenAI
    usage = {}
    if response.usage:
        usage = {
            #INPUT = zapytanie użytkownika
            'prompt_tokens' : response.usage.prompt_tokens,
            #OUTPUT = odpowiedź OpenAI
            'completion_tokens' : response.usage.completion_tokens,
            #INPUT & OUTPUT
            'total_tokens' : response.usage.total_tokens
        }

    return {
        'role' : 'assistant',
        'content' : response.choices[0].message.content,
        'usage' : usage,
    }

#
# CONVERSATION HISTORY AND DATABASE
#

DEFAULT_PERSONALITY = """
Jesteś pomocnikiem, który odpowiada na wszystkie pytania.
Odpowiadaj na pytania w sposób zwięzły i zrozumiały
""".strip()

DB_PATH = Path('db')
DB_CONVERSATIONS_PATH = DB_PATH / 'conversations'
# db/
# ├── current.json
# ├── conversations/
# │   ├── 1.json
# │   ├── 2.json
# │   └── ...

#funkcja ładująca elementy do pamięci session state
def load_conversation_to_session_state(conversation):
    st.session_state['id'] = conversation['id']
    st.session_state['name'] = conversation['name']
    st.session_state['messages'] = conversation['messages']
    st.session_state['chatbot_personality'] = conversation['chatbot_personality']

# WCZYTUJEMY NASZE DANE ZE STRUKTURY

def load_current_conversation():
#sprawdzamy czy istnieje nasza struktura - jeśli NIE, inicjalizujemy ją
    if not DB_PATH.exists():
        DB_PATH.mkdir()
        DB_CONVERSATIONS_PATH.mkdir()
        conversation_id = 1
        conversation = {
            'id' : conversation_id,
            'name' : 'Konwersacja 1',
            'chatbot_personality' : DEFAULT_PERSONALITY,
            'messages' : []
        }
#następnie tworzymy NOWE pliki w naszej strukturze (nowa konwersacja)
        with open(DB_CONVERSATIONS_PATH / f'{conversation_id}.json', 'w') as f:
            f.write(json.dumps(conversation))
#ta konwersacja staje się od razu aktualną
        with open(DB_PATH / 'current.json', 'w') as f:
            f.write(json.dumps({
                'current_conversation_id' : conversation_id
            }))
#jeśli struktura już ISTNIEJE, odczytujemy z niej aktualną konwersację
    else:
#sprawdzamy, która konwersacja jest aktualna
        with open(DB_PATH / 'current.json', 'r') as f:
            data = json.loads(f.read())
            conversation_id = data['current_conversation_id']
#wczytujemy aktualną konwersacje
        with open(DB_CONVERSATIONS_PATH / f'{conversation_id}.json', 'r') as f:
            conversation = json.loads(f.read())

    load_conversation_to_session_state(conversation)

#ZAPISUJEMY NOWE INFORMACJE DO KONWERSACJI

#nowe wiadomości
def save_current_conversation_messages(): 
    conversation_id = st.session_state['id']
    new_messages = st.session_state['messages']
#odczytujemy treść wskazanej konwersacji
    with open(DB_CONVERSATIONS_PATH / f'{conversation_id}.json', 'r') as f:
        conversation = json.loads(f.read())
#nadpisujemy ją poprzez nowe informacje
    with open(DB_CONVERSATIONS_PATH / f'{conversation_id}.json', 'w') as f:
        f.write(json.dumps({
            **conversation,
            'messages' : new_messages
        }))

#nowa nazwa konwersacji
def save_current_conversation_name():
    conversation_id = st.session_state['id']
    new_conversation_name = st.session_state['new_conversation_name']
    #odczytujemy treść wskazanej konwersacji
    with open(DB_CONVERSATIONS_PATH / f'{conversation_id}.json', 'r') as f:
        conversation = json.loads(f.read())
    #nadpisujemy ją poprzez nowe informacje
    with open(DB_CONVERSATIONS_PATH / f'{conversation_id}.json', 'w') as f:
        f.write(json.dumps({
            **conversation,
            'name' : new_conversation_name
        }))

#nowa osobowość
def save_current_conversation_personality():
    conversation_id = st.session_state['id']
    new_chatbot_personality = st.session_state['new_chatbot_personality']
#odczytujemy treść wskazanej konwersacji
    with open(DB_CONVERSATIONS_PATH / f'{conversation_id}.json', 'r') as f:
        conversation = json.loads(f.read())
#nadpisujemy ją poprzez nowe informacje
    with open(DB_CONVERSATIONS_PATH / f'{conversation_id}.json', 'w') as f:
        f.write(json.dumps({
            **conversation,
            'chatbot_personality' : new_chatbot_personality
        }))

#TWORZYMY NOWA KONWERSACJE

def create_new_conversation():
#szukamy id dla naszej kolejnej konwersacji
    conversation_ids = []
#iterujemy po wszystkich plikach .json
    for p in DB_CONVERSATIONS_PATH.glob('*.json'):
#dodajemy do listy wyciągniete nazwy bez rozszerzeń = id
        conversation_ids.append(int(p.stem))
#znajdujemy id dla naszej nowej konwersacji
    conversation_id = max(conversation_ids) + 1
#inicjalizujemy zawartość nowej konwersacji
    personality = DEFAULT_PERSONALITY
#dzięki poniższej instrukcji zostanie wczytana ostatnia zapisana wersja osobowości chatu
    if 'chatbot_personality' in st.session_state and st.session_state['chatbot_personality']:
        personality = st.session_state['chatbot_personality']
    conversation = {
        'id' : conversation_id,
        'name' : f'Konwersacja {conversation_id}',
        'chatbot_personality' : personality,
        'messages' : []
    }
#tworzymy nową konwersacje
    with open(DB_CONVERSATIONS_PATH / f'{conversation_id}.json', 'w') as f:
        f.write(json.dumps(conversation))
#która od razu staje się aktualna
    with open(DB_PATH / 'current.json', 'w') as f:
        f.write(json.dumps({
            'current_conversation_id' : conversation_id
        }))
#dane z nowej konwersacji ładujemy do session state
    load_conversation_to_session_state(conversation)
    st.rerun() #na koniec wymuszamy restart aplikacji

#PRZEŁACZANIE KONWERSACJI MIEDZY SOBA

#najpierw odczytaj mi konwersacje o podanym id
def switch_conversation(conversation_id):
    with open(DB_CONVERSATIONS_PATH / f'{conversation_id}.json', 'r') as f:
        conversation = json.loads(f.read())
#następnie przełącz ją na obecną konwersacje
    with open(DB_PATH / 'current.json', 'w') as f:
        f.write(json.dumps({
            'current_conversation_id' : conversation_id
        }))
    load_conversation_to_session_state(conversation)
    st.rerun()

#WYLISTOWANIE STWORZONYCH KONWERSACJI

def list_conversations():
    conversations = [] #inicjalizujemy pustą listę wszystkich konwersacji
    for p in DB_CONVERSATIONS_PATH.glob('*.json'):
        with open(p, 'r') as f:
            conversation = json.loads(f.read())
            conversations.append({
                'id' : conversation['id'],
                'name' : conversation['name']
            })
    return conversations #zwracamy listę wszystkich konwersacji

#
# MAIN PROGRAM
#

#wczytywanie historii rozmów z naszej bazy danych (utworzonej przez nas struktury)
load_current_conversation()

#tytuł aplikacji
st.title(':classical_building: Nasz GPT')

#zapamiętywanie starych wiadomości z czatu
for message in st.session_state['messages']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

#ustawienia zapytań i odpowiedzi
prompt = st.chat_input('O co chcesz spytać?')

if prompt:
#zapytanie użytkownika
    user_message = {'role' : 'user', 'content' : prompt}
    with st.chat_message('user'): #dodanie wiadomości do czatu
        st.markdown(user_message['content'])

#zapisanie zapytania użytkownika w pamięci
    st.session_state['messages'].append(user_message)
                                        
#odpowiedź OpenAI
    with st.chat_message('assistant'):
        chatbot_message = get_chatbot_reply(
            prompt, memory = st.session_state['messages'][-20:])
        st.markdown(chatbot_message['content'])

#zapisanie odpowiedzi OpenAI
    st.session_state['messages'].append(chatbot_message)

    save_current_conversation_messages() #zapisanie wszystkich wiadomości
    
#
#PASEK BOCZNY
#

with st.sidebar:
#wyświetlenie ustawionego aktualnie modelu czatu gpt
    st.write(f'Aktualny model: {MODEL}')

 #obliczenie kosztów
    total_cost = 0
    for message in st.session_state['messages']:
        if 'usage' in message:
            total_cost += message['usage']['prompt_tokens'] * PRICING['input_tokens']
            total_cost += message['usage']['completion_tokens'] * PRICING['output_tokens']

#wyświetlenie kosztów
    c0, c1 = st.columns(2)
    with c0:
        st.metric('Koszt rozmowy (USD): ', f'${total_cost:.4f}')
    with c1:
        st.metric('Koszt rozmowy (PLN): ', f'{total_cost * USD_TO_PLN:.4f}')

#wyświetlenie nazwy konwersacji
    st.session_state['name'] = st.text_input(
        'Nazwa konwersacji',
        value = st.session_state['name'],
        key = 'new_conversation_name',
        on_change = save_current_conversation_name 
        #on_change - pozwala na przekazanie funkcji jako argumentu
    )

#wyświetlenie osobowości OpenAI - pole do modyfikacji
    st.session_state['chatbot_personality'] = st.text_area(
        'Osobowość chatbota',
        max_chars = 1000,
        height = 200,
        value=st.session_state["chatbot_personality"],
        key = 'new_chatbot_personality',
        on_change = save_current_conversation_personality
    )

#tworzenie nowych konwersacji
    st.subheader('Konwersacje')
    if st.button('Nowa konwersacja'):
        create_new_conversation()

#sortowanie konwersacji i możliwość przełączania pomiędzy nimi
    conversations = list_conversations() 
    sorted_conversations = sorted(conversations, key=lambda x: x['id'], reverse=True)
    for conversation in sorted_conversations[:5]: #pokazujemy tylko top 5 konwersacji
        c0, c1 = st.columns([10, 5])
        with c0:
            st.write(conversation['name'])
        with c1:
            if st.button('Załaduj', key= conversation['id'], disabled=conversation['id'] == st.session_state['id']):
                switch_conversation(conversation['id'])






