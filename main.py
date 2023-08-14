import os
import time
from hashlib import sha256

import sanic
from dotenv import load_dotenv
from firebase_admin import messaging
from firebase_admin.messaging import Notification, AndroidNotification
from sanic import Request
from sanic.response import json
import firebase_admin
from database import Database
from sanic_limiter import Limiter, get_remote_address

load_dotenv()

app = sanic.Sanic(__name__)
db = Database()
fb_admin_app = firebase_admin.initialize_app(
    firebase_admin.credentials.Certificate(
        os.environ.get("SBURRAPP-FIREBASE-JSON")
    )
)
limiter = Limiter(app, key_func=get_remote_address)



@app.post('/isburred')
@limiter.limit("12 per hour;1/5minutes")
async def i_sburred(request: Request):
    device_id = request.headers["sbu-deviceid"]
    if device_id is None:
        return json({"sburraSent": False, "reason": "non so chi ha sburrato"})
    else:
        print(f"{device_id} HA SBURRATO")
        friends = db.get_friends(device_id)
        username = db.get_account(device_id)["username"]
        fcm_list = []
        for friend in friends["friends"]:
            device_id = db.get_account_by_username(friend["username"])["userId"]
            fcm = db.get_fcm(device_id)
            if fcm is not None:
                fcm_list.append(fcm["fcm"])
        message = messaging.MulticastMessage(
            tokens=[x for x in fcm_list if x], notification=Notification(
                title="Un tuo amico ha appena sborrato",
                body="Corri a vedere chi è stato!"),
            data={
                "username": username,
                "at": f"{int(time.time())}",
                "con": request.args.get("con", default=""),
                "hon": request.args.get("hon", default=""),
                "where": request.args.get("where", default="")
            }, android=messaging.AndroidConfig(
                priority='high',
                notification=AndroidNotification(
                    channel_id="AGG_SBURRAT", priority="high", sound="default"
                )
            )
        )
        response = messaging.send_each_for_multicast(message)
        print(f'{response.success_count} messages were sent successfully')
        if response.failure_count > 0:
            responses = response.responses
            failed_tokens = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    # The order of responses corresponds to the order of the registration tokens.
                    failed_tokens.append(fcm_list[idx])
            print('List of tokens that caused failures: {0}'.format(failed_tokens))
        return json({"sburraSent": True, "reason": None})


@app.post('/register')
async def register(request: Request):
    username = request.args.get("username")
    password = request.args.get("password")
    if username is None or password is None:
        return json({"changed": False, "reason": "non so i dati", "deviceId": None})
    else:
        acc_by_user = db.get_account_by_username(username)
        if acc_by_user is not None:
            if acc_by_user["password"] == sha256(password.encode('utf-8')).hexdigest():
                return json({"changed": True, "reason": None, "deviceId": acc_by_user["userId"]})
            else:
                return json({"changed": False, "reason": "cred sbagliate", "deviceId": None})

        else:
            device_id = db.insert_account(username, password)
            db.insert_friends_empty(device_id)

            return json({"changed": True, "reason": None, "deviceId": device_id})


@app.get('/getFriends')
async def get_friends(request: Request):
    device_id = request.headers["sbu-deviceid"]

    if device_id is None or device_id == "":
        return json({"friends": [], "reason": "non so chi vuole cambiare"})
    else:
        friends = db.get_friends(device_id)
        if friends is None:
            return json({"friends": [], "reason": "frate non hai un acc ziopera"})
        else:
            return json({"friends": friends["friends"], "reason": None})


@app.post('/addFriend')
async def add_friend(request: Request):
    device_id = request.headers["sbu-deviceid"]
    if device_id is None:
        return json({"done": False, "reason": "non so chi vuole cambiare"})
    else:

        friend_code = request.args.get("friendCode")
        if friend_code is None:
            return json({"done": False, "reason": "non so il friend code"})
        else:
            my_acc = db.get_account(device_id)
            friend_acc = db.get_account_by_friend_code(friend_code)
            if friend_acc is None:
                return json({"done": False, "reason": "il friend code non esiste"})
            elif friend_acc == my_acc:
                return json({"done": False,
                             "reason": "non puoi diventare amico di te stesso con la scusa che non hai amici ziopera"})
            else:
                db.add_friend(device_id, friend_acc["username"])
                return json({"done": True, "reason": None})


@app.post('/deleteFriend')
async def delete_friend(request: Request):
    device_id = request.headers["sbu-deviceid"]
    if device_id is None:
        return json({"done": False, "reason": "non so chi vuole cambiare"})
    else:
        username = request.args.get("username")
        if username is None:
            return json({"done": False, "reason": "non so l'username"})
        else:
            db.remove_friend(device_id, username)
            return json({"done": True, "reason": None})


@app.post('/changeFcm')
async def change_fcm(request: Request):
    device_id = request.headers["sbu-deviceid"]

    if device_id is None:
        return json({"changed": False, "reason": "non so chi vuole cambiare"})
    else:
        fcm = request.args.get("fcm")
        if fcm is None:
            return json({"changed": False, "reason": "non so l'fcm"})
        else:
            print(f"{device_id} VUOLE METTERSI COME FCM {fcm}")
            acc = db.get_fcm(device_id)

            if acc is None:
                db.insert_fcm(device_id, fcm)
            else:
                db.change_fcm(device_id, fcm)

            return json({"changed": True, "reason": None})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3459)
    print("stai sburrando in porta 3459")
