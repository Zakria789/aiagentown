"""
Quick script to add TM Dialer configuration
Run this once to set up your TM Dialer credentials
"""
import asyncio
import sys
from sqlalchemy import text
from app.database import async_session_maker


async def setup_tmdialer():
    """Add TM Dialer configuration to database"""
    
    print("\n🔧 TM Dialer Setup")
    print("=" * 50)
    
    # Configuration
    config = {
        'username': '1004',
        'password': 'tmai',
        'dialer_url': 'https://tmdialer.gradientconnectedai.com/',
        'dialer_type': 'tmdialer',
        'agent_id': 1,  # Change this to your AI agent ID
        'auto_login': True,
        'auto_unpause': True,
        'start_time': '09:00',
        'end_time': '18:00',
        'timezone': 'America/New_York',
        'is_active': True,
        'schedule_enabled': True
    }
    
    print("\n📋 Configuration:")
    print(f"   Dialer URL: {config['dialer_url']}")
    print(f"   Username: {config['username']}")
    print(f"   Password: {'*' * len(config['password'])}")
    print(f"   Agent ID: {config['agent_id']}")
    print(f"   Schedule: {config['start_time']} - {config['end_time']}")
    print(f"   Timezone: {config['timezone']}")
    
    confirm = input("\n✅ Add this configuration? (yes/no): ")
    
    if confirm.lower() not in ['yes', 'y']:
        print("❌ Setup cancelled.")
        return
    
    async with async_session_maker() as db:
        try:
            # Check if already exists
            check_query = text("SELECT COUNT(*) FROM dialer_users WHERE username = :username")
            result = await db.execute(check_query, {'username': config['username']})
            count = result.scalar()
            
            if count > 0:
                print(f"\n⚠️  Dialer user '{config['username']}' already exists!")
                update = input("   Update existing configuration? (yes/no): ")
                
                if update.lower() in ['yes', 'y']:
                    # Update existing
                    update_query = text("""
                        UPDATE dialer_users 
                        SET password = :password,
                            dialer_url = :dialer_url,
                            dialer_type = :dialer_type,
                            auto_login = :auto_login,
                            auto_unpause = :auto_unpause,
                            start_time = :start_time,
                            end_time = :end_time,
                            timezone = :timezone,
                            is_active = :is_active,
                            schedule_enabled = :schedule_enabled
                        WHERE username = :username
                    """)
                    await db.execute(update_query, config)
                    await db.commit()
                    print("\n✅ TM Dialer configuration updated successfully!")
                else:
                    print("❌ Update cancelled.")
                    return
            else:
                # Insert new
                insert_query = text("""
                    INSERT INTO dialer_users 
                    (username, password, dialer_url, dialer_type, agent_id, 
                     auto_login, auto_unpause, start_time, end_time, 
                     timezone, is_active, schedule_enabled)
                    VALUES 
                    (:username, :password, :dialer_url, :dialer_type, :agent_id,
                     :auto_login, :auto_unpause, :start_time, :end_time,
                     :timezone, :is_active, :schedule_enabled)
                """)
                await db.execute(insert_query, config)
                await db.commit()
                print("\n✅ TM Dialer configuration added successfully!")
            
            print("\n📝 Next Steps:")
            print("   1. Server restart karo: Ctrl+C aur phir uvicorn chalaao")
            print("   2. Test login karo:")
            print("      python test_tmdialer_login.py")
            print("   3. Auto-login test karo schedule se")
            
            print("\n🎯 Configuration Details:")
            print(f"   • Auto-login enabled at: {config['start_time']}")
            print(f"   • Auto-unpause: Enabled")
            print(f"   • Schedule: {config['start_time']} to {config['end_time']}")
            print(f"   • Days: All days (configure via API if needed)")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            await db.rollback()
            sys.exit(1)


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("   TM Dialer Configuration Setup")
    print("=" * 50)
    
    try:
        asyncio.run(setup_tmdialer())
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user.")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)
