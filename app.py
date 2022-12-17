from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)
from transitions import Machine
from fsm import TocMachine
from initial import app
machine = TocMachine(
    states=["user","introduction", "show_fsm_pic", "show_rate", "show_history_rate","n_month_ago","forecast" ],
    transitions=[
        {
            "trigger": "advance",
            "source": "user",
            "dest": "introduction",
            "conditions": "is_going_to_introduction",
        },
        {
            "trigger": "advance",
            "source": "user",
            "dest": "show_fsm_pic",
            "conditions": "is_going_to_show_fsm_pic",
        },
        {
            "trigger": "advance",
            "source": "user",
            "dest": "show_rate",
            "conditions": "is_going_to_show_rate",
        },
        {
            "trigger": "advance",
            "source": "user",
            "dest": "show_history_rate",
            "conditions": "is_going_to_show_history_rate",
        },
        {
            "trigger": "advance",
            "source": "show_history_rate",
            "dest": "n_month_ago",
            "conditions": "is_number",
        },
        {
            "trigger": "advance",
            "source": "user",
            "dest": "forecast",
            "conditions": "is_going_to_forecast",
        },
        {
            "trigger": "go_back", 
            "source": [ "introduction","show_fsm_pic", "show_rate", "n_month_ago","forecast" ],
            "dest": "user"
        },
    ],
    initial="user",
    auto_transitions=False,
    show_conditions=True,
)


app.config.from_pyfile('config.py') #隱藏變數的檔案
config=app.config['CONFIG'] #class 名稱(一定要全大寫，不然會error)
app.config.from_object(config)
line_bot_api = LineBotApi(config.channel_access_token)
handler = WebhookHandler(config.channel_secret)

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
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@app.route("/") #使用route()裝飾器。route()裝飾器可以告訴Flask，緊接在裝飾器下面的函式要載入在哪個url位址中
def home():
    return "This is Home Page"
@app.route("/show-fsm", methods=["GET"])
def show_fsm():
    machine.get_graph().draw("fsm.png", prog="dot", format="png")
    return send_file("fsm.png", mimetype="image/png")

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print(f"\nFSM STATE: {machine.state}")
    #print(f"REQUEST BODY: \n{body}")
    response = machine.advance(event)
    if response == False:
        #send_text_message(event.reply_token, "請依照指示與按鈕來操作!")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請依照指示與按鈕來操作\n請打\"說明\"會有使用資訊"))
        
if __name__ == "__main__":
    #machine.get_graph().draw("fsm.png", prog="dot", format="png")
    app.run(port=config.port)
