import streamlit as st
import pandas as pd
import numpy as np
import arxiv
import requests
import fitz
import plotly.express as px
from sentence_transformers import SentenceTransformer, util
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import tempfile
import spacy
import pytesseract
from pdf2image import convert_from_path
import community.community_louvain as community_louvain
import google.generativeai as genai

# App configuration
st.set_page_config(page_title="Deep Epistemic Research", layout="wide")

# Load models
@st.cache_resource
def load_nlp():
    try:
        return spacy.load("en_core_web_sm")
    except:
        spacy.cli.download("en_core_web_sm")
        return spacy.load("en_core_web_sm")

@st.cache_resource
def load_embedder():
    return SentenceTransformer("all-MiniLM-L6-v2")

nlp = load_nlp()
embedder = load_embedder()
# Gemini configuration (hardcoded key)
GEMINI_API_KEY = "AIzaSyB4Ixz658Bi1IG4CNSTbdD0hgcVg7nKJ2U"
genai.configure(api_key=GEMINI_API_KEY)

#  Epistemic Analyzer
class EpistemicAnalyzer:
    def __init__(self):
        self.hedges = {
            "suggest","imply","indicate","assume","likely","possibly","perhaps",
            "appear","seem","might","may","could","plausible","tentatively",
            "speculate","estimate","roughly"
        }
        self.boosters = {
            "establish","prove","demonstrate","show","confirm","undoubtedly",
            "clearly","obvious","fact","definitely","conclusively","evidence",
            "must","will","always","indisputable","canonical"
        }

    def score(self, text):
        if not text:
            return 0.0
        doc = nlp(text.lower()[:8000])
        tokens = [t.lemma_ for t in doc if t.is_alpha and not t.is_stop]
        b = sum(t in self.boosters for t in tokens)
        h = sum(t in self.hedges for t in tokens)
        total = b + h
        if total == 0:
            return 0.0
        return np.clip((b - 0.8 * h) / np.sqrt(total), -1, 1)

#  Research engine
class ResearchEngine:
    def search(self, query, limit):
        results = []
        client = arxiv.Client()
        search = arxiv.Search(query=query, max_results=limit)
        for r in client.results(search):
            results.append({
                "title": r.title,
                "abstract": r.summary.replace("\n"," "),
                "year": r.published.year,
                "url": r.entry_id
            })
        return results

    def graph(self, papers, threshold=0.5):
        texts = [p["title"] + " " + p["abstract"] for p in papers]
        emb = embedder.encode(texts)
        G = nx.Graph()
        for i,p in enumerate(papers):
            G.add_node(i, label=p["title"], title=p["abstract"][:200])
        sim = util.cos_sim(emb, emb)
        rows, cols = np.where(sim > threshold)
        for r,c in zip(rows, cols):
            if r != c:
                G.add_edge(int(r), int(c), weight=float(sim[r][c]))
        return G

# PDF processing
def process_pdf(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False,suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        path = tmp.name
    doc = fitz.open(path)
    text = "".join(page.get_text() for page in doc)
    if len(text) < 50:
        images = convert_from_path(path)
        text = "".join(pytesseract.image_to_string(img) for img in images)
    return text

#  Session state
if "papers" not in st.session_state:
    st.session_state.papers = []

#  UI
st.title("Epistemic Research")
st.markdown("Academic search, epistemic bias analysis, semantic networks and AI comparison")

tab1, tab2, tab3, tab4 = st.tabs(["Search","Bias Analysis","Networks","Chat"])

# -------------------- TAB 1 -----------------------
with tab1:
    query = st.text_input("Search topic", "quantum gravity")
    limit = st.slider("Number of papers",5,20,10)
    if st.button("Search"):
        engine = ResearchEngine()
        analyzer = EpistemicAnalyzer()
        results = engine.search(query,limit)
        texts = [r["abstract"] for r in results]
        emb = embedder.encode(texts)
        km = KMeans(n_clusters=min(4,len(results)), random_state=42).fit(emb)
        for i,r in enumerate(results):
            r["cluster"] = int(km.labels_[i])
            r["score"] = analyzer.score(r["abstract"])
            r["embedding"] = emb[i]
        st.session_state.papers = results
    if st.session_state.papers:
        st.dataframe(pd.DataFrame(st.session_state.papers)[["title","year","cluster","score"]])

# -------------------- TAB 2 -----------------------
with tab2:
    if st.session_state.papers:
        emb = np.array([p["embedding"] for p in st.session_state.papers])
        coords = PCA(2).fit_transform(emb)
        df = pd.DataFrame(st.session_state.papers)
        df["x"], df["y"] = coords[:,0], coords[:,1]
        fig = px.scatter(df,x="x",y="y",color=df["cluster"].astype(str),
                         size=df["score"].abs()+0.1,hover_data=["title","score"])
        st.plotly_chart(fig,use_container_width=True)

# -------------------- TAB 3 -----------------------
with tab3:
    if st.session_state.papers:
        engine = ResearchEngine()
        G = engine.graph(st.session_state.papers)
        part = community_louvain.best_partition(G)
        net = Network(height="600px", width="100%")
        for n,d in G.nodes(data=True):
            net.add_node(n,label=d["label"],group=part.get(n,0))
        for u,v,d in G.edges(data=True):
            net.add_edge(u,v,value=d.get("weight",1))
        net.save_graph("graph.html")
        components.html(open("graph.html").read(),height=620)

# -------------------- TAB 4 -----------------------
with tab4:
    user_input = st.chat_input("Ask a question")
    if user_input:
        context = ""
        for p in st.session_state.papers[:10]:
            context += f"{p['title']}\n{p['abstract'][:600]}\nScore:{p['score']}\n\n"
        prompt = f"""
You are an academic researcher.
Compare and contrast the following papers:

{context}

Question: {user_input}
"""
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        st.markdown(response.text)
