from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field, validator
from psycopg2.extras import RealDictCursor
from database.connection import db_connection, now_ts
from models.auth import UserOut
from routes.auth import get_current_user
from routes.security import get_optional_user
from config import settings

router = APIRouter(prefix="/community", tags=["community"])