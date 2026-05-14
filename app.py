from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from dotenv import load_dotenv
from openai import OpenAI
import os
import random


load_dotenv()



app = Flask(__name__)

channel_secret = os.getenv("LINE_CHANNEL_SECRET")
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)
conversation_history = {}
question_count = {}

@app.route("/webhook", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except Exception as e:
        print("LINE ERROR:", e)
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):

    

    user_message = event.message.text
    user_id = event.source.user_id
    print(user_id)

    from datetime import datetime

    

    if user_id not in conversation_history:
        conversation_history[user_id] = []
        question_count[user_id] = 0

    question_count[user_id] += 1

    conversation_history[user_id].append({
        "role": "user",
        "content": user_message
    })
    try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                    "role": "system",
                    "content": """
                    あなたはAI面接官です。

                    ユーザーの面接練習を行ってください。

                    対象：
                    ・就活
                    ・バイト
                    ・大学入試

                    ルール：
                    ・質問は1回につき1つ
                    ・ユーザーの回答後に良かった点を1つ伝える
                    ・改善点を2つ伝える
                    ・次の質問をする
                    ・面接官らしく自然に会話する
                    ・5問終了したら総合評価を出す。
                    ・5問終わったら総合評価する
                    """
                    }
                ] + conversation_history[user_id][-10:]

            )
            ai_message = response.choices[0].message.content

            if question_count[user_id] >= 5:
                score = random.randint(60,100)

                ai_message += f"""

            ----------------
            面接終了です！

            総合評価：{score}/100

            良かった点：
            ・コミュニケーション力がある
            ・目標が明確
            ・受け答えが自然

            改善点：
            ・具体例を増やす
            ・理由をもう少し深掘りする

            お疲れさまでした！
            """
                question_count[user_id] = 0
                conversation_history[user_id] = []

            conversation_history[user_id].append({
                "role": "assistant",
                "content": ai_message
            })
            
    except Exception as e:
        print("OPENAI ERROR:", e, flush=True)
        ai_message = "エラーが出ています"

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=ai_message)]
            )
        )

    


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
