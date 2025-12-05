"""
Quick Admin Password Fix
Fixes bcrypt password hash issue - uses bcrypt directly
"""
import sqlite3
import bcrypt

# Connect to database
conn = sqlite3.connect('callcenter.db')
cursor = conn.cursor()

# Delete old admin
cursor.execute("DELETE FROM agents WHERE agent_id = 'admin'")
print("✅ Old admin deleted")

# Create new password hash using bcrypt directly
password = "admin123"
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
print(f"✅ New password hash created: {password_hash[:50]}...")

# Insert new admin
cursor.execute("""
    INSERT INTO agents (
        agent_id, password_hash, full_name, email, phone, 
        role, permissions, is_active
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (
    'admin',
    password_hash,
    'System Administrator',
    'admin@callcenter.com',
    '+1234567890',
    'admin',
    '["all"]',
    1
))

conn.commit()
print("✅ New admin created successfully")

# Verify
cursor.execute("SELECT agent_id, full_name, role FROM agents WHERE agent_id = 'admin'")
result = cursor.fetchone()
if result:
    print(f"✅ Verified: {result[0]} - {result[1]} ({result[2]})")
    print("\n🎉 Admin credentials:")
    print("   Username: admin")
    print("   Password: admin123")
else:
    print("❌ Verification failed")

conn.close()
