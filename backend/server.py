from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enums
class GameMode(str, Enum):
    MULTIPLAYER = "multiplayer"
    SINGLE_PLAYER = "single_player"

class BotDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

# Game Models
class Player(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    consecutive_wins: int = 0
    best_streak: int = 0
    total_games: int = 0
    total_wins: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PlayerCreate(BaseModel):
    name: str

class PlayerUpdate(BaseModel):
    name: Optional[str] = None
    consecutive_wins: Optional[int] = None
    best_streak: Optional[int] = None
    total_games: Optional[int] = None
    total_wins: Optional[int] = None

class GameSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mode: GameMode
    player1_name: str
    player2_name: Optional[str] = None  # None for bot games
    winner: str
    player1_score: int
    player2_score: int
    bot_difficulty: Optional[BotDifficulty] = None
    game_duration: int  # in seconds
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GameSessionCreate(BaseModel):
    mode: GameMode
    player1_name: str
    player2_name: Optional[str] = None
    winner: str
    player1_score: int
    player2_score: int
    bot_difficulty: Optional[BotDifficulty] = None
    game_duration: int

class LeaderboardEntry(BaseModel):
    name: str
    consecutive_wins: int
    best_streak: int
    total_games: int
    total_wins: int

# Helper functions
def prepare_for_mongo(data):
    """Prepare datetime objects for MongoDB storage"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(item):
    """Parse datetime strings from MongoDB"""
    if isinstance(item, dict):
        for key, value in item.items():
            if key in ['created_at'] and isinstance(value, str):
                try:
                    item[key] = datetime.fromisoformat(value)
                except:
                    item[key] = datetime.now(timezone.utc)
    return item

# Player Routes
@api_router.post("/players", response_model=Player)
async def create_player(player_data: PlayerCreate):
    # Check if player already exists
    existing_player = await db.players.find_one({"name": player_data.name})
    if existing_player:
        return Player(**parse_from_mongo(existing_player))
    
    player = Player(**player_data.dict())
    player_dict = prepare_for_mongo(player.dict())
    await db.players.insert_one(player_dict)
    return player

@api_router.get("/players/{player_name}", response_model=Player)
async def get_player(player_name: str):
    player = await db.players.find_one({"name": player_name})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return Player(**parse_from_mongo(player))

@api_router.put("/players/{player_name}", response_model=Player)
async def update_player(player_name: str, updates: PlayerUpdate):
    update_data = {k: v for k, v in updates.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid updates provided")
    
    result = await db.players.update_one(
        {"name": player_name},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Player not found")
    
    updated_player = await db.players.find_one({"name": player_name})
    return Player(**parse_from_mongo(updated_player))

@api_router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard():
    players = await db.players.find().sort("consecutive_wins", -1).limit(10).to_list(10)
    return [LeaderboardEntry(**parse_from_mongo(player)) for player in players]

@api_router.get("/leaderboard/best-streaks", response_model=List[LeaderboardEntry])
async def get_best_streaks_leaderboard():
    players = await db.players.find().sort("best_streak", -1).limit(10).to_list(10)
    return [LeaderboardEntry(**parse_from_mongo(player)) for player in players]

# Game Session Routes
@api_router.post("/games", response_model=GameSession)
async def create_game_session(game_data: GameSessionCreate):
    game = GameSession(**game_data.dict())
    game_dict = prepare_for_mongo(game.dict())
    await db.game_sessions.insert_one(game_dict)
    
    # Update player stats
    await update_player_stats(game_data.player1_name, game_data.winner == game_data.player1_name)
    if game_data.player2_name:
        await update_player_stats(game_data.player2_name, game_data.winner == game_data.player2_name)
    
    return game

async def update_player_stats(player_name: str, won: bool):
    """Update player statistics after a game"""
    player = await db.players.find_one({"name": player_name})
    if not player:
        # Create player if doesn't exist
        new_player = Player(
            name=player_name,
            consecutive_wins=1 if won else 0,
            best_streak=1 if won else 0,
            total_games=1,
            total_wins=1 if won else 0
        )
        await db.players.insert_one(prepare_for_mongo(new_player.dict()))
        return
    
    # Update existing player
    total_games = player.get('total_games', 0) + 1
    total_wins = player.get('total_wins', 0) + (1 if won else 0)
    consecutive_wins = player.get('consecutive_wins', 0)
    best_streak = player.get('best_streak', 0)
    
    if won:
        consecutive_wins += 1
        if consecutive_wins > best_streak:
            best_streak = consecutive_wins
    else:
        consecutive_wins = 0
    
    await db.players.update_one(
        {"name": player_name},
        {"$set": {
            "consecutive_wins": consecutive_wins,
            "best_streak": best_streak,
            "total_games": total_games,
            "total_wins": total_wins
        }}
    )

@api_router.get("/games", response_model=List[GameSession])
async def get_recent_games():
    games = await db.game_sessions.find().sort("created_at", -1).limit(20).to_list(20)
    return [GameSession(**parse_from_mongo(game)) for game in games]

# Basic status routes
@api_router.get("/")
async def root():
    return {"message": "Ping Pong Game API is running!"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()