from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageSendMessage 
)

from transitions.extensions import GraphMachine
from initial import app
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import pyimgur
import pickle
import numpy as np

# 創建server
app.config.from_pyfile('config.py') #隱藏變數的檔案
config=app.config['CONFIG'] #class 名稱(一定要全大寫，不然會error)
app.config.from_object(config)

#抓取資料
def predict_rate():
    #抓取歷史資料
    date_history = []
    history_buy = []
    history_sell = []
    datalist=make_date(2) #製作要提取的月份，送進爬蟲(本次預測只要5天的資料，取得兩個月的匯率資訊一定以得到五天的資料)
    for i in range(len(datalist)):
        newdata=craw_exchange_rate(datalist[i],date_history,history_buy,history_sell)
    #製作feature
    total_day=5
    company=['匯率公司']
    feature=['exchange_rate']
    feature_X=np.zeros((len(company),len(feature),total_day), dtype=np.float)
    counter=total_day
    for i in range(len(company)):
        for j in range(len(feature)):
            for k in range(total_day):
                feature_X[i,j,counter-1]=history_sell[k]
                counter-=1
    #predict
    predict=np.zeros((len(company),len(feature)), dtype=np.float)
    for j in range(len(company)):
        for i in range(len(feature)):
            filename = company[j]+'_'+feature[i]+'_model.sav'
            regr = pickle.load(open(filename, 'rb'))
            temp=feature_X[j][i].reshape((1,-1))
            predict[j][i]=regr.predict(temp)
    answer=list()
    answer.append(predict[0][0])
    if(predict[0][0]>feature_X[0][0][total_day-1]):
        answer.append('漲')
    else:
        answer.append('跌')
    return answer
    
def get_today_value():
    url = "https://rate.bot.com.tw/xrt?Lang=zh-TW"
    resp = requests.get(url)
    resp.encoding = 'utf-8'
    html_soup = BeautifulSoup(resp.text, "lxml")
    rate_table = html_soup.find('table', attrs={'title':'牌告匯率'}).find('tbody').find_all('tr')
    # 查詢英鎊(也就是匯率表的第3個元素)對台幣的匯率
    id=0 #(美金)
    currency = rate_table[id].find('div', attrs={'class':'visible-phone print_hide'})
    print(currency.text.replace(" ", ""))  # 去掉所有的空白
    buyin_rate = rate_table[id].find('td', attrs={'data-table':'本行現金買入'})
    sellout_rate = rate_table[id].find('td', attrs={'data-table':'本行現金賣出'})
    print("buyin_rate=",buyin_rate.get_text(),type(buyin_rate.get_text()))
    print("即時現金買入: {}, 即時現金賣出: {}".format(buyin_rate.get_text(), sellout_rate.get_text()))
    return [buyin_rate.get_text(),sellout_rate.get_text()]

# 製作要讀取的月份
def make_date(month_age):
    today = datetime.today()
    datalist=[]
    for j in range(int(month_age)):
        if today.month-j > 0:
            y=today.year
            m=today.month-j
            if m<10:
              datalist.append(f'{y}-0{m}')
            else:
              datalist.append(f'{y}-{m}')
        else:
            y=today.year-1
            m=12-(j-today.month)
            if m<10:
              datalist.append(f'{y}-0{m}')
            else:
              datalist.append(f'{y}-{m}')
    print(datalist)
    return datalist

#抓取指定匯率資料
def craw_exchange_rate(date,date_history,history_buy,history_sell):
    # 先到牌告匯率首頁，爬取所有貨幣的種類
    url = "https://rate.bot.com.tw/xrt?Lang=zh-TW"
    resp = requests.get(url)
    resp.encoding = 'utf-8'
    html = BeautifulSoup(resp.text, "lxml")
    rate_table = html.find('table', attrs={'title':'牌告匯率'}).find('tbody').find_all('tr')
    # 針對美金，找到其「歷史匯率」的首頁:
    history_link = rate_table[0].find('td', attrs={'data-table':'歷史匯率'})
    #print(history_link)
    history_rate_link = "https://rate.bot.com.tw" + history_link.a["href"]  # 該貨幣的歷史資料首頁
    #print(history_rate_link)
    # 到貨幣歷史匯率網頁，選則該貨幣的「歷史區間」，送出查詢後，觀察其網址變化情形，再試著抓取其歷史匯率資料
    # 用’quote/西元年-月‘去更換網址，就可以連到該貨幣的歷史資料
    replace_str=f'quote/{date}'
    quote_history_url = history_rate_link.replace("history", replace_str)
    resp = requests.get(quote_history_url)
    resp.encoding = 'utf-8'
    #print(resp.text)
    history = BeautifulSoup(resp.text, "lxml")
    history_table = history.find('table', attrs={'title':'歷史本行營業時間牌告匯率'}).find('tbody').find_all('tr')
    for history_rate in history_table:
        # 擷取日期資料
        date_string = history_rate.a.get_text()
        date = datetime.strptime(date_string,"%Y/%M/%d").strftime("%Y/%M/%d")  # 轉換日期格式
        date_history.append(date)  # 日期歷史資料

        history_ex_rate = history_rate.find_all(name="td", attrs={'class':'rate-content-cash text-right print_table-cell'})
        history_buy.append(float(history_ex_rate[0].get_text()))  # 歷史買入匯率
        history_sell.append(float(history_ex_rate[1].get_text()))  # 歷史賣出匯率

#取得歷史資料圖片網址
def get_imgurl(n_month_age):
    date_history = []
    history_buy = []
    history_sell = []
    datalist=make_date(n_month_age) #製作要提取的月份，送進爬蟲
    for i in range(len(datalist)):
        newdata=craw_exchange_rate(datalist[i],date_history,history_buy,history_sell)
        #print(date_history)
    # 將匯率資料建成dataframe形式
    History_Ex_Rate = pd.DataFrame({'date': date_history,'buy_rate':history_buy,'sell_rate':history_sell})
    History_Ex_Rate['date'] = pd.to_datetime(History_Ex_Rate['date'])
    History_Ex_Rate = History_Ex_Rate.set_index('date')  # 指定日期欄位為datafram的index
    History_Ex_Rate = History_Ex_Rate.sort_index(ascending=True)
    print(History_Ex_Rate)
    # 畫出歷史匯率軌跡圖
    plt.figure(figsize=(10, 8))
    History_Ex_Rate[['buy_rate','sell_rate']].plot()  # x=['date'], y=[['buy_rate','sell_rate']] 
    plt.legend(loc="upper left")
    plt.savefig('USA_month.png')
    #plt.show()
    CLIENT_ID = config.imgr_id
    PATH = "USA_month.png"
    im = pyimgur.Imgur(CLIENT_ID)
    uploaded_image = im.upload_image(PATH, title="upload")
    print('link:',uploaded_image.link) 
    return uploaded_image.link

# fsm 
class TocMachine(GraphMachine):
    def __init__(self, **machine_configs):
        self.machine = GraphMachine(model=self, **machine_configs)
    
    #以下為判斷式
    def is_number(seif,event):
        number=False
        try:
            int(event.message.text)
            if(int(event.message.text)>12):
                number=False
                message = "請輸入您想查幾個月前的歷史匯率資料(最多查看至一年前的資料)\nex:1,2,...12"
                line_bot_api = LineBotApi(config.channel_access_token)
                line_bot_api.reply_message(reply_token,TextSendMessage(text=message))
            number=True
        except:
            reply_token = event.reply_token
            message = "請輸入您想查幾個月前的歷史匯率資料(最多查看至一年前的資料)\nex:1,2,...12"
            line_bot_api = LineBotApi(config.channel_access_token)
            line_bot_api.reply_message(reply_token,TextSendMessage(text=message))
        return number
    def is_going_to_introduction(self, event):
        text = event.message.text
        return text == "說明"

    def is_going_to_show_fsm_pic(self, event):
        text = event.message.text
        return text == "fsm"

    def is_going_to_show_rate(self, event):
        text = event.message.text
        return text == "今日匯率"

    def is_going_to_show_history_rate(self, event):
        text = event.message.text
        return text == "歷史匯率"

    def is_going_to_forecast(self, event):
        text = event.message.text
        return text == "預測"
    #以下為進入state時會執行的動作
    def on_enter_introduction(self, event):
        reply_token = event.reply_token
        message = "請打\"說明\"會有使用資訊 \n請打\"今日匯率\"會有今日美金的匯率資訊 \n請打\"歷史匯率\"後，再須入您要查詢幾個月前的歷史資料，就會跑出走勢圖 \n請打\"預測\"會預測下一個交易日美金的漲跌與售出價格 \n請打\"fsm\"會輸出本系統fsm圖片"
        #message_to_reply = FlexSendMessage("說明", message)
        line_bot_api = LineBotApi(config.channel_access_token)
        line_bot_api.reply_message(reply_token,TextSendMessage(text=message))
        #line_bot_api.reply_message(reply_token, message)
        self.go_back()
    
    def on_enter_show_fsm_pic(self, event):
        reply_token = event.reply_token
        line_bot_api = LineBotApi(config.channel_access_token)
        line_bot_api.reply_message(reply_token,ImageSendMessage(
                original_content_url=r'https://i.imgur.com/2eoyCJr.png',
                preview_image_url=r'https://i.imgur.com/2eoyCJr.png'))
        self.go_back()
        

    def on_enter_show_rate(self, event):
        value=get_today_value()
        reply_token = event.reply_token
        message = f"本行(台銀)買入:{value[0]} \n本行(台銀)賣出:{value[1]}"
        #message_to_reply = FlexSendMessage("今日匯率:", message)
        line_bot_api = LineBotApi(config.channel_access_token)
        line_bot_api.reply_message(reply_token,TextSendMessage(text=message))
        self.go_back()

    def on_enter_show_history_rate(self, event):
        reply_token = event.reply_token
        message = "請輸入您想查幾個月前的歷史匯率資料(最多查看至一年前的資料)\nex:1,2,...12"
        line_bot_api = LineBotApi(config.channel_access_token)
        line_bot_api.reply_message(reply_token,TextSendMessage(text=message))
        
    def on_enter_n_month_ago(self,event):
        url=get_imgurl(int(event.message.text))
        reply_token = event.reply_token
        message = f"{int(event.message.text)}天前歷史匯率"
        line_bot_api = LineBotApi(config.channel_access_token)
        line_bot_api.reply_message(reply_token,ImageSendMessage(
                original_content_url=url,
                preview_image_url=url))
        self.go_back()
        
    def on_enter_forecast(self, event):
        reply_token = event.reply_token
        predict=predict_rate()
        up_down=predict[1]
        value=predict[0]
        message = f"預測下一個交易日\n漲跌:{up_down}\n"+'本行賣出:{:.2f}'.format(value)
        #message_to_reply = FlexSendMessage("今日匯率:", message)
        line_bot_api = LineBotApi(config.channel_access_token)
        line_bot_api.reply_message(reply_token,TextSendMessage(text=message))
        self.go_back()
