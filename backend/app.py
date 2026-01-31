from flask import (
    Flask, jsonify, request, render_template,
    redirect, url_for, session, send_file
)
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from web3 import Web3
import json, os
from datetime import datetime
import qrcode
import time
from threading import Thread, Lock
import random

# ---------------------------
# Configuration (edit here)
# ---------------------------
GANACHE_URL = "http://127.0.0.1:7545"
PRIVATE_KEY = "0xf248d6a4e7fbdf1eca5ffd286e8aef4c1da95c103daa5d5ff270e07dd6fdf6ea"
CONTRACT_ADDRESS = "0x2D485a42fE61e30DF7B44D3268DbE6ca9C858177"

# ---------------------------
# Web3 / contract setup
# ---------------------------
web3 = Web3(Web3.HTTPProvider(GANACHE_URL))
if not web3.is_connected():
    raise Exception("❌ Could not connect to Ganache!")

SIGNER_ACCOUNT = web3.eth.account.from_key(PRIVATE_KEY).address
print("✅ Connected to Ganache. Signing account:", SIGNER_ACCOUNT)

# Load contract ABI (assumes contract_abi.json present)
with open("contract_abi.json", "r") as f:
    ABI = json.load(f)

contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

# ---------------------------
# Flask + SocketIO app
# ---------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
BATCHES_FILE = os.path.join(DATA_DIR, "batches.json")
GANACHE_BLOCKS_FILE = os.path.join(DATA_DIR, "ganache_blocks.json")
QR_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(QR_DIR, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "supersecretkey"
CORS(app)

# SocketIO for real-time Ganache updates
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global variables for real-time block monitoring
block_monitor_lock = Lock()
last_processed_block = 0
ganache_blocks_data = {"blocks": []}

# ---------------------------
# JSON helpers (robust)
# ---------------------------
def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def read_json(path, default=None):
    if not os.path.exists(path):
        if default is not None:
            write_json(path, default)
            return default
        return default or {}
    try:
        with open(path, "r") as f:
            content = f.read().strip()
            if not content:
                if default is not None:
                    write_json(path, default)
                    return default
                return default or {}
            return json.loads(content)
    except Exception:
        if default is not None:
            write_json(path, default)
            return default
        return default or {}

# Ensure files exist with sensible defaults
read_json(USERS_FILE, {"users": []})
read_json(BATCHES_FILE, {"batches": [], "conditions": []})
read_json(GANACHE_BLOCKS_FILE, {"blocks": []})

# ---------------------------
# Random batch data generator
# ---------------------------
RANDOM_DATA_POOLS = {
    "origins": ["Mysore", "Bangalore", "Coimbatore", "Ratnagiri", "Pune"],
    "farms": ["GreenFarm-001", "SunriseFarm-002", "OrganicFarm-003", "GoldenFields-004"],
    "exporters": ["ABC Exports", "XYZ Traders", "Global Foods", "AgriLink Exports"],
    "colors": ["Yellow", "Green", "Red", "Orange"],
    "conditions": ["Fresh", "Good", "Excellent", "Premium"],
    "farmers": ["Ramesh K", "Sita M", "Rajesh P", "Lakshmi R"]
}

def generate_random_batch():
    return {
        "id": f"{len(read_json(BATCHES_FILE, {'batches': []})['batches']) + 1001}",
        "origin": random.choice(RANDOM_DATA_POOLS["origins"]),
        "farm": random.choice(RANDOM_DATA_POOLS["farms"]),
        "exporter": random.choice(RANDOM_DATA_POOLS["exporters"]),
        "ipfsHash": f"Qm{random.randint(100000, 999999)}{random.randrange(1000, 9999)}",
        "color": random.choice(RANDOM_DATA_POOLS["colors"]),
        "temperature": round(20 + random.uniform(-5, 10), 1),
        "condition": random.choice(RANDOM_DATA_POOLS["conditions"]),
        "created_by": random.choice(RANDOM_DATA_POOLS["farmers"]),
        "timestamp": datetime.utcnow().isoformat()
    }

# ---------------------------
# Simple registration/login (unchanged)
# ---------------------------
@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        role = (request.form.get("role") or "").strip()
        if not role:
            return render_template("register.html", error="Please select a role!")
        if not username or not password or not role:
            return render_template("register.html", error="All fields required")

        users_data = read_json(USERS_FILE, {"users": []})
        for u in users_data.get("users", []):
            if u.get("username") == username:
                return render_template("register.html", error="Username already exists")

        users_data["users"].append({
            "username": username,
            "password": password,
            "role": role
        })
        write_json(USERS_FILE, users_data)
        return render_template("login.html", success="Registered — please login")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        users_data = read_json(USERS_FILE, {"users": []})
        for u in users_data.get("users", []):
            if u.get("username") == username and u.get("password") == password:
                session["user"] = username
                session["role"] = u.get("role")
                return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------------------
# NEW: Generate Random Batch (for farmer dashboard)
# ---------------------------
@app.route("/generate_random_batch", methods=["POST"])
def generate_random_batch_endpoint():
    if "user" not in session or session.get("role") != "farmer":
        return jsonify({"error": "Farmer access only"}), 403
    
    new_batch = generate_random_batch()
    
    # Save to local storage (NO blockchain yet)
    batches_data = read_json(BATCHES_FILE, {"batches": [], "conditions": []})
    batches_data["batches"].append(new_batch)
    write_json(BATCHES_FILE, batches_data)
    
    return jsonify({
        "message": "Random batch generated and saved locally",
        "batch": new_batch
    })

# ---------------------------
# NEW: Create Block with Multiple Selected Batches
# ---------------------------
@app.route("/create_block", methods=["POST"])
def create_block():
    if "user" not in session or session.get("role") != "farmer":
        return jsonify({"error": "Farmer access only"}), 403
    
    data = request.get_json()
    selected_batch_ids = data.get("batch_ids", [])
    
    if not selected_batch_ids:
        return jsonify({"error": "No batches selected"}), 400
    
    batches_data = read_json(BATCHES_FILE, {"batches": [], "conditions": []})
    selected_batches = []
    
    # Find selected batches by ID
    for batch_id in selected_batch_ids:
        batch = next((b for b in batches_data["batches"] if b.get("id") == batch_id), None)
        if batch:
            selected_batches.append(batch)
    
    if not selected_batches:
        return jsonify({"error": "No valid batches found"}), 400
    
    print(f"🚀 Creating block with {len(selected_batches)} batches...")
    tx_results = []
    
    # Send each batch as separate transaction (will go to same/next block due to Ganache blockTime)
    for batch in selected_batches:
        try:
            # Remove from pending list, mark as processed
            batches_data["batches"] = [b for b in batches_data["batches"] if b.get("id") != batch["id"]]
            
            # Create blockchain transaction
            nonce = web3.eth.get_transaction_count(SIGNER_ACCOUNT)
            txn = contract.functions.createBatch(
                batch["origin"], 
                batch["farm"], 
                batch["exporter"], 
                batch["ipfsHash"]
            ).build_transaction({
                "from": SIGNER_ACCOUNT,
                "nonce": nonce,
                "gas": 3000000,
                "gasPrice": web3.to_wei("20", "gwei")
            })
            
            signed = web3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
            raw_tx = signed.raw_transaction
            tx_hash = web3.eth.send_raw_transaction(raw_tx)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Update batch with blockchain details
            batch["tx_hash"] = web3.to_hex(tx_hash)
            batch["block_number"] = receipt.blockNumber
            batch["status"] = "On Blockchain"
            batch["timestamp"] = datetime.utcnow().isoformat()
            
            tx_results.append({
                "batch_id": batch["id"],
                "tx_hash": batch["tx_hash"],
                "block_number": batch["block_number"]
            })
            
            print(f"✅ Batch {batch['id']} → TX: {batch['tx_hash']}")
            
        except Exception as e:
            print(f"❌ Batch {batch.get('id', 'unknown')} failed: {str(e)}")
            tx_results.append({
                "batch_id": batch.get("id", "unknown"),
                "error": str(e)
            })
    
    write_json(BATCHES_FILE, batches_data)
    return jsonify({
        "message": f"✅ Created {len([t for t in tx_results if 'error' not in t])} successful transactions",
        "results": tx_results
    })

# ---------------------------
# SocketIO: Real-time Ganache block monitoring
# ---------------------------
def monitor_ganache_blocks():
    global last_processed_block, ganache_blocks_data
    while True:
        try:
            current_block = web3.eth.block_number
            if current_block > last_processed_block:
                with block_monitor_lock:
                    block = web3.eth.get_block(current_block, full_transactions=True)
                    block_data = {
                        "block_number": current_block,
                        "block_hash": block.hash.hex(),
                        "timestamp": block.timestamp,
                        "real_time": datetime.fromtimestamp(block.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                        "transactions": []
                    }
                    
                    # Filter transactions for your contract
                    for tx in block.transactions:
                        if tx.get('to') and tx['to'].lower() == CONTRACT_ADDRESS.lower():
                            block_data["transactions"].append({
                                "tx_hash": tx.hash.hex(),
                                "from": tx.get('from', ''),
                                "gas_used": tx.get('gas', 0)
                            })
                    
                    if block_data["transactions"]:  # Only emit blocks with our contract txs
                        ganache_blocks_data["blocks"].append(block_data)
                        # Keep only last 10 blocks
                        if len(ganache_blocks_data["blocks"]) > 10:
                            ganache_blocks_data["blocks"] = ganache_blocks_data["blocks"][-10:]
                        write_json(GANACHE_BLOCKS_FILE, ganache_blocks_data)
                        
                        # Emit to all connected clients
                        # socketio.emit('new_ganache_block', block_data, broadcast=True)
                        # socketio.emit('new_ganache_block', block_data, room=None, include_self=False, to_all=True)
                        socketio.emit('new_ganache_block', block_data)
                        print(f"🔗 New block {current_block} with {len(block_data['transactions'])} contract txs")
                    
                    last_processed_block = current_block
                
        except Exception as e:
            print(f"⚠️ Block monitor error: {str(e)}")
        
        time.sleep(2)  # Poll every 2 seconds

# Start block monitor thread
Thread(target=monitor_ganache_blocks, daemon=True).start()

@socketio.on('connect')
def handle_connect():
    print('Client connected to SocketIO')
    emit('connected', {'message': 'Connected to Ganache real-time updates'})

# ---------------------------
# Dashboard routing (unchanged)
# ---------------------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    role = session.get("role")
    user = session.get("user")
    template_name = f"{role}_dashboard.html"
    if not os.path.exists(os.path.join(BASE_DIR, "templates", template_name)):
        return render_template("dashboard.html", user=user, role=role)
    return render_template(template_name, user=user)

# ---------------------------
# Existing endpoints (unchanged but preserved)
# ---------------------------
@app.route("/create_batch", methods=["POST"])
def create_batch():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    origin = data.get("origin")
    farm = data.get("farm")
    exporter = data.get("exporter")
    ipfsHash = data.get("ipfsHash")
    color = data.get("color")
    temperature = data.get("temperature")
    condition = data.get("condition")

    print("📦 create_batch payload:", data)

    if not (origin and farm and exporter and ipfsHash):
        msg = "Missing required fields for batch creation"
        if not request.is_json:
            return render_template(f"{session.get('role')}_dashboard.html", user=session.get("user"), error=msg)
        return jsonify({"error": msg}), 400

    temp_val = None
    try:
        if temperature is not None and temperature != "":
            temp_val = float(temperature)
    except Exception:
        temp_val = None

    try:
        nonce = web3.eth.get_transaction_count(SIGNER_ACCOUNT)
        txn = contract.functions.createBatch(origin, farm, exporter, ipfsHash).build_transaction({
            "from": SIGNER_ACCOUNT,
            "nonce": nonce,
            "gas": 3000000,
            "gasPrice": web3.to_wei("20", "gwei")
        })
        signed = web3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
        raw_tx = signed.raw_transaction
        tx_hash = web3.eth.send_raw_transaction(raw_tx)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        tx_hex = web3.to_hex(tx_hash)
        print("✅ createBatch tx:", tx_hex)
    except Exception as e:
        print("❌ Blockchain create_batch failed:", str(e))
        if not request.is_json:
            return render_template(f"{session.get('role')}_dashboard.html", user=session.get("user"), error=str(e))
        return jsonify({"error": str(e)}), 500

    batches = read_json(BATCHES_FILE, {"batches": [], "conditions": []})
    new_id = len(batches["batches"]) + 1
    new_batch = {
        "id": new_id,
        "origin": origin,
        "farm": farm,
        "exporter": exporter,
        "status": "Batch Created",
        "ipfsHash": ipfsHash,
        "color": color or "",
        "temperature": temp_val,
        "condition": condition or "",
        "tx_hash": tx_hex,
        "created_by": session.get("user"),
        "timestamp": datetime.utcnow().isoformat()
    }
    batches["batches"].append(new_batch)
    write_json(BATCHES_FILE, batches)

    

    if request.is_json:
        return jsonify({"message": "✅ Batch created and recorded locally & on-chain", "batch": new_batch})
    return render_template(f"{session.get('role')}_dashboard.html", user=session.get("user"), success="Batch created successfully")

# [Other existing endpoints unchanged - submit_condition, generate_qr, trace_page, update_status, local_batches]

@app.route("/submit_condition", methods=["POST"])
def submit_condition():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    role = data.get("role") or session.get("role")
    batch_id_raw = data.get("batch_id")
    color = data.get("color", "")
    temp_raw = data.get("temperature")
    remarks = data.get("remarks", "") or data.get("condition", "")

    try:
        batch_id = int(batch_id_raw)
    except Exception:
        msg = "Invalid batch_id"
        if request.is_json:
            return jsonify({"error": msg}), 400
        return render_template(f"{session.get('role')}_dashboard.html", user=session.get("user"), error=msg)

    try:
        temperature = float(temp_raw) if temp_raw is not None and temp_raw != "" else None
    except Exception:
        temperature = None

    batches = read_json(BATCHES_FILE, {"batches": [], "conditions": []})
    index = batch_id - 1
    if index < 0 or index >= len(batches["batches"]):
        msg = f"Batch {batch_id} not found"
        if request.is_json:
            return jsonify({"error": msg}), 404
        return render_template(f"{session.get('role')}_dashboard.html", user=session.get("user"), error=msg)

    approved = True
    reasons = []
    if color:
        if color.lower() in ["black", "bad", "rotten"]:
            approved = False
            reasons.append("Bad color")
    if temperature is not None:
        if temperature < 5 or temperature > 35:
            approved = False
            reasons.append("Temperature out of range")
    if remarks:
        if "mold" in remarks.lower() or "spoilt" in remarks.lower():
            approved = False
            reasons.append("Remark indicates spoilage")

    status = "Approved" if approved else "Rejected"

    record = {
        "batch_id": batch_id,
        "role": role,
        "user": session.get("user"),
        "color": color,
        "temperature": temperature,
        "remarks": remarks,
        "status": status,
        "reasons": reasons,
        "timestamp": datetime.utcnow().isoformat()
    }
    if "conditions" not in batches:
        batches["conditions"] = []
    batches["conditions"].append(record)

    if approved:
        batches["batches"][index]["status"] = f"{role.capitalize()} Approved"
        batches["batches"][index].setdefault("history", []).append(record)

    write_json(BATCHES_FILE, batches)

    if request.is_json:
        return jsonify({"message": "Condition recorded", "record": record})
    return render_template(f"{session.get('role')}_dashboard.html", user=session.get("user"), success=f"Condition {status}")

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.get_json()
    batch_id = data.get("batchId")

    if batch_id is None:
        return jsonify({"error": "Batch ID missing"}), 400

    qr_filename = f"qr_batch_{batch_id}.png"
    qr_path = os.path.join("static", qr_filename)

    trace_url = f"http://127.0.0.1:5000/trace/{batch_id}"

    qr = qrcode.make(trace_url)
    qr.save(qr_path)

    return jsonify({
        "qr_url": f"static/{qr_filename}",
        "trace_url": trace_url
    })

@app.route("/trace/<int:batch_id>")
def trace_page(batch_id):
    data = read_json(BATCHES_FILE, {"batches": [], "conditions": []})
    batches = data.get("batches", [])
    batch = next((b for b in batches if int(b.get("id", -1)) == batch_id), None)
    if not batch:
        return f"<h2>Batch {batch_id} not found.</h2>", 404
    return render_template("trace.html", batch=batch)

@app.route("/update_status", methods=["POST"])
def update_status():
    try:
        data = request.get_json()
        batch_id = int(data.get("id"))
        status = data.get("status")
        ipfsHash = data.get("ipfsHash", "")
        color = data.get("color", "")
        temperature = str(data.get("temperature", ""))

        if status is None:
            return jsonify({"error": "Missing status"}), 400

        nonce = web3.eth.get_transaction_count(SIGNER_ACCOUNT)
        txn = contract.functions.updateBatch(batch_id, status, ipfsHash, color, temperature).build_transaction({
            "from": SIGNER_ACCOUNT,
            "nonce": nonce,
            "gas": 3000000,
            "gasPrice": web3.to_wei("20", "gwei")
        })

        signed_txn = web3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
        raw_tx = signed_txn.raw_transaction
        tx_hash = web3.eth.send_raw_transaction(raw_tx)
        web3.eth.wait_for_transaction_receipt(tx_hash)
        tx_hex = web3.to_hex(tx_hash)

        batches = read_json(BATCHES_FILE, {"batches": [], "conditions": []})
        index = batch_id - 1

        if 0 <= index < len(batches.get("batches", [])):
            batches["batches"][index]["status"] = status
            batches["batches"][index]["ipfsHash"] = ipfsHash
            batches["batches"][index]["color"] = color
            try:
                batches["batches"][index]["temperature"] = float(temperature) if temperature != "" else ""
            except Exception:
                batches["batches"][index]["temperature"] = temperature
            batches["batches"][index]["tx_hash"] = tx_hex
            batches["batches"][index]["timestamp"] = datetime.utcnow().isoformat()
            write_json(BATCHES_FILE, batches)

        return jsonify({"message": "✅ Status and IoT data updated successfully!", "tx_hash": tx_hex})

    except Exception as e:
        print("❌ Error update_status:", str(e))
        return jsonify({"error": str(e)}), 500

'''
@app.route("/local_batches", methods=["GET"])
def local_batches():
    data = read_json(BATCHES_FILE, {"batches": [], "conditions": []})
    data["batches"].sort(key=lambda x: int(x.get("id", 0)))
    return jsonify(data)
''' 
@app.route("/local_batches", methods=["GET"])
def local_batches():
    data = read_json(BATCHES_FILE, {"batches": [], "conditions": []})
    # FIXED: Safe sorting for both numeric (1,2,3) and alphanumeric (B1001) IDs
    import re
    def get_sort_key(batch):
        id_str = str(batch.get("id", "0"))
        numbers = re.findall(r'\d+', id_str)  # Extract digits: B1001 → ['1001']
        return int(numbers[0]) if numbers else 0
    
    if data["batches"]:
        data["batches"].sort(key=get_sort_key)
    return jsonify(data)



# NEW: Get Ganache blocks data
@app.route("/ganache_blocks", methods=["GET"])
def ganache_blocks():
    return jsonify(read_json(GANACHE_BLOCKS_FILE, {"blocks": []}))

# ---------------------------
# Run server
# ---------------------------
if __name__ == "__main__":
    print("🚀 Starting Flask + SocketIO server with Ganache real-time monitoring...")
    print("💡 Run Ganache with: ganache-cli -p 7545 --blockTime 60")
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)







'''

# app.py
from flask import (
    Flask, jsonify, request, render_template,
    redirect, url_for, session, send_file
)
from web3 import Web3
import json, os
from datetime import datetime
from flask_cors import CORS
import qrcode

# ---------------------------
# Configuration (edit here)
# ---------------------------
GANACHE_URL = "http://127.0.0.1:7545"
PRIVATE_KEY = "0x1a4c7c3aa707fa2cbb53b22f993dcf603085202584cd100ae0a61b96f63eed91"
CONTRACT_ADDRESS = "0x7E3e2aAeF5aa629Cc269072e16d3710A93Bb6730"
# ---------------------------

# Web3 / contract setup
web3 = Web3(Web3.HTTPProvider(GANACHE_URL))
if not web3.is_connected():
    raise Exception("❌ Could not connect to Ganache!")

# Use account derived from PRIVATE_KEY for signing
SIGNER_ACCOUNT = web3.eth.account.from_key(PRIVATE_KEY).address
print("✅ Connected to Ganache. Signing account:", SIGNER_ACCOUNT)

# Load contract ABI (assumes contract_abi.json present)
with open("contract_abi.json", "r") as f:
    ABI = json.load(f)

contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

# Flask app
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
BATCHES_FILE = os.path.join(DATA_DIR, "batches.json")
QR_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(QR_DIR, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "supersecretkey"
CORS(app)


# ---------------------------
# JSON helpers (robust)
# ---------------------------
def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def read_json(path, default=None):
    if not os.path.exists(path):
        if default is not None:
            write_json(path, default)
            return default
        return default or {}
    try:
        with open(path, "r") as f:
            content = f.read().strip()
            if not content:
                if default is not None:
                    write_json(path, default)
                    return default
                return default or {}
            return json.loads(content)
    except Exception:
        # If file corrupted or unreadable, create default
        if default is not None:
            write_json(path, default)
            return default
        return default or {}


# Ensure files exist with sensible defaults
read_json(USERS_FILE, {"users": []})
read_json(BATCHES_FILE, {"batches": [], "conditions": []})


# ---------------------------
# Simple registration/login
# ---------------------------
@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        role = (request.form.get("role") or "").strip()
        if not role:
            return render_template("register.html", error="Please select a role!")
        if not username or not password or not role:
            return render_template("register.html", error="All fields required")

        users_data = read_json(USERS_FILE, {"users": []})
        for u in users_data.get("users", []):
            if u.get("username") == username:
                return render_template("register.html", error="Username already exists")

        users_data["users"].append({
            "username": username,
            "password": password,
            "role": role
        })
        write_json(USERS_FILE, users_data)
        return render_template("login.html", success="Registered — please login")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        users_data = read_json(USERS_FILE, {"users": []})
        for u in users_data.get("users", []):
            if u.get("username") == username and u.get("password") == password:
                session["user"] = username
                session["role"] = u.get("role")
                return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------
# Dashboard routing
# ---------------------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    role = session.get("role")
    user = session.get("user")
    template_name = f"{role}_dashboard.html"
    if not os.path.exists(os.path.join(BASE_DIR, "templates", template_name)):
        # fallback: generic dashboard
        return render_template("dashboard.html", user=user, role=role)
    return render_template(template_name, user=user)


# ---------------------------
# Create a batch (used by farmer dashboard)
# ---------------------------
@app.route("/create_batch", methods=["POST"])
def create_batch():
    # accept either JSON or form submit
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    origin = data.get("origin")
    farm = data.get("farm")
    exporter = data.get("exporter")
    ipfsHash = data.get("ipfsHash")
    color = data.get("color")
    temperature = data.get("temperature")
    condition = data.get("condition")

    print("📦 create_batch payload:", data)

    if not (origin and farm and exporter and ipfsHash):
        msg = "Missing required fields for batch creation"
        if not request.is_json:
            return render_template(f"{session.get('role')}_dashboard.html", user=session.get("user"), error=msg)
        return jsonify({"error": msg}), 400

    temp_val = None
    try:
        if temperature is not None and temperature != "":
            temp_val = float(temperature)
    except Exception:
        temp_val = None

    # Transaction: createBatch(origin, farm, exporter, ipfsHash)
    try:
        nonce = web3.eth.get_transaction_count(SIGNER_ACCOUNT)
        txn = contract.functions.createBatch(origin, farm, exporter, ipfsHash).build_transaction({
            "from": SIGNER_ACCOUNT,
            "nonce": nonce,
            "gas": 3000000,
            "gasPrice": web3.to_wei("20", "gwei")
        })
        signed = web3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
        try:
            raw_tx = signed.raw_transaction
        except Exception:
            raw_tx = getattr(signed, "rawTransaction", None)
        tx_hash = web3.eth.send_raw_transaction(raw_tx)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        tx_hex = web3.to_hex(tx_hash)
        print("✅ createBatch tx:", tx_hex)
    except Exception as e:
        print("❌ Blockchain create_batch failed:", str(e))
        if not request.is_json:
            return render_template(f"{session.get('role')}_dashboard.html", user=session.get("user"), error=str(e))
        return jsonify({"error": str(e)}), 500

    # Save to local batches.json (IDs are 1-based per your choice A)
    batches = read_json(BATCHES_FILE, {"batches": [], "conditions": []})
    new_id = len(batches["batches"]) + 1
    new_batch = {
        "id": new_id,
        "origin": origin,
        "farm": farm,
        "exporter": exporter,
        "status": "Batch Created",
        "ipfsHash": ipfsHash,
        "color": color or "",
        "temperature": temp_val,
        "condition": condition or "",
        "tx_hash": tx_hex,
        "created_by": session.get("user"),
        "timestamp": datetime.utcnow().isoformat()
    }
    batches["batches"].append(new_batch)
    write_json(BATCHES_FILE, batches)

    if request.is_json:
        return jsonify({"message": "✅ Batch created and recorded locally & on-chain", "batch": new_batch})
    return render_template(f"{session.get('role')}_dashboard.html", user=session.get("user"), success="Batch created successfully")


# ---------------------------
# Submit condition (used by wholesaler, distributor, retailer)
# ---------------------------
@app.route("/submit_condition", methods=["POST"])
def submit_condition():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    role = data.get("role") or session.get("role")
    batch_id_raw = data.get("batch_id")
    color = data.get("color", "")
    temp_raw = data.get("temperature")
    remarks = data.get("remarks", "") or data.get("condition", "")

    try:
        batch_id = int(batch_id_raw)
    except Exception:
        msg = "Invalid batch_id"
        if request.is_json:
            return jsonify({"error": msg}), 400
        return render_template(f"{session.get('role')}_dashboard.html", user=session.get("user"), error=msg)

    try:
        temperature = float(temp_raw) if temp_raw is not None and temp_raw != "" else None
    except Exception:
        temperature = None

    batches = read_json(BATCHES_FILE, {"batches": [], "conditions": []})
    index = batch_id - 1  # convert 1-based id to 0-based index
    if index < 0 or index >= len(batches["batches"]):
        msg = f"Batch {batch_id} not found"
        if request.is_json:
            return jsonify({"error": msg}), 404
        return render_template(f"{session.get('role')}_dashboard.html", user=session.get("user"), error=msg)

    approved = True
    reasons = []
    if color:
        if color.lower() in ["black", "bad", "rotten"]:
            approved = False
            reasons.append("Bad color")
    if temperature is not None:
        if temperature < 5 or temperature > 35:
            approved = False
            reasons.append("Temperature out of range")
    if remarks:
        if "mold" in remarks.lower() or "spoilt" in remarks.lower():
            approved = False
            reasons.append("Remark indicates spoilage")

    status = "Approved" if approved else "Rejected"

    record = {
        "batch_id": batch_id,
        "role": role,
        "user": session.get("user"),
        "color": color,
        "temperature": temperature,
        "remarks": remarks,
        "status": status,
        "reasons": reasons,
        "timestamp": datetime.utcnow().isoformat()
    }
    if "conditions" not in batches:
        batches["conditions"] = []
    batches["conditions"].append(record)

    if approved:
        batches["batches"][index]["status"] = f"{role.capitalize()} Approved"
        batches["batches"][index].setdefault("history", []).append(record)
        # attempt on-chain update using the confirmed contract signature:
        try:
            nonce = web3.eth.get_transaction_count(SIGNER_ACCOUNT)
            # call updateBatch(id, newStatus, ipfsHash, color, temperature)
            tx_ipfs = batches["batches"][index].get("ipfsHash", "") or ""
            tx_color = color or ""
            tx_temp = str(temperature) if temperature is not None else ""
            txn = contract.functions.updateBatch(batch_id, f"{role.capitalize()} Approved", tx_ipfs, tx_color, tx_temp).build_transaction({
                "from": SIGNER_ACCOUNT,
                "nonce": nonce,
                "gas": 3000000,
                "gasPrice": web3.to_wei("20", "gwei")
            })
            signed = web3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
            try:
                raw_tx = signed.raw_transaction
            except Exception:
                raw_tx = getattr(signed, "rawTransaction", None)
            tx_hash = web3.eth.send_raw_transaction(raw_tx)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            tx_hex = web3.to_hex(tx_hash)
            record["onchain_tx"] = tx_hex
            print(f"✅ updateBatch on-chain for batch {batch_id}: {tx_hex}")
        except Exception as e:
            record["onchain_error"] = str(e)
            print("⚠️ Failed to write updateBatch to chain:", str(e))
    else:
        batches["batches"][index].setdefault("history", []).append(record)

    write_json(BATCHES_FILE, batches)

    if request.is_json:
        return jsonify({"message": "Condition recorded", "record": record})
    return render_template(f"{session.get('role')}_dashboard.html", user=session.get("user"), success=f"Condition {status}")


# ---------------------------
# Generate QR
# ---------------------------

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.get_json()
    batch_id = data.get("batchId")

    if batch_id is None:
        return jsonify({"error": "Batch ID missing"}), 400

    # Save QR file inside /static folder
    qr_filename = f"qr_batch_{batch_id}.png"
    qr_path = os.path.join("static", qr_filename)

    # QR Content = traceability URL
    trace_url = f"http://127.0.0.1:5000/trace/{batch_id}"

    qr = qrcode.make(trace_url)
    qr.save(qr_path)

    return jsonify({
        "qr_url": f"static/{qr_filename}",   # <-- IMPORTANT
        "trace_url": trace_url
    })


   


# ---------------------------
# Trace page
# ---------------------------
@app.route("/trace/<int:batch_id>")
def trace_page(batch_id):
    data = read_json(BATCHES_FILE, {"batches": [], "conditions": []})
    batches = data.get("batches", [])
    # find by 1-based id field
    batch = next((b for b in batches if int(b.get("id", -1)) == batch_id), None)
    if not batch:
        return f"<h2>Batch {batch_id} not found.</h2>", 404
    return render_template("trace.html", batch=batch)


# -----------------------------------------
# Update Status (called from dashboards)
# -----------------------------------------
@app.route("/update_status", methods=["POST"])
def update_status():
    try:
        data = request.get_json()
        batch_id = int(data.get("id"))
        status = data.get("status")
        ipfsHash = data.get("ipfsHash", "")
        color = data.get("color", "")
        temperature = str(data.get("temperature", ""))

        if status is None:
            return jsonify({"error": "Missing status"}), 400

        # call contract: updateBatch(id, newStatus, ipfsHash, color, temperature)
        nonce = web3.eth.get_transaction_count(SIGNER_ACCOUNT)
        txn = contract.functions.updateBatch(batch_id, status, ipfsHash, color, temperature).build_transaction({
            "from": SIGNER_ACCOUNT,
            "nonce": nonce,
            "gas": 3000000,
            "gasPrice": web3.to_wei("20", "gwei")
        })

        signed_txn = web3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
        try:
            raw_tx = signed_txn.raw_transaction
        except Exception:
            raw_tx = getattr(signed_txn, "rawTransaction", None)
        tx_hash = web3.eth.send_raw_transaction(raw_tx)
        web3.eth.wait_for_transaction_receipt(tx_hash)
        tx_hex = web3.to_hex(tx_hash)

        # Update locally too (IDs are 1-based -> convert to index)
        batches = read_json(BATCHES_FILE, {"batches": [], "conditions": []})
        index = batch_id - 1

        if 0 <= index < len(batches.get("batches", [])):
            batches["batches"][index]["status"] = status
            batches["batches"][index]["ipfsHash"] = ipfsHash
            batches["batches"][index]["color"] = color
            # store temperature as number if convertible else empty string
            try:
                batches["batches"][index]["temperature"] = float(temperature) if temperature != "" else ""
            except Exception:
                batches["batches"][index]["temperature"] = temperature
            batches["batches"][index]["tx_hash"] = tx_hex
            batches["batches"][index]["timestamp"] = datetime.utcnow().isoformat()
            write_json(BATCHES_FILE, batches)

        return jsonify({"message": "✅ Status and IoT data updated successfully!", "tx_hash": tx_hex})

    except Exception as e:
        print("❌ Error update_status:", str(e))
        return jsonify({"error": str(e)}), 500


# ---------------------------
# Get local batches & conditions
# ---------------------------
@app.route("/local_batches", methods=["GET"])
def local_batches():
    data = read_json(BATCHES_FILE, {"batches": [], "conditions": []})
    # ensure batches sorted by id ascending for consistent display
    data["batches"].sort(key=lambda x: int(x.get("id", 0)))
    return jsonify(data)


# ---------------------------
# Run server
# ---------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

'''