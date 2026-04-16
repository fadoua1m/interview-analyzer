from supabase import create_client, Client
from sqlalchemy.orm import declarative_base
from app.config import settings

supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_key,
)

Base = declarative_base()