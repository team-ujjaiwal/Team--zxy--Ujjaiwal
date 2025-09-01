from flask import Flask, jsonify
import aiohttp
import asyncio
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from visit_count_pb2 import Info

app = Flask(__name__)

# Content from byte.py
dec = ['80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '8a', '8b', '8c', '8d', '8e', '8f', '90', '91', '92', '93', '94', '95', '96', '97', '98', '99', '9a', '9b', '9c', '9d', '9e', '9f', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8', 'a9', 'aa', 'ab', 'ac', 'ad', 'ae', 'af', 'b0', 'b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b7', 'b8', 'b9', 'ba', 'bb', 'bc', 'bd', 'be', 'bf', 'c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'ca', 'cb', 'cc', 'cd', 'ce', 'cf', 'd0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'd8', 'd9', 'da', 'db', 'dc', 'dd', 'de', 'df', 'e0', 'e1', 'e2', 'e3', 'e4', 'e5', 'e6', 'e7', 'e8', 'e9', 'ea', 'eb', 'ec', 'ed', 'ee', 'ef', 'f0', 'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'fa', 'fb', 'fc', 'fd', 'fe', 'ff']
x_list = ['1','01', '02', '03', '04', '05', '06', '07', '08', '09', '0a', '0b', '0c', '0d', '0e', '0f', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '1a', '1b', '1c', '1d', '1e', '1f', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '2a', '2b', '2c', '2d', '2e', '2f', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '3a', '3b', '3c', '3d', '3e', '3f', '40', '41', '42', '43', '44', '45', '46', '47', '48', '49', '4a', '4b', '4c', '4d', '4e', '4f', '50', '51', '52', '53', '54', '55', '56', '57', '58', '59', '5a', '5b', '5c', '5d', '5e', '5f', '60', '61', '62', '63', '64', '65', '66', '67', '68', '69', '6a', '6b', '6c', '6d', '6e', '6f', '70', '71', '72', '73', '74', '75', '76', '77', '78', '79', '7a', '7b', '7c', '7d', '7e', '7f']

def Encrypt_ID(x):
    x = int(x)
    if x < 128:
        return x_list[x]
    
    result = ""
    while x > 0:
        remainder = x % 128
        x = x // 128
        if x > 0:
            result = dec[remainder] + result
        else:
            result = x_list[remainder] + result
    
    return result

def encrypt_api(plain_text):
    plain_text = bytes.fromhex(plain_text)
    key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    cipher_text = cipher.encrypt(pad(plain_text, AES.block_size))
    return cipher_text.hex()

# Token loading function
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
        app.logger.error(f"❌ Token load error for {region}: {e}")
        return None

def get_url(server_name):
    if server_name == "IND":
        return "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
    elif server_name in {"BR", "US", "SAC", "NA"}:
        return "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
    else:
        return "https://clientbp.ggblueshark.com/GetPlayerPersonalShow"

def parse_protobuf_response(response_data):
    try:
        info = Info()
        info.ParseFromString(response_data)
        
        player_data = {
            "uid": info.AccountInfo.UID if info.AccountInfo.UID else 0,
            "nickname": info.AccountInfo.PlayerNickname if info.AccountInfo.PlayerNickname else "",
            "likes": info.AccountInfo.Likes if info.AccountInfo.Likes else 0,
            "region": info.AccountInfo.PlayerRegion if info.AccountInfo.PlayerRegion else "",
            "level": info.AccountInfo.Levels if info.AccountInfo.Levels else 0
        }
        return player_data
    except Exception as e:
        app.logger.error(f"❌ Protobuf parsing error: {e}")
        return None

async def visit(session, url, token, uid, data):
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB50",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SM-N975F Build/PI)",
        "Host": url.replace("https://", "").split("/")[0],
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    
    try:
        async with session.post(url, headers=headers, data=data, ssl=False, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            response_data = await resp.read()
            if resp.status == 200:
                return True, response_data, resp.status
            else:
                return False, response_data, resp.status
    except Exception as e:
        app.logger.error(f"❌ Visit error: {e}")
        return False, None, None

async def send_visits_exact(tokens_data, uid, server_name):
    """Send exactly as many visits as there are tokens"""
    url = get_url(server_name)
    total_success = 0
    player_info = None

    async with aiohttp.ClientSession() as session:
        # Prepare the encrypted data
        encrypted_data = encrypt_api("08" + Encrypt_ID(str(uid)) + "1801")
        data = bytes.fromhex(encrypted_data)
        
        print(f"📤 Sending {len(tokens_data)} visits (one per token)...")
        
        # Create tasks for each token
        tasks = []
        for token_item in tokens_data:
            token = token_item.get("token", "")
            if token:  # Only use valid tokens
                task = asyncio.create_task(visit(session, url, token, uid, data))
                tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, tuple) and result[0]:  # Success
                total_success += 1
                if player_info is None and result[1]:  # Get player info from first success
                    player_info = parse_protobuf_response(result[1])
    
    return total_success, len(tokens_data), player_info

@app.route('/<string:server>/<int:uid>', methods=['GET'])
def send_visits(server, uid):
    server = server.upper()
    tokens_data = load_tokens(server)
    
    if not tokens_data:
        return jsonify({"error": "❌ No valid tokens found"}), 500
    
    valid_tokens = [item for item in tokens_data if item.get("token") not in ["", "N/A", None]]
    
    if not valid_tokens:
        return jsonify({"error": "❌ No valid tokens found"}), 500

    print(f"🚀 Sending visits to UID: {uid}")
    print(f"📊 Total tokens available: {len(valid_tokens)}")
    print(f"🎯 Will send exactly {len(valid_tokens)} visits (one per token)")

    try:
        total_success, total_sent, player_info = asyncio.run(send_visits_exact(
            valid_tokens, uid, server
        ))

        response_data = {
            "SuccessfulVisits": total_success,
            "TotalTokensUsed": total_sent,
            "FailedVisits": total_sent - total_success,
            "SuccessRate": f"{(total_success/total_sent*100):.1f}%" if total_sent > 0 else "0%"
        }

        if player_info:
            response_data.update({
                "PlayerLevel": player_info.get("level", 0),
                "PlayerLikes": player_info.get("likes", 0),
                "PlayerNickname": player_info.get("nickname", ""),
                "PlayerRegion": player_info.get("region", ""),
                "UID": player_info.get("uid", 0)
            })
        else:
            response_data["PlayerInfo"] = "Not available - no successful response"

        print(f"✅ Completed: {total_success}/{total_sent} successful visits")
        return jsonify(response_data), 200
            
    except Exception as e:
        app.logger.error(f"❌ Main execution error: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Server is running"}), 200

@app.route('/info/<string:server>/<int:uid>', methods=['GET'])
def get_player_info(server, uid):
    """Get only player information without sending visits"""
    server = server.upper()
    tokens_data = load_tokens(server)
    
    if not tokens_data:
        return jsonify({"error": "❌ No valid tokens found"}), 500
    
    valid_tokens = [item for item in tokens_data if item.get("token") not in ["", "N/A", None]]
    
    if not valid_tokens:
        return jsonify({"error": "❌ No valid tokens found"}), 500

    async def fetch_player_info():
        url = get_url(server)
        encrypted_data = encrypt_api("08" + Encrypt_ID(str(uid)) + "1801")
        data = bytes.fromhex(encrypted_data)
        
        async with aiohttp.ClientSession() as session:
            # Try each token until we get a successful response
            for token_item in valid_tokens:
                token = token_item.get("token", "")
                success, response, status = await visit(session, url, token, uid, data)
                if success and response:
                    player_info = parse_protobuf_response(response)
                    if player_info:
                        return player_info
            return None

    try:
        player_info = asyncio.run(fetch_player_info())
        if player_info:
            return jsonify({
                "UID": player_info.get("uid", 0),
                "PlayerNickname": player_info.get("nickname", ""),
                "PlayerLevel": player_info.get("level", 0),
                "PlayerLikes": player_info.get("likes", 0),
                "PlayerRegion": player_info.get("region", ""),
                "Status": "Success"
            }), 200
        else:
            return jsonify({"error": "Could not fetch player information"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)