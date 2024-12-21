from typing import Union

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
def read_root(request:Request):
    #return {"Hello": "World"}
    seq=os.listdir('strategies')
    return templates.TemplateResponse(request=request,name="index.html",context={"seq":seq})

@app.post("/strategies/{item}")
def read_item(item: str):
    with open(f'strategies\\{item}') as f:
        fl=f.read()
    #co=[f"<pre class='strategy'><code class='language-python'>{f}</code></pre>" for f in fl]
    #print(' '.join(co))
    #return HTMLResponse(f"<pre class='strategy'><code class='language-python'>{fl}</code></pre>")
    return HTMLResponse(f'<pre class="strategy w-8/12"><code class="language-python">{fl}</code></pre>')

@app.post("/strategies/edit/{item}")
def edit_item(item: str):
    with open(f'strategies\\{item}') as f:
        fl=f.read()
    #co=[f"<pre class='strategy'><code class='language-python'>{f}</code></pre>" for f in fl]
    #return HTMLResponse(f"<pre class='strategy'><code class='language-python'>{fl}</code></pre>")
    return HTMLResponse(f'<textarea class="textarea mockup-code strategy bg-gray-800 min-h-16" style="white-space: pre;">{fl}</textarea>')