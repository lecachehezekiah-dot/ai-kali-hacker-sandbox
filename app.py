import os, subprocess, paramiko, base64, io
from flask import Flask, request, jsonify, render_template, Response
from flask_socketio import SocketIO, emit
import ollama
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.vectorstores import Chroma
from langchain.embeddings import OllamaEmbeddings
import threading, time, json

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
clients = {}  # Track sandbox sessions

# AI Memory (learns from hacks)
embeddings = OllamaEmbeddings(model="llama3.1:8b")
vectorstore = Chroma(persist_directory="./ai_memory", embedding_function=embeddings)

# OP Hacking AI
llm = Ollama(model="llama3.1:8b")
HACK_PROMPT = PromptTemplate(
    input_variables=["query", "memory", "tools"],
    template="""You are ELITE HACKER AI. Ubuntu/Kali Linux expert.

Memory: {memory}
Available: nmap, msfconsole, nuclei, sqlmap, hydra, burpsuite, custom exploits

User: {query}

OUTPUT JSON ONLY:
{{
  "analysis": "What it does",
  "command": "bash command here",
  "tools": ["msf", "nuclei", "custom"],
  "risk": "low/medium/high",
  "learn": "What you learned"
}}"""
)
hack_chain = LLMChain(llm=llm, prompt=HACK_PROMPT)

class Sandbox:
    def __init__(self, distro="ubuntu"):
        self.distro = distro
        self.port_vnc = 5901 + len(clients)
        self.port_ws = 6080 + len(clients)
        self.session_id = f"{distro}_{self.port_vnc}"
        clients[self.session_id] = self
        self.start_sandbox()
    
    def start_sandbox(self):
        cmd = f"""
        sudo apt update -qq
        sudo apt install -y kali-linux-default xvfb fluxbox tightvncserver novnc
        export DISPLAY=:{self.port_vnc-5900}
        Xvfb :{self.port_vnc-5900} -screen 0 1920x1080x24 > /dev/null 2>&1 &
        vncserver :{self.port_vnc-5900} -geometry 1920x1080 -depth 24 -localhost no
        websockify {self.port_ws} localhost:{self.port_vnc} > /dev/null 2>&1 &
        """
        subprocess.Popen(cmd, shell=True)
        time.sleep(3)

def exec_cmd(session_id, cmd):
    sandbox = clients[session_id]
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('localhost', 22, 'kali', 'kali')
    stdin, stdout, stderr = ssh.exec_command(cmd)
    result = stdout.read().decode() + stderr.read().decode()
    ssh.close()
    # AI LEARNS
    vectorstore.add_texts([f"Command: {cmd}\nResult: {result}"])
    return result

@socketio.on('hack')
def ai_hack(data):
    query = data['query']
    session_id = data['session']
    
    # Get AI memory
    memory = vectorstore.similarity_search(query, k=3)
    memory_text = "\n".join([doc.page_content for doc in memory])
    
    # Generate attack
    response = hack_chain.run(query=query, memory=memory_text, tools="all pentest tools")
    hack_plan = json.loads(response)
    
    # Execute
    output = exec_cmd(session_id, hack_plan['command'])
    
    emit('hack_result', {
        'plan': hack_plan,
        'output': output,
        'vnc': f"http://3000-{socketio.server.environ['GITPOD_WORKSPACE_ID']}.ws-us.gitpod.io:{clients[session_id].port_ws}/vnc.html?autoconnect=true"
    })

@app.route('/')
def dashboard():
    return render_template('index.html')

@app.route('/sandbox/<distro>')
def create_sandbox(distro):
    sandbox = Sandbox(distro)
    return jsonify({'session_id': sandbox.session_id, 'vnc_port': sandbox.port_ws})

@app.route('/vnc_proxy')
def vnc_proxy():
    return """
    <!DOCTYPE html>
    <html><body>
    <iframe src="/vnc.html?port=6080" width="100%" height="800px"></iframe>
    </body></html>
    """

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, debug=True)
