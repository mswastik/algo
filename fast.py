from typing import Union

from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from datetime import datetime
from typing import Annotated

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

foo = {}
app.state.it=''

@app.get("/")
def read_root(request:Request):
    #return {"Hello": "World"}
    seq=os.listdir('strategies')
    return templates.TemplateResponse(request=request,name="index.html",context={"seq":seq})

@app.post("/strategies/{item}")
def read_item(item: str):
    with open(f'strategies\\{item}') as f:
        fl=f.read()
    app.state.it=item
    print(item)
    #co=[f"<pre class='strategy'><code class='language-python'>{f}</code></pre>" for f in fl]
    #print(' '.join(co))
    #return HTMLResponse(f"<pre class='strategy'><code class='language-python'>{fl}</code></pre>")
    return HTMLResponse(f'''<div hx-post="/edit" hx-swap="outerHTML" class="mockup-code strategy"><pre><code class="language-python">{fl}</code></pre></div>''')

@app.post("/edit")
async def edit_item():
    with open(f'strategies\\{app.state.it}') as f:
        fl=f.read()
    #co=[f"<pre class='strategy'><code class='language-python'>{f}</code></pre>" for f in fl]
    #return HTMLResponse(f"<pre class='strategy'><code class='language-python'>{fl}</code></pre>")
    return HTMLResponse(f'''<div class="mockup-code strategy"><form hx-post="/save/" hx-target=".strategy" hx-swap="outerHTML"><button class="btn btn-primary px-3 mx-5 my-2" type="submit">Save</button>
        <textarea name="cont" spellcheck="false" class="textarea bg-gray-800 resize-none" 
        style="white-space: pre; min-width:90%; min-height:600px;">{fl}</textarea></form></div>''')

@app.post("/save/")
async def save_item(cont: str=Form(...)):
    #print(cont)
    os.popen(f'copy {app.state.it} /backup/{app.state.it.join(datetime.now().strftime('%d-%m-%y %M%S'))}')  # Works only in WINDOWS
    #with open(f'strategies\\backup\\{app.state.it}','w') as f:
    #    f.write(item.join(datetime.now().strftime()))
    #co=[f"<pre class='strategy'><code class='language-python'>{f}</code></pre>" for f in fl]
    #print(' '.join(co))
    #return HTMLResponse(f"<pre class='strategy'><code class='language-python'>{fl}</code></pre>")
    return HTMLResponse(f'<div hx-post="/edit" hx-swap="outerHTML" class="mockup-code strategy"><pre><code class="language-python">{cont}</code></pre></div>')