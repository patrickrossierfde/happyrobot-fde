"""
HappyRobot Inbound Carrier Sales - FastAPI Backend
Forward Deployment Engineer Challenge
"""

from fastapi import FastAPI, HTTPException, Security, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import json
import uuid
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
import requests
from dotenv import load_dotenv
from textblob import TextBlob
import logging

# 1. LOAD ENV VARS FIRST
load_dotenv()

# 2. THEN GRAB THE KEY
FMCSA_API_KEY = os.getenv("FMCSA_API_KEY", "cdc33e44d693a3a58451898d4ec9df862c65b954")

# ==================== DATABASE SETUP ====================
DATABASE_URL = "sqlite:///./loads.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== MODELS ====================
class LoadDB(Base):
    __tablename__ = "loads"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    load_id = Column(String, unique=True, index=True)
    origin = Column(String)
    destination = Column(String)
    pickup_datetime = Column(DateTime)
    delivery_datetime = Column(DateTime)
    equipment_type = Column(String)
    loadboard_rate = Column(Float)
    notes = Column(String)
    weight = Column(Float)
    commodity_type = Column(String)
    num_of_pieces = Column(Integer)
    miles = Column(Float)
    dimensions = Column(String)
    available = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

class CallRecordDB(Base):
    __tablename__ = "call_records"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    call_id = Column(String, unique=True, index=True)
    mc_number = Column(String)
    load_id = Column(String)
    initial_offer = Column(Float)
    final_offer = Column(Float)
    agreed_price = Column(Float, nullable=True)
    call_outcome = Column(String)  # "agreed", "rejected", "no_match", "error"
    sentiment = Column(String)  # "positive", "neutral", "negative"
    carrier_name = Column(String, nullable=True)
    negotiation_rounds = Column(Integer, default=0)
    call_transcript = Column(String)  # JSON string of conversation
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ==================== PYDANTIC MODELS ====================
class Load(BaseModel):
    load_id: str
    origin: str
    destination: str
    pickup_datetime: datetime
    delivery_datetime: datetime
    equipment_type: str
    loadboard_rate: float
    notes: str
    weight: float
    commodity_type: str
    num_of_pieces: int
    miles: float
    dimensions: str
    
    class Config:
        from_attributes = True

class CallInitRequest(BaseModel):
    mc_number: str
    carrier_name: Optional[str] = None

class LoadSearchRequest(BaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    equipment_type: Optional[str] = None
    max_miles: Optional[float] = None

class NegotiationRequest(BaseModel):
    call_id: str
    carrier_offer: float
    transcript_snippet: str

class CallCompleteRequest(BaseModel):
    call_id: str
    outcome: str
    agreed_price: float
    transcript: str
    mc_number: Optional[str] = None
    carrier_name: Optional[str] = None # Added for FMCSA name tracking
    load_id: Optional[str] = None
    negotiation_rounds: int = 0

# ==================== API INITIALIZATION ====================
app = FastAPI(
    title="HappyRobot Inbound Carrier Sales",
    description="API for managing inbound carrier calls and load matching",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== SECURITY ====================
API_KEY = os.getenv("API_KEY", "happyrobot-dev-key-12345")

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== UTILITY FUNCTIONS ====================
def analyze_sentiment(text: str) -> str:
    """Analyze sentiment of carrier's response"""
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    
    if polarity > 0.1:
        return "positive"
    elif polarity < -0.1:
        return "negative"
    return "neutral"

def calculate_final_offer(initial_offer: float, carrier_offer: float, round_num: int) -> float:
    """Calculate system's counter offer - Broker Logic"""
    if round_num >= 3:
        return initial_offer
    max_pay = initial_offer * 1.15
    proposed_increase = (initial_offer + carrier_offer) / 2
    return min(proposed_increase, max_pay)

# --- NEW FMCSA LOGIC HERE ---
def check_fmcsa_status(mc_number: str):
    """Hits the live FMCSA API to verify carrier authority."""
    FMCSA_API_KEY = os.getenv("FMCSA_API_KEY", "cdc33e44d693a3a58451898d4ec9df862c65b954")
    
    # --- THE FIX: Clean the input! ---
    # Government APIs crash if they see spaces or letters (like "MC 54283" or "54283 ").
    # This line extracts ONLY the digits from whatever the AI heard.
    clean_number = "".join(filter(str.isdigit, str(mc_number)))
    
    if not clean_number:
        return {"verified": False, "message": "Could not understand the number."}

    try:
        url = f"https://mobile.fmcsa.dot.gov/qc/services/carriers/{clean_number}?webKey={FMCSA_API_KEY}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get('content', {})
            carrier = content.get('carrier', {})
            
            is_allowed = carrier.get('allowedToOperate') == 'Y'
            legal_name = carrier.get('legalName', "Unknown Carrier")
            
            return {
                "verified": is_allowed,
                "carrier_name": legal_name,
                "message": "Authorized" if is_allowed else "Authority Not Active"
            }
        elif response.status_code == 404:
            # Safely handle numbers that don't exist
            return {"verified": False, "message": "Carrier not found in federal database."}
        else:
            return {"verified": False, "message": f"FMCSA System Error ({response.status_code})."}
            
    except Exception as e:
        return {"verified": False, "message": f"Connection error: {str(e)}"}

# ==================== ENDPOINTS ====================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "HappyRobot Inbound Carrier Sales API"}

@app.post("/loads/seed", dependencies=[Depends(verify_api_key)])
async def seed_loads(db: Session = Depends(get_db)):
    """Seed database with sample loads"""
    sample_loads = [
        {
            "load_id": "LOAD001",
            "origin": "Los Angeles, CA",
            "destination": "Chicago, IL",
            "pickup_datetime": datetime(2024, 4, 20, 8, 0),
            "delivery_datetime": datetime(2024, 4, 23, 18, 0),
            "equipment_type": "Flatbed",
            "loadboard_rate": 3500.00,
            "notes": "Heavy machinery, requires air suspension",
            "weight": 45000,
            "commodity_type": "Machinery",
            "num_of_pieces": 2,
            "miles": 2015,
            "dimensions": "40x8x9"
        },
        {
            "load_id": "LOAD002",
            "origin": "Houston, TX",
            "destination": "Atlanta, GA",
            "pickup_datetime": datetime(2024, 4, 21, 10, 0),
            "delivery_datetime": datetime(2024, 4, 22, 20, 0),
            "equipment_type": "Dry Van",
            "loadboard_rate": 2800.00,
            "notes": "Fragile goods, handle with care",
            "weight": 35000,
            "commodity_type": "Electronics",
            "num_of_pieces": 150,
            "miles": 789,
            "dimensions": "40x8x8.5"
        },
        {
            "load_id": "LOAD003",
            "origin": "Miami, FL",
            "destination": "New York, NY",
            "pickup_datetime": datetime(2024, 4, 20, 14, 0),
            "delivery_datetime": datetime(2024, 4, 24, 10, 0),
            "equipment_type": "Refrigerated",
            "loadboard_rate": 4200.00,
            "notes": "Temperature controlled, 38-42°F",
            "weight": 40000,
            "commodity_type": "Perishables",
            "num_of_pieces": 1,
            "miles": 1280,
            "dimensions": "40x8x8"
        },
        {
            "load_id": "LOAD004",
            "origin": "Seattle, WA",
            "destination": "Denver, CO",
            "pickup_datetime": datetime(2024, 4, 21, 9, 0),
            "delivery_datetime": datetime(2024, 4, 23, 15, 0),
            "equipment_type": "Flatbed",
            "loadboard_rate": 3100.00,
            "notes": "Standard flatbed load",
            "weight": 42000,
            "commodity_type": "Construction Materials",
            "num_of_pieces": 5,
            "miles": 1315,
            "dimensions": "48x8.5x9"
        },
        {
            "load_id": "LOAD005",
            "origin": "Dallas, TX",
            "destination": "Phoenix, AZ",
            "pickup_datetime": datetime(2024, 4, 20, 16, 0),
            "delivery_datetime": datetime(2024, 4, 22, 12, 0),
            "equipment_type": "Dry Van",
            "loadboard_rate": 2600.00,
            "notes": "Consumer goods shipment",
            "weight": 38000,
            "commodity_type": "Consumer Goods",
            "num_of_pieces": 800,
            "miles": 1100,
            "dimensions": "40x8x8.5"
        }
    ]
    
    for load_data in sample_loads:
        existing = db.query(LoadDB).filter(LoadDB.load_id == load_data["load_id"]).first()
        if not existing:
            db_load = LoadDB(**load_data)
            db.add(db_load)
    
    db.commit()
    return {"message": f"Seeded {len(sample_loads)} loads"}

@app.post("/verify-mc")
async def verify_mc(request: CallInitRequest, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """Verify MC number via live FMCSA API"""
    verification = check_fmcsa_status(request.mc_number)
    
    if not verification["verified"]:
        return {
            "verified": False,
            "reason": verification.get("message", "Invalid MC number"),
            "call_id": None
        }
    
    call_id = str(uuid.uuid4())
    carrier_name = verification.get("carrier_name", "Unknown Carrier")
    
    return {
        "verified": True,
        "call_id": call_id,
        "mc_number": request.mc_number,
        "carrier_name": carrier_name,
        "message": f"MC number verified. Carrier name is {carrier_name}. Ready to offer loads."
    }

@app.post("/search-loads")
async def search_loads(
    request: LoadSearchRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    query = db.query(LoadDB).filter(LoadDB.available == 1)
    
    if request.origin:
        query = query.filter(LoadDB.origin.ilike(f"%{request.origin}%"))
    if request.destination:
        query = query.filter(LoadDB.destination.ilike(f"%{request.destination}%"))
    if request.equipment_type:
        query = query.filter(LoadDB.equipment_type == request.equipment_type)
    if request.max_miles:
        query = query.filter(LoadDB.miles <= request.max_miles)
    
    loads = query.limit(5).all()
    
    return {
        "found": len(loads) > 0,
        "count": len(loads),
        "loads": [
            {
                "load_id": load.load_id,
                "origin": load.origin,
                "destination": load.destination,
                "pickup_datetime": load.pickup_datetime.isoformat(),
                "delivery_datetime": load.delivery_datetime.isoformat(),
                "equipment_type": load.equipment_type,
                "loadboard_rate": load.loadboard_rate,
                "notes": load.notes,
                "weight": load.weight,
                "commodity_type": load.commodity_type,
                "num_of_pieces": load.num_of_pieces,
                "miles": load.miles,
                "dimensions": load.dimensions
            }
            for load in loads
        ]
    }

@app.post("/negotiate")
async def negotiate(
    request: NegotiationRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    call_record = db.query(CallRecordDB).filter(CallRecordDB.call_id == request.call_id).first()
    
    if not call_record:
        raise HTTPException(status_code=404, detail="Call record not found")
    
    if call_record.negotiation_rounds >= 3:
        return {
            "can_negotiate": False,
            "reason": "Maximum negotiation rounds reached",
            "final_offer": call_record.final_offer
        }
    
    call_record.negotiation_rounds += 1
    sentiment = analyze_sentiment(request.transcript_snippet)
    
    counter_offer = calculate_final_offer(
        call_record.initial_offer,
        request.carrier_offer,
        call_record.negotiation_rounds
    )
    
    call_record.final_offer = counter_offer
    db.commit()
    
    return {
        "round": call_record.negotiation_rounds,
        "carrier_offer": request.carrier_offer,
        "system_counter_offer": counter_offer,
        "sentiment_detected": sentiment,
        "can_continue": call_record.negotiation_rounds < 3,
        "message": f"We can go to ${counter_offer:.2f}. Can you accept this rate?"
    }
    
@app.post("/complete-call")
async def complete_call(
    request: CallCompleteRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    call_record = db.query(CallRecordDB).filter(CallRecordDB.call_id == request.call_id).first()
    
    if not call_record:
        call_record = CallRecordDB(
            call_id=request.call_id,
            mc_number=request.mc_number,
            load_id=request.load_id
        )
        db.add(call_record)
        db.flush()

    call_record.mc_number = request.mc_number
    call_record.load_id = request.load_id
    call_record.agreed_price = request.agreed_price
    call_record.call_outcome = request.outcome
    call_record.call_transcript = request.transcript
    call_record.negotiation_rounds = request.negotiation_rounds
    
    # --- ADDED: Store Carrier Name if HappyRobot extracts it ---
    if request.carrier_name:
        call_record.carrier_name = request.carrier_name
    
    sentiment = analyze_sentiment(request.transcript)
    call_record.sentiment = sentiment

    try:
        if request.outcome == "agreed" and request.agreed_price and request.load_id:
            load = db.query(LoadDB).filter(LoadDB.load_id == request.load_id).first()
            if load:
                load.available = 0
    except Exception as e:
        print(f"Load locking skipped: {e}")

    db.commit()
    return {"status": "success", "message": "Dashboard sync perfect"}

@app.get("/calls/{call_id}")
async def get_call(call_id: str, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    call_record = db.query(CallRecordDB).filter(CallRecordDB.call_id == call_id).first()
    if not call_record:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {
        "call_id": call_record.call_id,
        "mc_number": call_record.mc_number,
        "carrier_name": call_record.carrier_name,
        "load_id": call_record.load_id,
        "initial_offer": call_record.initial_offer,
        "final_offer": call_record.final_offer,
        "agreed_price": call_record.agreed_price,
        "outcome": call_record.call_outcome,
        "sentiment": call_record.sentiment,
        "negotiation_rounds": call_record.negotiation_rounds,
        "created_at": call_record.created_at.isoformat()
    }

@app.get("/metrics")
async def get_metrics(db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    total_calls = db.query(CallRecordDB).count()
    agreed_calls = db.query(CallRecordDB).filter(CallRecordDB.call_outcome == "agreed").count()
    
    from sqlalchemy import func
    avg_negotiation = db.query(func.avg(CallRecordDB.negotiation_rounds)).scalar() or 0
    total_revenue = db.query(func.sum(CallRecordDB.agreed_price)).scalar() or 0
    
    sentiment_counts = db.query(
        CallRecordDB.sentiment,
        func.count(CallRecordDB.id)
    ).group_by(CallRecordDB.sentiment).all()
    
    sentiment_breakdown = {sentiment: count for sentiment, count in sentiment_counts}
    
    return {
        "total_calls": total_calls,
        "agreed_calls": agreed_calls,
        "conversion_rate": (agreed_calls / total_calls * 100) if total_calls > 0 else 0,
        "avg_negotiation_rounds": round(avg_negotiation, 2),
        "total_revenue_generated": round(float(total_revenue), 2),
        "sentiment_breakdown": sentiment_breakdown
    }

@app.get("/calls")
async def list_calls(db: Session = Depends(get_db), api_key: str = Depends(verify_api_key), limit: int = 100):
    calls = db.query(CallRecordDB).order_by(CallRecordDB.created_at.desc()).limit(limit).all()
    
    return {
        "total": len(calls),
        "calls": [
            {
                "call_id": call.call_id,
                "mc_number": call.mc_number,
                "carrier_name": call.carrier_name,
                "load_id": call.load_id,
                "outcome": call.call_outcome,
                "sentiment": call.sentiment,
                "agreed_price": call.agreed_price,
                "created_at": call.created_at.isoformat(),
                "call_transcript": call.call_transcript 
            }
            for call in calls
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
