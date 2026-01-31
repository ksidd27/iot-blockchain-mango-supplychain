# 🥭 Mango Supply Chain Traceability using Blockchain

A **full-stack Ethereum blockchain application** for end-to-end traceability of mango exports, integrating **IoT condition monitoring**, **role-based dashboards**, and **QR-code verification** to ensure food safety and transparency from farmer to consumer.

---

## 🚀 Project Overview

Traditional food supply chains lack transparency, making it difficult to trace product origin, handling conditions, and accountability in case of spoilage or fraud.

This project solves that by implementing a **blockchain-based traceability system** where:
- Each mango batch is immutably recorded on the Ethereum blockchain
- IoT parameters (color, temperature, condition) are validated at each stage
- Multiple stakeholders interact through dedicated dashboards
- Consumers can scan a **QR code** to verify the complete batch history

---

## 🧠 Key Features

### 🔗 Blockchain Integration
- Ethereum Smart Contracts (Solidity)
- Local blockchain using **Ganache**
- Immutable batch creation and updates
- Multiple transactions stored across blocks

### 👥 Role-Based Access
| Role | Capabilities |
|----|----|
| Farmer | Create batches, submit IoT data |
| Wholesaler | Verify & update batch conditions |
| Distributor | Approve/reject based on quality |
| Retailer | Generate QR code for consumers |

### 🌡 IoT Condition Tracking
- Color
- Temperature
- Condition (Good / Optimal / Rejected)
- Automatic rejection if parameters are out of range

### 📱 QR Code Traceability
- Retailer generates QR code per batch
- Consumer scans QR to view full batch history
- Data pulled from local storage + blockchain reference

### 📂 Local + On-Chain Storage
- Blockchain → Integrity & immutability
- JSON files → Fast querying & dashboards

---

## 🏗 System Architecture

# 🥭 Mango Supply Chain Traceability using Blockchain

A **full-stack Ethereum blockchain application** for end-to-end traceability of mango exports, integrating **IoT condition monitoring**, **role-based dashboards**, and **QR-code verification** to ensure food safety and transparency from farmer to consumer.

---

## 🚀 Project Overview

Traditional food supply chains lack transparency, making it difficult to trace product origin, handling conditions, and accountability in case of spoilage or fraud.

This project solves that by implementing a **blockchain-based traceability system** where:
- Each mango batch is immutably recorded on the Ethereum blockchain
- IoT parameters (color, temperature, condition) are validated at each stage
- Multiple stakeholders interact through dedicated dashboards
- Consumers can scan a **QR code** to verify the complete batch history

---

## 🧠 Key Features

### 🔗 Blockchain Integration
- Ethereum Smart Contracts (Solidity)
- Local blockchain using **Ganache**
- Immutable batch creation and updates
- Multiple transactions stored across blocks

### 👥 Role-Based Access
| Role | Capabilities |
|----|----|
| Farmer | Create batches, submit IoT data |
| Wholesaler | Verify & update batch conditions |
| Distributor | Approve/reject based on quality |
| Retailer | Generate QR code for consumers |

### 🌡 IoT Condition Tracking
- Color
- Temperature
- Condition (Good / Optimal / Rejected)
- Automatic rejection if parameters are out of range

### 📱 QR Code Traceability
- Retailer generates QR code per batch
- Consumer scans QR to view full batch history
- Data pulled from local storage + blockchain reference

### 📂 Local + On-Chain Storage
- Blockchain → Integrity & immutability
- JSON files → Fast querying & dashboards

---

## 🏗 System Architecture

User (Browser)  
↓  
Flask Backend (Python)  
↓  
Web3.py  
↓  
Ethereum Smart Contract (Ganache)  
↓  
Local JSON Storage + Blockchain Ledger  


---

## 🛠 Technology Stack

### Backend
- Python
- Flask
- Web3.py
- Flask-CORS

### Blockchain
- Solidity
- Ethereum
- Ganache
- Remix IDE

### Frontend
- HTML5
- CSS3
- JavaScript (Fetch API)

### Utilities
- QR Code Generator
- JSON-based local database

---
## 📂 Project Structure

mango-supply-chain-blockchain/  
│  
├── backend/  
│ ├── app.py  
│ ├── contract_abi.json  
│ ├── data/  
│ │ ├── users.json  
│ │ └── batches.json  
│  
├── templates/  
│ ├── login.html  
│ ├── register.html  
│ ├── farmer_dashboard.html  
│ ├── wholesaler_dashboard.html  
│ ├── distributor_dashboard.html  
│ ├── retailer_dashboard.html  
│ └── trace.html  
│  
├── static/  
│ ├── style.css  
│ ├── scripts.js  
│ └── qr_batch_*.png  
│  
└── README.md    

---

## Future Enhancement  
- Deploy on public Ethereum testnet
- IPFS storage for certificates
- Mobile-friendly UI
- Real IoT sensor integration
- Analytics dashboard for regulators

## 👨‍💻 Author

Siddharth Kumar
M.Tech (CSE) – IIIT Bhubaneswar  
Blockchain | Web3 | Full-Stack Development
