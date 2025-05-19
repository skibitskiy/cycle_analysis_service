from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, date, timedelta
import statistics

app = FastAPI(title="Cycle Analysis Service")

# Модели данных
class User(BaseModel):
    id: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    timezone: Optional[str] = "America/New_York"
    send_emails: bool = True
    birth_date: Optional[datetime] = None
    luteal_phase_length: int = 14

class Period(BaseModel):
    id: int
    user_id: int
    timestamp: datetime
    first_day: bool = False

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

# Имитация БД (in-memory)
USERS = {}
PERIODS = []

# Вспомогательные функции

def get_user_periods(user_id: int):
    return sorted([p for p in PERIODS if p.user_id == user_id and p.first_day], key=lambda p: p.timestamp)

def get_cycle_lengths(user_id: int):
    first_days = get_user_periods(user_id)
    cycle_lengths = []
    for i in range(1, len(first_days)):
        duration = (first_days[i].timestamp.date() - first_days[i-1].timestamp.date()).days
        cycle_lengths.append(duration)
    return cycle_lengths

def get_statistics(user_id: int):
    cycle_lengths = get_cycle_lengths(user_id)
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
    user = USERS.get(user_id)
    today_date = date.today()
    previous_period = None
    for p in reversed(get_user_periods(user_id)):
        if p.timestamp.date() <= today_date:
            previous_period = p
            break
    if previous_period:
        stats['current_cycle_length'] = (today_date - previous_period.timestamp.date()).days
    else:
        stats['current_cycle_length'] = -1
    # Прогнозы
    predicted_events = []
    if previous_period and stats['average_cycle_length']:
        for i in range(1, 4):
            ovulation_date = previous_period.timestamp.date() + timedelta(days=i*stats['average_cycle_length'] - user.luteal_phase_length)
            predicted_events.append({'timestamp': ovulation_date, 'type': 'projected ovulation'})
            period_date = previous_period.timestamp.date() + timedelta(days=i*stats['average_cycle_length'])
            predicted_events.append({'timestamp': period_date, 'type': 'projected period'})
    stats['predicted_events'] = predicted_events
    return stats

# Эндпоинты
@app.post("/users/", response_model=User)
def create_user(user: User):
    USERS[user.id] = user
    return user

@app.post("/periods/", response_model=Period)
def create_period(period: Period):
    PERIODS.append(period)
    return period

@app.get("/statistics/{user_id}", response_model=StatisticsResponse)
def get_user_statistics(user_id: int):
    if user_id not in USERS:
        raise HTTPException(status_code=404, detail="User not found")
    stats = get_statistics(user_id)
    return StatisticsResponse(**stats) 