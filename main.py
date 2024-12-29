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
from backtest import Backtester

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

df=pl.read_parquet(f'C:\\Users\\{os.getlogin()}\\OneDrive\\Python\\stockdata.parquet')
#df=pl.read_csv(f'stockdata.csv')
app.state.it=''
app.state.df=''
app.state.fig=''

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
    return HTMLResponse(f'''<div hx-post="/edit" hx-swap="outerHTML" class="mockup-code strategy w-full">
    <pre><code class="language-python">{fl}</code></pre></div>''')

@app.post("/select/{item}")
async def read_item(item: str):
    with open(f'strategies\\{item}') as f:
        fl=f.read()
    app.state.it=item
    return HTMLResponse(f'''<div>{item}</div>''')

@app.post("/edit")
async def edit_item():
    with open(f'strategies\\{app.state.it}') as f:
        fl=f.read()
    return HTMLResponse(f'''<div class="mockup-code strategy flex"><form hx-post="/save/" hx-target=".strategy" hx-swap="outerHTML" class="space-y-4 p-6 w-full">
        <button class="btn btn-sm btn-secondary" hx-post="/run" hx-target="#stats" hx-swap="innerHTML">Run</button>
        <button class="btn btn-sm btn-primary" type="submit">Save</button>
        <button class="btn btn-sm btn-primary" hx-post="/strategies/{app.state.it}">Cancel</button>
        <textarea name="cont" spellcheck="false" class="textarea bg-black w-full" 
        style="white-space: pre; min-height:600px;">{fl}</textarea></form></div>''')

@app.post("/save/")
async def save_item(cont: str=Form(...)):
    shutil.copy(f"strategies/{app.state.it}", f"strategies/backups/{app.state.it}.{datetime.now().strftime('%d-%m-%y_%M%S')}")  # Works only in WINDOWS
    with open(f'strategies\\{app.state.it}','w') as f:
        f.write(cont)
    return HTMLResponse(f'''<div hx-post="/edit" hx-swap="outerHTML" class="mockup-code strategy"><pre>
                        <code class="language-python">{cont}</code></pre></div>''')

@app.post("/run")
async def run_strategy(symbol: str = Form(...)):
    print(app.state.it)
    strategy_name = app.state.it
    data = df.filter(pl.col('symbol') == symbol)
    backtester = Backtester(data)
    my_module = SourceFileLoader(strategy_name, f"strategies/{app.state.it}").load_module()
    results, app.state.fig = backtester.apply_strategy(my_module.main)
    stats_df = pd.DataFrame([results])
    stats_html = stats_df.to_html(justify='left',index=False)    
    return HTMLResponse(stats_html.replace("\n", ""))

@app.post("/fig")
async def fig():
    return HTMLResponse(app.state.fig)

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
    return symbol

@app.post("/optimize")
async def run_strategy(symbol: str = Form(...)):
    print(app.state.it)
    strategy_name = app.state.it
    # Filter data by symbol
    data = df.filter(pl.col('symbol') == symbol)
    # Instantiate Backtester
    backtester = Backtester(data)
    # Load the strategy module
    my_module = SourceFileLoader(strategy_name, f"strategies/{app.state.it}").load_module()
    # Apply the strategy
    results, app.state.fig = backtester.apply_strategy(my_module.main,optimize=True)
    # Format results for display
    stats_df = pd.DataFrame([results])
    stats_html = stats_df.to_html(justify='left',index=False)
    return HTMLResponse(stats_html.replace("\n", ""))

@app.get('/strategy')
def page(request:Request):
    seq=os.listdir('strategies')
    file_list=[f for f in seq if os.path.isfile(os.path.join('strategies',f))]
    with open(f'symbols.txt') as f:
        fl=f.readlines()
    return templates.TemplateResponse(request=request,name="strategy.html",context={"seq":file_list,"fl":fl})