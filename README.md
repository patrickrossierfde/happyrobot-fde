# 🤖 HappyRobot Inbound Carrier Sales Integration
### Build Description for Acme Logistics

## 📌 Overview
This project provides an end-to-end automated solution for handling inbound carrier inquiries. Using the HappyRobot Voice AI platform, we have developed an agent capable of vetting carriers, searching real-time load data, and negotiating rates autonomously.

## 🔗 Live Project Links
* **Demo Video (Walkthrough):** [Insert Loom/Zoom Link here]
* **Live Analytics Dashboard:** [Insert your Streamlit/Railway URL here]
* **HappyRobot Workflow:** [Insert HappyRobot share link here]
* **Backend API Base URL:** [Insert your Railway Backend URL here]

## 🛠️ Technical Stack
- **AI Platform:** HappyRobot (Voice AI & LLM Extraction)
- **Backend:** FastAPI (Python)
- **Database:** SQLite (Relational data storage)
- **Dashboard:** Streamlit (Real-time analytics & QA)
- **Infrastructure:** Docker & Railway (Cloud Deployment)

## ✨ Key Features
1. **Automated Vetting:** Integrated with FMCSA logic to verify Motor Carrier (MC) eligibility.
2. **Dynamic Negotiation:** The agent handles up to 3 rounds of price negotiation based on margin guardrails.
3. **Sentiment Analysis:** Every call is analyzed for carrier tone (Positive/Neutral/Negative) to flag potential service issues.
4. **Self-Healing Webhooks:** Implemented "Upsert" logic to ensure data integrity even during server redeployments.
5. **Human-in-the-Loop Review:** A custom dashboard featuring interactive chat-bubble transcripts for rapid quality assurance.

## 🚀 Deployment Instructions
The solution is containerized via Docker. To run locally:
```bash
git clone [Your-Repo-Link]
cd [Your-Repo-Folder]
docker-compose up --build
