import polars as pl
from fyers_apiv3 import fyersModel
import json
import datetime as dt
from dateutil.relativedelta import relativedelta
import pyotp
import os
import webbrowser
import time
import pyperclip
from urllib.parse import parse_qs,urlparse
import pickle
#import math

fd=pl.read_parquet(f'C:\\Users\\{os.getlogin()}\\OneDrive\\Python\\stockdata.parquet')
with open(f"C:\\Users\\{os.getlogin()}\\Downloads\\fyers.json") as f:
    f=json.load(f)

def generate_access_token():
    global user_id, pin, app_id, api_key, redirect_url, totp_key, url
    print("\nGenerating Access Token .....................")
    try:
        user_id = f["ci"]
        pin = f["pin"]
        app_id = f["client_id"]
        api_key = f["secret_key"]
        redirect_url = f["redirect_uri"]
        totp_key = f["totp"]
        session = fyersModel.SessionModel(
            client_id=app_id,
            secret_key=api_key,
            redirect_uri=redirect_url,
            response_type="code",
            state=f["state"],
        )
        url = session.generate_authcode()
        webbrowser.open_new(url)
        print("Copy URL to clipboard")
        old_clipboard_contents = ""
        new_clipboard_contents = ""
        while old_clipboard_contents == new_clipboard_contents:
            time.sleep(5)
            new_clipboard_contents = pyperclip.paste()
        url = new_clipboard_contents
        parsed = urlparse(url)
        auth_code = parse_qs(parsed.query)["auth_code"][0]
        session = fyersModel.SessionModel(
            client_id=app_id,
            secret_key=api_key,
            redirect_uri=redirect_url,
            response_type="code",
            grant_type="authorization_code",
        )
        session.set_token(auth_code)
        response = session.generate_token()
        access_token = response["access_token"]
        refresh_token = response["refresh_token"]
        token_dict = {
            "app_id": app_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
        with open("token_dict.pickle", "wb") as file:
            pickle.dump(token_dict, file)
    except:
        time.sleep(5)
        generate_access_token()


def fyers_login():
    global fyers, token_dict, name
    while True:
        try:
            with open("token_dict.pickle", "rb") as file:
                token_dict = pickle.load(file)
                print(token_dict)
        except:
            token_dict = {"app_id": 0, "access_token": 0, "refresh_token": 0}
        fyers = fyersModel.FyersModel(
            client_id=token_dict["app_id"],
            is_async=False,
            token=token_dict["access_token"],
            log_path="",
        )
        response = fyers.get_profile()
        if response["s"] == "error":
            generate_access_token()
        else:
            print("\nlogin Details ..........")
            print(fyers.get_profile()["data"]["name"])
            # print(name)
            break
    return fyers
    
#sym = mo.ui.dropdown(fd["symbol"].unique().to_list())
PARQUET_FILE = f'C:\\Users\\{os.getlogin()}\\OneDrive\\Python\\stockdata.parquet'
def fetch_data(ticker, sd, ed,fyers):
    std=fyers.history(data={'symbol':f'NSE:{ticker}-EQ','resolution':'1D','date_format':1,'range_from':sd,'range_to':ed,'cont_flag':1})
    print(std)
    df1=pl.DataFrame(std['candles'],schema={'date':pl.Int32,'open':pl.Float32,'high':pl.Float32,'low':pl.Float32,'close':pl.Float32,'volume':pl.Float32},orient="row")
    df1=df1.with_columns(date=pl.from_epoch('date'))
    df1=df1.with_columns(symbol=pl.lit(ticker))
    return df1

def save_to_parquet(data, file_name):
    if os.path.exists(file_name):
        existing_data = pl.read_parquet(file_name)
        data = pl.concat([existing_data, data]).unique(subset=["date", "symbol"])
        #data = data[~data.index.duplicated(keep='last')]  # Remove duplicates
    data.write_parquet(file_name)
    print(f"Data saved to {file_name}")

def update_parquet_data(ticker,fyers):
    new_data=pl.DataFrame()
    if os.path.exists(PARQUET_FILE):
        # Load existing data and find the last available date for the ticker
        all_data = pl.read_parquet(PARQUET_FILE)
        if ticker in all_data['symbol'].unique():
            ticker_data = all_data.filter(pl.col('symbol') == ticker)
            last_date = ticker_data.select(pl.col('date').max())[0,0]
            start_date= last_date+dt.timedelta(hours=24)
            #start_date = (last_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            start_date = dt.datetime(2019,9,19)
    else:
        start_date = dt.datetime(2019,9,19)
    end_date = dt.datetime.now()
    ny=(end_date-start_date).days
    if ny>366:
        for i in range(ny//366 + (ny % 366>0)):
            ed=(end_date-dt.timedelta(hours=24)-relativedelta(years=i)).strftime('%Y-%m-%d')
            sd=(end_date-relativedelta(years=i+1)).strftime('%Y-%m-%d')
            print(sd,ed)
            tmp_data = fetch_data(ticker, sd, ed, fyers)
            new_data=pl.concat([new_data,tmp_data])
    elif ny<=366 and ny>0:
        new_data = fetch_data(ticker, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), fyers)
    if not new_data.is_empty():
        save_to_parquet(new_data, f'C:\\Users\\{os.getlogin()}\\OneDrive\\Python\\stockdata.parquet')
    else:
        print(f"No new data available for {ticker}.")