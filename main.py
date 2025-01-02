from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from datetime import datetime
import shutil
from importlib.machinery import SourceFileLoader
import polars as pl
import pandas as pd
from pyecharts.charts import Bar, Candlestick, Scatter, Line, Grid
from pyecharts import options as opts
#import pickle
from bs4 import BeautifulSoup
from pyecharts.commons.utils import JsCode
from data import fyers_login, update_parquet_data
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
app.state.equity=''
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
    app.state.equity=stats['_equity_curve']
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
         color0="#ec0000",border_color0="#ec0000"),yaxis_index=0,xaxis_index=0)
    .set_global_opts(title_opts=opts.TitleOpts(title=app.state.sym,pos_left="7%",pos_top="1%"),
        legend_opts=opts.LegendOpts(pos_top="2%",orient='horizontal'),
        # datazoom_opts=[opts.DataZoomOpts(type_="inside"),opts.DataZoomOpts(pos_top="middle",xaxis_index=0,range_end="100%")],
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
    #bar.extend_axis(yaxis=opts.AxisOpts(position="right",min_=0,max_=100,)).add_yaxis('Returns',app.state.equity['DrawdownPct'].tolist(),yaxis_index=1)
    print(df2)
    print(app.state.equity.reset_index()[['date','DrawdownPct']])
    df2=df2.join(app.state.equity['DrawdownPct'],on='date',how='left')
    area = Line().add_xaxis(df2['date'].astype('str').tolist()).add_yaxis('Returns',df2['DrawdownPct'].round(3).tolist(),
                                    areastyle_opts=opts.AreaStyleOpts(opacity=.6),xaxis_index=0,yaxis_index=1).set_global_opts(
        yaxis_opts=opts.AxisOpts(position='right'))
    #bar.overlap(area, yaxis_index=1, is_add_yaxis=True)
    trc=app.state.trades.copy()
    #trp=trc.copy() #for cumulative PnL for Portfolio value
    #trp['CumProfit']=trp['PnL'].cumsum()
    trc=trc.resample('ME',on='ExitTime').sum(numeric_only=True)
    trc['CumProfit']=trc['PnL'].cumsum()
    cuma = Line(init_opts=opts.InitOpts(height="150px",width="820px")).add_xaxis(trc.index.astype('str').tolist()).add_yaxis('Returns',trc['CumProfit'].tolist(),
            areastyle_opts=opts.AreaStyleOpts(opacity=.6),yaxis_index=3,xaxis_index=1,label_opts=opts.LabelOpts(is_show=False)).set_global_opts(
        yaxis_opts=opts.AxisOpts(position='right'))
    #print(trc)
    color_function = """
        function (params) {
            if (params.value > 0) {
                return 'green';
            } else if (params.value <= 0) {
                return 'red';
            }}
        """
    bar1=(Bar(init_opts=opts.InitOpts(height="300px",width="820px")).add_xaxis(trc.index.astype('str').tolist()).add_yaxis("PnL",trc['PnL'].round(0).tolist(),
        #label_opts=opts.LabelOpts(is_show=True,formatter=JsCode("function(param) {return Number(param.data[1]).toFixed(0);}")))
        label_opts=opts.LabelOpts(is_show=True,color='black',position='outside',vertical_align='top'),
        itemstyle_opts=opts.ItemStyleOpts(color=JsCode(color_function)),yaxis_index=2,xaxis_index=1)
        #.extend_axis(yaxis=opts.AxisOpts(position="right",min_=0,max_=100,axisline_opts=opts.AxisLineOpts(
        #        linestyle_opts=opts.LineStyleOpts(color="#d14a61")),))
        #.add_yaxis('Returns',trc['CumProfit'].tolist(),yaxis_index=1)
        )
    #bar1.set_global_opts(datazoom_opts=opts.DataZoomOpts(is_show=False,is_disabled=True))
    bar1.set_series_opts(label_opts=opts.LabelOpts(position="end"))
    #bar1.overlap(cuma)
    #line=Line().add_xaxis(trc.index.astype('str').tolist()).add_yaxis("Return",trc['ReturnPct'].tolist())
    grid = (Grid(init_opts=opts.InitOpts(height="1000px",width="1320px")).add(bar, grid_opts=opts.GridOpts(pos_bottom="55%"),grid_index=0)
            .add(bar1, grid_opts=opts.GridOpts(pos_bottom="3%",pos_top="58%"),grid_index=1)
            .add(area, grid_opts=opts.GridOpts(pos_bottom="55%"))
            .add(cuma, grid_opts=opts.GridOpts(pos_bottom="3%",pos_top="58%")))
    grid.options['dataZoom'] = [opts.DataZoomOpts(type_="inside",yaxis_index=0,range_end="100%"),opts.DataZoomOpts(xaxis_index=0,pos_top="48%",range_end="100%",is_zoom_on_mouse_wheel= True, type_= "slider")]
    #grid.options['Legend'] = opts.LegendOpts(orient='horizontal',pos_top="2%")
    htstr=grid.render_embed()
    soup=BeautifulSoup(htstr,features="lxml")
    print(app.state.equity)
    return HTMLResponse(soup.body)

@app.post("/new")
async def new_item(filename: str=Form(...)):
    file_path = f"{filename}.py"
    if os.path.exists(file_path):
        return {"message": "File already exists"}
    with open(f'strategies\\{file_path}', "w") as file:
        file.write("")
    return HTMLResponse(f'<div hx-post="/edit" hx-swap="outerHTML" class="mockup-code strategy"><pre><code class="language-python"></code></pre></div>')

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
    app.state.equity=stats[0]['_equity_curve']
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
    app.state.equity=pd.DataFrame(rd.loc['_equity_curve'][ind])
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
