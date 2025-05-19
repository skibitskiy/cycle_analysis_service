import os
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, date, timedelta
import statistics
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import IntegrityError

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cycle_analysis")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(title="Cycle Analysis Service")

# SQLAlchemy модели
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(30))
    last_name = Column(String(30))
    timezone = Column(String(63), default="America/New_York")
    send_emails = Column(Boolean, default=True)
    birth_date = Column(DateTime, nullable=True)
    luteal_phase_length = Column(Integer, default=14)

class PeriodDB(Base):
    __tablename__ = "periods"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    first_day = Column(Boolean, default=False)

# Pydantic модели
class User(BaseModel):
    id: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    timezone: Optional[str] = "America/New_York"
    send_emails: bool = True
    birth_date: Optional[datetime] = None
    luteal_phase_length: int = 14
    class Config:
        orm_mode = True

class Period(BaseModel):
    id: int
    user_id: int
    timestamp: datetime
    first_day: bool = False
    class Config:
        orm_mode = True

class StatisticsResponse(BaseModel):
    average_cycle_length: Optional[float]
    all_time_average_cycle_length: Optional[float]
    cycle_length_minimum: Optional[int]
    cycle_length_maximum: Optional[int]
    cycle_length_mean: Optional[float]
    cycle_length_median: Optional[float]
    cycle_length_mode: Optional[int]
    cycle_length_standard_deviation: Optional[float]
    current_cycle_length: Optional[int]
    predicted_events: List[dict]

# Создание таблиц при старте
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Вспомогательные функции

def get_user_periods(db: Session, user_id: int):
    return db.query(PeriodDB).filter_by(user_id=user_id, first_day=True).order_by(PeriodDB.timestamp).all()

def get_cycle_lengths(db: Session, user_id: int):
    first_days = get_user_periods(db, user_id)
    cycle_lengths = []
    for i in range(1, len(first_days)):
        duration = (first_days[i].timestamp.date() - first_days[i-1].timestamp.date()).days
        cycle_lengths.append(duration)
    return cycle_lengths

def get_statistics(db: Session, user_id: int):
    cycle_lengths = get_cycle_lengths(db, user_id)
    stats = {}
    stats['average_cycle_length'] = round(sum(cycle_lengths[-6:]) / len(cycle_lengths[-6:]), 1) if len(cycle_lengths) >= 1 else None
    stats['all_time_average_cycle_length'] = round(sum(cycle_lengths) / len(cycle_lengths), 1) if len(cycle_lengths) >= 1 else None
    stats['cycle_length_minimum'] = min(cycle_lengths) if cycle_lengths else None
    stats['cycle_length_maximum'] = max(cycle_lengths) if cycle_lengths else None
    stats['cycle_length_mean'] = round(statistics.mean(cycle_lengths), 1) if cycle_lengths else None
    stats['cycle_length_median'] = statistics.median(cycle_lengths) if cycle_lengths else None
    try:
        stats['cycle_length_mode'] = statistics.mode(cycle_lengths) if cycle_lengths else None
    except statistics.StatisticsError:
        stats['cycle_length_mode'] = None
    stats['cycle_length_standard_deviation'] = round(statistics.stdev(cycle_lengths), 3) if len(cycle_lengths) > 1 else None
    # Текущий цикл
    user = db.query(UserDB).filter_by(id=user_id).first()
    today_date = date.today()
    previous_period = None
    for p in reversed(get_user_periods(db, user_id)):
        if p.timestamp.date() <= today_date:
            previous_period = p
            break
    if previous_period:
        stats['current_cycle_length'] = (today_date - previous_period.timestamp.date()).days
    else:
        stats['current_cycle_length'] = -1
    # Прогнозы
    predicted_events = []
    if previous_period and stats['average_cycle_length'] and user:
        for i in range(1, 4):
            ovulation_date = previous_period.timestamp.date() + timedelta(days=i*stats['average_cycle_length'] - user.luteal_phase_length)
            predicted_events.append({'timestamp': ovulation_date, 'type': 'projected ovulation'})
            period_date = previous_period.timestamp.date() + timedelta(days=i*stats['average_cycle_length'])
            predicted_events.append({'timestamp': period_date, 'type': 'projected period'})
    stats['predicted_events'] = predicted_events
    return stats

# Эндпоинты
@app.post("/users/", response_model=User)
def create_user(user: User, db: Session = Depends(get_db)):
    user_db = UserDB(**user.dict())
    db.add(user_db)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="User already exists")
    db.refresh(user_db)
    return user_db

@app.post("/periods/", response_model=Period)
def create_period(period: Period, db: Session = Depends(get_db)):
    period_db = PeriodDB(**period.dict())
    db.add(period_db)
    db.commit()
    db.refresh(period_db)
    return period_db

@app.get("/statistics/{user_id}", response_model=StatisticsResponse)
def get_user_statistics(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    stats = get_statistics(db, user_id)
    return StatisticsResponse(**stats) 