from flask import Flask
from flask import request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

import os
from dotenv import load_dotenv
load_dotenv()

port = os.getenv("port")
app = Flask(__name__) #建立類別實體app（你也可以命名為別的）。將__name__傳給Flask
line_bot_api = LineBotApi('YOUR_CHANNEL_ACCESS_TOKEN')
handler = WebhookHandler('YOUR_CHANNEL_SECRET')

@app.route("/") #使用route()裝飾器。route()裝飾器可以告訴Flask，緊接在裝飾器下面的函式要載入在哪個url位址中
def home():
    return "This is Home Page"
@app.route("/hello")#我們想要讓hello函式被載入到hello的url位址中，
def hello():
    return "Hello World! This is Hello Page "

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text))
    
if __name__ == "__main__": #接著加上if判斷式，並且當條件成立時，執行app.run()： #if __name__ == ‘__main__’的敘述表示，當模組被直接啟動時，才會執行下面的程式
    app.run(port=port)