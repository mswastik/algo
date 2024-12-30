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
from pyecharts.charts import Bar, Candlestick, Kline, Scatter
from pyecharts import options as opts

pd.options.display.float_format = '{:,.2f}'.format

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

df=pl.read_parquet(f'C:\\Users\\{os.getlogin()}\\OneDrive\\Python\\stockdata.parquet')
#df=pl.read_csv(f'stockdata.csv')
app.state.it=''
app.state.df=''
app.state.fig=''
app.state.stats=''
app.state.sym=''
app.state.tradeplot=False
app.state.trades=''

col=['Start','End','Duration','Exposure Time [%]','Equity Final [$]','Equity Peak [$]','Return [%]','Buy & Hold Return [%]','Return (Ann.) [%]','Volatility (Ann.) [%]',
    'Sharpe Ratio',	'Sortino Ratio','Calmar Ratio',	'Max. Drawdown [%]','Avg. Drawdown [%]','Max. Drawdown Duration','Avg. Drawdown Duration','# Trades','Win Rate [%]',
    'Best Trade [%]','Worst Trade [%]','Avg. Trade [%]','Max. Trade Duration','Avg. Trade Duration','Profit Factor','Expectancy [%]','SQN']

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
'''
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
'''

@app.post("/run")
async def run_strategy(symbol: str = Form(...)):
    strategy_name = app.state.it
    #df1 = df.filter(pl.col('symbol') == symbol).drop('symbol').sort('date',descending=False)
    #df1=df1.rename({'open':"Open",'high':'High','low':'Low','close':"Close",'volume':'Volume'})
    #df1=app.state.df.rename({'open':"Open",'high':'High','low':'Low','close':"Close",'volume':'Volume'})
    df1=app.state.df.clone()
    my_module = SourceFileLoader(strategy_name, f"strategies/{app.state.it}").load_module()
    stats = my_module.main(df1.to_pandas().set_index('date'))
    # Format results for display
    app.state.trades=stats['_trades']
    stats_df = pd.DataFrame([stats])
    app.state.stats=stats_df
    stats_html = stats_df.iloc[:,0:-3].T.to_html(justify='left',index=True,header=False)
    return HTMLResponse(stats_html.replace("\n", ""))

@app.post("/fig")
async def fig():
    #return HTMLResponse(app.state.fig)
    df=app.state.df.to_pandas()
    bar = (
    Candlestick(init_opts=opts.InitOpts(height="600px",width="1320px"))
    .add_xaxis(df['date'].astype('str').tolist())
    .add_yaxis(series_name="", y_axis=df[['Open','Close','Low','High']].to_numpy().tolist(),itemstyle_opts=opts.ItemStyleOpts(color="#00da3c",border_color="#00da3c", color0="#ec0000",border_color0="#ec0000"),)
    #.add_dataset(data=list(df['open','high','low','close','gain'].to_numpy().tolist()),)
    .set_global_opts(title_opts=opts.TitleOpts(title=app.state.sym), datazoom_opts=[
        opts.DataZoomOpts(is_show=False,type_="inside",xaxis_index=[0, 1],range_start=90,range_end=100,),
        opts.DataZoomOpts(is_show=True,xaxis_index=[0, 5],type_="slider",pos_bottom="5%",range_start=85,range_end=100,)],
        tooltip_opts=opts.TooltipOpts(trigger="axis",axis_pointer_type="cross",background_color="rgba(245, 245, 245, 0.8)",border_width=1,border_color="#ccc",textstyle_opts=opts.TextStyleOpts(color="#000"),),))
    #print(bar.render_embed())
#if app.state.tradeplot:
    s1=Scatter().add_xaxis(app.state.trades['EntryTime'].astype('str').tolist()).add_yaxis('Entry',app.state.trades['EntryPrice'].tolist(),symbol_size=15,symbol='triangle')
    s2=Scatter().add_xaxis(app.state.trades['ExitTime'].astype('str').tolist()).add_yaxis('Exit',app.state.trades['ExitPrice'].tolist(),symbol_size=15,symbol='triangle')
    s2.options['series'][0]['symbolRotate']=180
    s1.options['series'][0]['itemStyle']={ 'color': 'yellow'}
    s2.options['series'][0]['itemStyle']={ 'color': 'blue'}
    bar=bar.overlap(s1)
    bar=bar.overlap(s2)
    return HTMLResponse(bar.render_embed())

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
    df1=df1.rename({'open':"Open",'high':'High','low':'Low','close':"Close",'volume':'Volume'})
    df1=df1.sort('date',descending=False)
    app.state.df=df1
    app.state.sym=symbol
    return symbol
'''
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
'''
@app.post("/optimize")
async def run_strategy(symbol: str = Form(...)):
    strategy_name = app.state.it
    #df1 = df.filter(pl.col('symbol') == symbol).drop('symbol').sort('date',descending=False)
    #df1=df1.rename({'open':"Open",'high':'High','low':'Low','close':"Close",'volume':'Volume'})
    #df1=app.state.df.rename({'open':"Open",'high':'High','low':'Low','close':"Close",'volume':'Volume'})
    df1=app.state.df.clone()
    my_module = SourceFileLoader(strategy_name, f"strategies/{app.state.it}").load_module()
    stats = my_module.optimize(df1.to_pandas().set_index('date'))
    # Format results for display
    app.state.trades=stats['_trades']
    stats_df = pd.DataFrame([stats])
    app.state.stats=stats_df.copy()
    stats_html = stats_df.iloc[:,0:-3].T.to_html(justify='left',index=True,header=False)
    app.state.tradeplot=True
    return HTMLResponse(stats_html.replace("\n", ""))

@app.get('/strategy')
def page(request:Request):
    seq=os.listdir('strategies')
    file_list=[f for f in seq if os.path.isfile(os.path.join('strategies',f))]
    with open(f'symbols.txt') as f:
        fl=f.readlines()
    return templates.TemplateResponse(request=request,name="strategy.html",context={"seq":file_list,"fl":fl})