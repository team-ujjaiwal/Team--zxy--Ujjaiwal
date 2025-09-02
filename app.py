from flask import Flask, request, jsonify
import json
import binascii
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import aiohttp
import asyncio
import urllib3
from datetime import datetime, timedelta
import os
import threading
from functools import lru_cache
import time
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from google.protobuf.json_format import MessageToJson
import uid_generator_pb2
import CSVisit_count_pb2

app = Flask(__name__)

def load_tokens(region):
    try:
        if region == "IND":
            with open("token_ind.json", "r") as f:
                tokens = json.load(f)
        elif region in {"BR", "US", "SAC", "NA"}:
            with open("token_br.json", "r") as f:
                tokens = json.load(f)
        else:
            with open("token_bd.json", "r") as f:
                tokens = json.load(f)
        return tokens
    except Exception as e:
        return None

def encrypt_message(plaintext):
    try:
        key = b'Yg&tc%DEuh6%Zc^8'
        iv = b'6oyZDr22E3ychjM%'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_message = pad(plaintext, AES.block_size)
        encrypted_message = cipher.encrypt(padded_message)
        return binascii.hexlify(encrypted_message).decode('utf-8')
    except Exception as e:
        return None

def create_protobuf(uid):
    try:
        message = uid_generator_pb2.uid_generator()
        message.ujjaiwal_ = int(uid)
        message.garena = 1
        return message.SerializeToString()
    except Exception as e:
        return None

def enc(uid):
    protobuf_data = create_protobuf(uid)
    if protobuf_data is None:
        return None
    encrypted_uid = encrypt_message(protobuf_data)
    return encrypted_uid

async def make_request_async(encrypt, region, token, session):
    try:
        if region == "IND":
            url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
        elif region in {"BR", "US", "SAC", "NA"}:
            url = "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
        else:
            url = "https://clientbp.ggblueshark.com/GetPlayerPersonalShow"
            
        edata = bytes.fromhex(encrypt)
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB50"
        }
        
        async with session.post(url, data=edata, headers=headers, ssl=False, timeout=5) as response:
            if response.status != 200:
                return None
            else:
                binary = await response.read()
                return decode_protobuf(binary)
    except Exception as e:
        return None

def decode_protobuf(binary):
    try:
        items = CSVisit_count_pb2.Info()
        items.ParseFromString(binary)
        return items
    except Exception as e:
        return None

def extract_player_info(protobuf_obj):
    if not protobuf_obj:
        return None, None, None
    
    try:
        # Extract information directly from the protobuf object
        if hasattr(protobuf_obj, 'AccountInfo'):
            account_info = protobuf_obj.AccountInfo
            player_name = account_info.PlayerNickname if account_info.PlayerNickname else None
            player_level = account_info.Levels if account_info.Levels else None
            player_likes = account_info.Likes if account_info.Likes else None
            return player_name, player_level, player_likes
        return None, None, None
    except Exception as e:
        return None, None, None

@app.route('/visit', methods=['GET'])
async def visit():
    target_uid = request.args.get("uid")
    region = request.args.get("region", "").upper()
    
    if not all([target_uid, region]):
        return jsonify({"error": "UID and region are required"}), 400
        
    try:
        tokens = load_tokens(region)
        if tokens is None:
            raise Exception("Failed to load tokens.")
            
        encrypted_target_uid = enc(target_uid)
        if encrypted_target_uid is None:
            raise Exception("Encryption of target UID failed.")
            
        total_visits = len(tokens) * 20
        success_count = 0
        failed_count = 0
        player_name = None
        player_level = None
        player_likes = None
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for token in tokens:
                for _ in range(20):
                    tasks.append(make_request_async(encrypted_target_uid, region, token['token'], session))
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for response in responses:
                if response and isinstance(response, CSVisit_count_pb2.Info):
                    success_count += 1
                    # Extract player info from the first successful response
                    if player_name is None:
                        player_name, player_level, player_likes = extract_player_info(response)
                else:
                    failed_count += 1
                
        summary = {
            "TotalVisits": total_visits,
            "SuccessfulVisits": success_count,
            "FailedVisits": failed_count,
            "PlayerNickname": player_name,
            "PlayerLevel": player_level,
            "PlayerLikes": player_likes,
            "UID": int(target_uid),
            "TotalResponses": len(responses)
        }
        
        return jsonify(summary)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)