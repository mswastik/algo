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
from pyecharts.charts import Bar, Candlestick, Kline, Scatter, Line
from pyecharts import options as opts
import pickle
from bs4 import BeautifulSoup
from pyecharts.commons.utils import JsCode
from data import fyers_login, fetch_data, save_to_parquet, update_parquet_data
#import sys
#sys.path.append("strategies")
#from macd import MACDStrategy

pd.options.display.float_format = '{:,.2f}'.format

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def load():
    df=pl.read_parquet(f'C:\\Users\\{os.getlogin()}\\OneDrive\\Python\\stockdata.parquet')
    df=df.rename({'open':"Open",'high':'High','low':'Low','close':"Close",'volume':'Volume'})
    df=df.sort('date',descending=False)
    #df=pl.read_csv(f'stockdata.csv')
    return df
df=load()
app.state.sl=''
app.state.df=''
app.state.fig=''
app.state.stats=''
app.state.sym=''
app.state.trades=''
app.state.fyers=''

col=['Start','End','Duration','Exposure Time [%]','Equity Final [$]','Equity Peak [$]','Return [%]','Buy & Hold Return [%]','Return (Ann.) [%]','Volatility (Ann.) [%]',
    'Sharpe Ratio',	'Sortino Ratio','Calmar Ratio',	'Max. Drawdown [%]','Avg. Drawdown [%]','Max. Drawdown Duration','Avg. Drawdown Duration','# Trades','Win Rate [%]',
    'Best Trade [%]','Worst Trade [%]','Avg. Trade [%]','Max. Trade Duration','Avg. Trade Duration','Profit Factor','Expectancy [%]','SQN']

runs=pd.read_pickle('runs.pkl')
with open('symbols.txt') as f:
    fl=f.read()
fl=fl[1:-1].strip().replace("'","").replace(" ","").split(',')
#print(fl)
@app.get("/")
async def read_root(request:Request):
    seq=os.listdir('strategies')
    file_list=[f for f in seq if os.path.isfile(os.path.join('strategies',f))] 
    rd=runs[['Symbol','Strategy','Return (Ann.) [%]']].to_html(justify='left',classes=['table table-sm'])
    soup = BeautifulSoup(rd,"html.parser")
    for tag in soup.findAll('tr'):
        if tag.find('th').contents:
            tag['hx-get']='/getruns/'+str(tag.find('th').contents[0])
            tag['hx-target']="#stats"
            tag['class']='cursor-pointer border-b transition-colors hover'
    return templates.TemplateResponse(request=request,name="index.html",context={"seq":file_list,"fl":fl,'runs':soup})

@app.post("/strategies/{item}")
async def read_item(item: str):
    with open(f'strategies\\{item}') as f:
        sl=f.read()
    app.state.sl=item
    return HTMLResponse(f'''<div hx-post="/edit" hx-swap="outerHTML" class="mockup-code strategy w-full">
    <pre><code class="language-python">{sl}</code></pre></div>''')

@app.post("/select/{item}")
async def read_item(item: str):
    with open(f'strategies\\{item}') as f:
        sl=f.read()
    app.state.sl=item
    return HTMLResponse(f'''<div>{item}</div>''')

@app.post("/edit")
async def edit_item():
    with open(f'strategies\\{app.state.sl}') as f:
        sl=f.read()
    return HTMLResponse(f'''<div class="mockup-code strategy flex"><form hx-post="/save/" hx-target=".strategy" hx-swap="outerHTML" class="space-y-4 p-6 w-full">
        <button class="btn btn-sm btn-secondary" hx-post="/run" hx-target="#stats" hx-swap="innerHTML">Run</button>
        <button class="btn btn-sm btn-primary" type="submit">Save</button>
        <button class="btn btn-sm btn-primary" hx-post="/strategies/{app.state.sl}">Cancel</button>
        <textarea name="cont" spellcheck="false" class="textarea bg-black w-full" 
        style="white-space: pre; min-height:600px;">{sl}</textarea></form></div>''')

@app.post("/save/")
async def save_item(cont: str=Form(...)):
    shutil.copy(f"strategies/{app.state.sl}", f"strategies/backups/{app.state.sl}.{datetime.now().strftime('%d-%m-%y_%M%S')}")  # Works only in WINDOWS
    with open(f'strategies\\{app.state.sl}','w') as f:
        f.write(cont)
    return HTMLResponse(f'''<div hx-post="/edit" hx-swap="outerHTML" class="mockup-code strategy"><pre>
                        <code class="language-python">{cont}</code></pre></div>''')

@app.post("/run")
async def run_strategy(symbol: str = Form(...)):
    strategy_name = app.state.sl
    df1=app.state.df.clone()
    my_module = SourceFileLoader(strategy_name, f"strategies/{app.state.sl}").load_module()
    stats = my_module.main(df1.to_pandas().set_index('date'))
    app.state.trades=stats['_trades']
    stats_df = pd.DataFrame([stats])
    app.state.stats=stats_df
    stats_html = stats_df.iloc[:,0:-3].T.to_html(justify='left',index=True,header=False)
    return HTMLResponse(stats_html.replace("\n", ""))

@app.post("/fig")
async def fig():
    df2=app.state.df.to_pandas().copy()
    df2=df2.round({'Open':1,'Close':1,'Low':1,'High':1})
    bar = (
    Candlestick(init_opts=opts.InitOpts(height="600px",width="1320px"))
    .add_xaxis(df2['date'].astype('str').tolist())
    .add_yaxis(series_name="", y_axis=df2[['Open','Close','Low','High']].to_numpy().tolist(),itemstyle_opts=opts.ItemStyleOpts(color="#00da3c",border_color="#00da3c",
         color0="#ec0000",border_color0="#ec0000"))
    .set_global_opts(title_opts=opts.TitleOpts(title=app.state.sym), datazoom_opts=[
        opts.DataZoomOpts(is_show=False,type_="inside",xaxis_index=[0, 1],range_start=90,range_end=100,),
        opts.DataZoomOpts(is_show=True,xaxis_index=[0, 5],type_="slider",pos_bottom="5%",range_start=85,range_end=100,)],
        tooltip_opts=opts.TooltipOpts(trigger="axis",axis_pointer_type="cross",background_color="rgba(245, 245, 245, 0.8)",border_width=1,border_color="#ccc",textstyle_opts=opts.TextStyleOpts(color="#000"),),))
    s1=Scatter().add_xaxis(app.state.trades['EntryTime'].astype('str').tolist()).add_yaxis('Entry',app.state.trades['EntryPrice'].tolist(),symbol_size=15,symbol='triangle',
    label_opts=opts.LabelOpts(is_show=False))
    s2=Scatter().add_xaxis(app.state.trades['ExitTime'].astype('str').tolist()).add_yaxis('Exit',app.state.trades['ExitPrice'].tolist(),symbol_size=15,symbol='triangle',
        #label_opts=opts.LabelOpts(is_show=True,formatter=JsCode("function(param) {return Number(param.data[1]).toFixed(0);}")))
        label_opts=opts.LabelOpts(is_show=False))
    s2.options['series'][0]['symbolRotate']=180
    s1.options['series'][0]['itemStyle']={ 'color': 'brown'}
    s2.options['series'][0]['itemStyle']={ 'color': 'blue'}
    bar=bar.overlap(s1)
    bar=bar.overlap(s2)
    for i,n in app.state.trades.iterrows():
        col='red' if n['PnL']<=0 else 'green'
        l=Line().add_xaxis([n['EntryTime'].strftime("%Y-%m-%d"),n['ExitTime'].strftime("%Y-%m-%d")]).add_yaxis(series_name='Trades',y_axis=[n['EntryPrice'],n['ExitPrice']],label_opts=opts.LabelOpts(is_show=False)
        ,linestyle_opts=opts.LineStyleOpts(width=2,color=col))
        bar.overlap(l)
    htstr=bar.render_embed()
    soup=BeautifulSoup(htstr,features="lxml")
    tags=soup.find('div')
    '''for tag in tags:
        #try:
        current_style = tag.get('style', '')
        styles = {}
        for item in current_style.split(';'):
            item = item.strip()
            if item and ':' in item:
                key, value = item.split(':', 1)
                styles[key.strip()] = value.strip()
        styles.pop('width', None)
        styles.pop('height', None)
        styles['width'] = '1320px'
        styles['height'] = '600px'
        tag['style'] = '; '.join(f'{k}: {v}' for k, v in styles.items())
        #except:
        #    tag['style']='width:1320px;height:600px'
        '''
    tags['style']="width:1320px;height:600px"
    return HTMLResponse(soup.body)

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
    app.state.sym=symbol
    return symbol

@app.post("/optimize")
async def run_strategy(symbol: str = Form(...)):
    strategy_name = app.state.sl
    df1=app.state.df.clone()
    my_module = SourceFileLoader(strategy_name, f"strategies/{app.state.sl}").load_module()
    stats = my_module.optimize(df1.to_pandas().set_index('date'))
    app.state.trades=stats[0]['_trades']
    stats_df = pd.DataFrame([stats[0]])
    stats_df['best_params']=[stats[1].x]
    print(stats_df)
    app.state.stats=stats_df.copy()
    stats_html = stats_df.iloc[:,0:-3].T.to_html(justify='left',index=True,header=False)
    return HTMLResponse(stats_html.replace("\n", ""))

@app.get('/strategy')
async def page(request:Request):
    seq=os.listdir('strategies')
    file_list=[f for f in seq if os.path.isfile(os.path.join('strategies',f))]
    return templates.TemplateResponse(request=request,name="strategy.html",context={"seq":file_list,"fl":fl})

@app.get('/saveruns')
async def page(request:Request):
    global runs
    run=app.state.stats
    run=run.drop(columns=['_strategy'])
    run["Symbol"]=app.state.sym
    run["Strategy"]=app.state.sl
    runs=pd.concat([runs,run],ignore_index=True)
    runs.to_pickle('runs.pkl')

@app.get('/getruns/{ind}')
async def page(request:Request,ind:int):
    rd=pd.DataFrame(runs.iloc[ind])
    app.state.trades=pd.DataFrame(rd.loc['_trades'][ind])
    rd=rd.drop(['_equity_curve','_trades'])
    rd=rd.rename(columns={0:"Stats"})
    app.state.sym=rd.loc['Symbol'].values[0]
    app.state.df=df.filter(pl.col('symbol')==app.state.sym)
    return HTMLResponse(rd.to_html(justify='left',classes=['table table-xs']))

@app.get('/data')
async def page(request:Request):
    return templates.TemplateResponse(request=request,name='data.html',context={'fl':', '.join(fl)})

@app.post('/saveconfig')
async def page(sym: str=Form()):
    print(sym.strip().split('/n').__str__())
    open('symbols.txt','w').write(sym.strip().split('/n').__str__())

@app.post('/getdata')
async def getd(sym: str=Form()):
    for i in sym.strip().split(','):
        update_parquet_data(i.strip(),app.state.fyers)

@app.post('/login')
async def getd():
    app.state.fyers=fyers_login()

@app.get('/reload')
async def reload():
    global df
    df=load()
