import os
import streamlit as st
from sentence_transformers import SentenceTransformer, util
import json
import torch
import requests
import ast

# --- Constants ---
MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
TOP_K = 3
BASE_FILE = 'sklearn_knowledge_base.jsonl'
EMBEDDINGS_CACHE = 'embeddings.pt'
MAX_PROMPT_LINES = 50  # макс. строк кода в промпте

# --- Streamlit UI ---
st.title('Code Assistant for Scikit-learn')

# --- Retrieve API Key (manual input) ---
API_KEY = st.text_input('Введите YandexGPT API-ключ', type='password')
if not API_KEY:
    st.warning('Введите API-ключ в поле выше')
    st.stop()

mode = st.radio('Режим поиска', ['Semantic', 'Grep'])
user_query = st.text_input('Введите запрос')

# --- Load articles ---
@st.cache_data
def load_articles(path):
    with open(path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f]

articles = load_articles(BASE_FILE)
texts = [art['content'] + ' ' + ' '.join(art.get('queries', [])) for art in articles]

# --- Load model ---
@st.cache_resource
def load_model():
    return SentenceTransformer(MODEL_NAME)

model = load_model()

# --- Encode or load embeddings ---
@st.cache_data
def load_embeddings(texts):
    if os.path.exists(EMBEDDINGS_CACHE):
        return torch.load(EMBEDDINGS_CACHE)
    embeddings = model.encode(texts, convert_to_tensor=True)
    torch.save(embeddings, EMBEDDINGS_CACHE)
    return embeddings

article_embeddings = load_embeddings(texts)

# --- Grep search ---
def grep_search(keyword, articles, top_k=TOP_K):
    keyword = keyword.lower()
    hits = []
    for art in articles:
        cnt = art['content'].lower().count(keyword)
        if cnt > 0:
            hits.append((art, cnt))
    hits.sort(key=lambda x: x[1], reverse=True)
    return [art for art,_ in hits[:top_k]]

# --- Prompt generation ---
def trim_content(content):
    lines = content.splitlines()
    if len(lines) > MAX_PROMPT_LINES:
        return '\n'.join(lines[:MAX_PROMPT_LINES]) + '\n#... (truncated)'
    return content


def generate_prompt(article, question):
    snippet = trim_content(article['content'])
    return f"""Код ({article.get('path','<unknown>')}):
{snippet}

Комментарий:
Этот фрагмент выбран, потому что отвечает на запрос: \"{question}\"

Запрос пользователя:
{question}"""

# --- Call YandexGPT ---
def call_yandex_gpt(prompt):
    headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
    data = {
        'modelUri': 'gpt://b1gsbr4nrvr3j95f6nqp/yandexgpt-lite',
        'completionOptions': {'stream': False, 'temperature': 0.6, 'maxTokens': '2000'},
        'messages': [
            {'role': 'system', 'text': 'Ты — интеллектуальный помощник, отвечающий на основе кода.'},
            {'role': 'user', 'text': prompt}
        ]
    }
    resp = requests.post(
        'https://llm.api.cloud.yandex.net/foundationModels/v1/completion',
        headers=headers, json=data
    )
    if resp.status_code == 200:
        return resp.json().get('result', {}).get('alternatives', [{}])[0].get('message', {}).get('text', '')
    else:
        st.error(f'Ошибка API: {resp.status_code} {resp.text}')
        return None

# --- Main logic ---
if user_query:
    # первичный поиск
    if mode == 'Grep' and user_query.lower().startswith('grep:'):
        key = user_query.split(':',1)[1].strip()
        top = grep_search(key, articles)
        st.write(f'🔎 Grep-режим: найдено {len(top)} фрагментов по "{key}"')
    else:
        q_emb = model.encode(user_query, convert_to_tensor=True)
        scores = util.pytorch_cos_sim(q_emb, article_embeddings)[0]
        idxs = torch.topk(scores, k=TOP_K).indices
        top = [articles[i] for i in idxs]
        st.write(f'🔍 Семантический режим: топ {len(top)} фрагментов')
    
    # отображаем сниппеты
    for i, art in enumerate(top, 1):
        st.subheader(f"{i}. {art['title']} [{art.get('path','')}] ")
        st.code(trim_content(art['content']), language='python')
    
    # уточняющий вопрос по первому сниппету (для grep-режима)
    if mode == 'Grep':
        followup = st.text_input('Задайте вопрос по выбранному фрагменту', '')
    else:
        followup = user_query
    
    if followup:
        prompt = generate_prompt(top[0], followup)
        st.markdown('**Сформированный промпт:**')
        st.text_area('Prompt', prompt, height=200)
        if st.button('Отправить в YandexGPT'):
            with st.spinner('Получение ответа...'):
                answer = call_yandex_gpt(prompt)
            if answer:
                st.subheader('Ответ YandexGPT')
                st.write(answer)
            else:
                st.error('Не удалось получить ответ от модели.')
