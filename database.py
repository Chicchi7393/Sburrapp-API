import os
from hashlib import sha256
from typing import Mapping, Any

import pymongo


class Database:
    def __init__(self):
        self.connection_string = os.environ.get("CONN_STRING")
        self.db = pymongo.MongoClient(self.connection_string)["sburrapp"]

    def get_account(self, device_id: str):
        print("[DB] Getting account")
        return self.db["accounts"].find_one({"userId": device_id})

    def get_account_by_username(self, username: str):
        print("[DB] Getting account")
        return self.db["accounts"].find_one({"username": username})

    def get_account_by_friend_code(self, friend_code: str):
        print("[DB] Getting account")
        for acc in self.db["accounts"].find({}):
            friend_code_calc = sha256(acc["userId"].encode('utf-8')).hexdigest()[0:15]
            friend_sect = [friend_code_calc[i:i+5] for i in range(0, len(friend_code_calc), 5)]
            friend_code_calc = "-".join(friend_sect)
            if friend_code_calc == friend_code:
                return acc
        return None

    def insert_account(self, username: str, password: str):
        print("[DB] Inserting account")
        hash_pass = sha256(password.encode('utf-8')).hexdigest()
        device_id = sha256(f"sburra_{username}_{hash_pass}".encode('utf-8')).hexdigest()
        self.db["accounts"].insert_one({"userId": device_id, "username": username, "password": hash_pass})
        return device_id

    def change_username(self, device_id: str, username: str):
        print("[DB] Changing username")
        return self.db["accounts"].find_one_and_update({"userId": device_id}, {"$set": {
            "username": username
        }})

    def insert_friends_empty(self, device_id: str):
        print("[DB] Inserting empty friends")
        return self.db["friends"].replace_one({"userId": device_id}, {"userId": device_id, "friends": []}, upsert=True)

    def get_friends(self, device_id: str):
        print("[DB] Getting friends")
        return self.db["friends"].find_one({"userId": device_id})

    def add_friend(self, device_id: str, friend_username: str):
        print("[DB] Adding friend")
        self.db["friends"].find_one_and_update({"userId": device_id},
                                               {"$addToSet": {"friends": {"username": friend_username}}})
        friend_id = self.db["accounts"].find_one({"username": friend_username})
        your_username = self.db["accounts"].find_one({"userId": device_id})

        self.db["friends"].find_one_and_update({"userId": friend_id["userId"]},
                                               {"$addToSet": {"friends": {"username": your_username["username"]}}})

    def remove_friend(self, device_id: str, friend_username: str):
        print("[DB] Removing friend")
        self.db["friends"].find_one_and_update({"userId": device_id},
                                               {"$pull": {"friends": {"username": friend_username}}})
        friend_id = self.db["accounts"].find_one({"username": friend_username})
        your_username = self.db["accounts"].find_one({"userId": device_id})

        self.db["friends"].find_one_and_update({"userId": friend_id["userId"]},
                                               {"$pull": {"friends": {"username": your_username}}})

    def get_fcm(self, device_id: str):
        print("[DB] Getting fcm")
        return self.db["fcm"].find_one({"userId": device_id})

    def insert_fcm(self, device_id: str, fcm: str):
        print("[DB] Inserting fcm")

        return self.db["fcm"].insert_one({"userId": device_id, "fcm": fcm})

    def change_fcm(self, device_id: str, fcm: str):
        print("[DB] Changing fcm")
        return self.db["fcm"].find_one_and_update({"userId": device_id}, {"$set": {
            "fcm": fcm
        }})
