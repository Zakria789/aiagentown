"""
Migration: Add HumeAI fields to agents table
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine
import asyncio
from app.config import settings


async def upgrade():
    """Add campaign_script, hume_config_id, hume_voice_id to agents table"""
    
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        # SQLite: Check if columns exist using PRAGMA
        check_query = text("PRAGMA table_info(agents)")
        result = await conn.execute(check_query)
        columns = [row[1] for row in result.fetchall()]  # Column name is at index 1
        
        # Add campaign_script if not exists
        if 'campaign_script' not in columns:
            print("Adding campaign_script column...")
            await conn.execute(text("""
                ALTER TABLE agents 
                ADD COLUMN campaign_script TEXT
            """))
            print("✅ campaign_script column added")
        else:
            print("⏭️  campaign_script column already exists")
        
        # Add hume_config_id if not exists
        if 'hume_config_id' not in columns:
            print("Adding hume_config_id column...")
            await conn.execute(text("""
                ALTER TABLE agents 
                ADD COLUMN hume_config_id VARCHAR(100)
            """))
            print("✅ hume_config_id column added")
        else:
            print("⏭️  hume_config_id column already exists")
        
        # Add hume_voice_id if not exists
        if 'hume_voice_id' not in columns:
            print("Adding hume_voice_id column...")
            await conn.execute(text("""
                ALTER TABLE agents 
                ADD COLUMN hume_voice_id VARCHAR(100)
            """))
            print("✅ hume_voice_id column added")
        else:
            print("⏭️  hume_voice_id column already exists")
        
        print("\n✅ Migration completed successfully!")


async def downgrade():
    """Remove HumeAI fields from agents table"""
    
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        print("Removing HumeAI fields...")
        
        await conn.execute(text("ALTER TABLE agents DROP COLUMN IF EXISTS campaign_script"))
        await conn.execute(text("ALTER TABLE agents DROP COLUMN IF EXISTS hume_config_id"))
        await conn.execute(text("ALTER TABLE agents DROP COLUMN IF EXISTS hume_voice_id"))
        
        print("✅ Rollback completed!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        print("🔽 Running downgrade...")
        asyncio.run(downgrade())
    else:
        print("🔼 Running upgrade...")
        asyncio.run(upgrade())
