from typing import Union

from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from datetime import datetime
from typing import Annotated
import shutil
from importlib.machinery import SourceFileLoader
import polars as pl
import pandas as pd

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

df=pl.read_parquet(f'C:\\Users\\{os.getlogin()}\\OneDrive\\Python\\stockdata.parquet')
app.state.it=''
app.state.df=''

@app.get("/")
async def read_root(request:Request):
    seq=os.listdir('strategies')
    file_list=[f for f in seq if os.path.isfile(os.path.join('strategies',f))]
    with open(f'symbols.txt') as f:
        fl=f.readlines()
    return templates.TemplateResponse(request=request,name="index.html",context={"seq":file_list,"fl":fl})

@app.post("/strategies/{item}")
async def read_item(item: str):
    with open(f'strategies\\{item}') as f:
        fl=f.read()
    app.state.it=item
    print(item)
    return HTMLResponse(f'''<div hx-post="/edit" hx-swap="outerHTML" class="mockup-code strategy w-full">
    <button class="btn btn-sm btn-secondary mx-5" hx-post="/run" hx-target="#stats" hx-swap="innerHTML">Run</button>
    <pre><code class="language-python">{fl}</code></pre></div>''')

@app.post("/edit")
async def edit_item():
    with open(f'strategies\\{app.state.it}') as f:
        fl=f.read()
    return HTMLResponse(f'''<div class="mockup-code strategy flex"><form hx-post="/save/" hx-target=".strategy" hx-swap="outerHTML" class="space-y-4 p-6 w-full">
        <button class="btn btn-sm btn-secondary" hx-post="/run" hx-target="#stats" hx-swap="innerHTML">Run</button>
        <button class="btn btn-sm btn-primary" type="submit">Save</button>
        <button class="btn btn-sm btn-primary" hx-post="/strategies/{app.state.it}">Cancel</button>
        <textarea name="cont" spellcheck="false" class="textarea bg-gray-800 w-full" 
        style="white-space: pre; min-height:600px;">{fl}</textarea></form></div>''')

@app.post("/save/")
async def save_item(cont: str=Form(...)):
    shutil.copy(f"strategies/{app.state.it}", f"strategies/backups/{app.state.it}.{datetime.now().strftime('%d-%m-%y_%M%S')}")  # Works only in WINDOWS
    with open(f'strategies\\{app.state.it}','w') as f:
        f.write(cont)
    return HTMLResponse(f'<div hx-post="/edit" hx-swap="outerHTML" class="mockup-code strategy"><pre><code class="language-python">{cont}</code></pre></div>')

@app.post("/run")
async def edit_item():
    print(app.state.it[:-3])
    my_module = SourceFileLoader('my_module', f"strategies/{app.state.it}").load_module()
    bt, stats=my_module.main(app.state.df)
    st=pd.DataFrame(stats,columns=['stat'])
    st=st.drop(['_equity_curve','_trades']).to_html()
    bt.plot(plot_return=False)
    return st.replace("\n", "")

@app.post("/new")
async def new_item(filename: str=Form(...)):
    file_path = f"{filename}.py"
    if os.path.exists(file_path):
        return {"message": "File already exists"}
    with open(f'strategies\\{file_path}', "w") as file:
        file.write("")
    return HTMLResponse(f'<div hx-post="/edit" hx-swap="outerHTML" class="mockup-code strategy"><pre><code class="language-python">{cont}</code></pre></div>')

@app.post("/loaddata")
async def edit_item(symbol: str=Form(...)):
    df1=df.filter(pl.col('symbol')==symbol)
    app.state.df=df1
    #print("loading  ".join(app.state.df))
    return symbol