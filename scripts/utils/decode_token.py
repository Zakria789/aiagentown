import jwt
import json
from datetime import datetime

# Token from login
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImFnZW50X2lkIjoxLCJleHAiOjE3NjM0NTk1NTYsImlhdCI6MTc2MzQ1NTk1Nn0.jlFIM0Zs6cSEX06JH6n0GTGtUoJ2l455NvmP7_T8HrQ"

# Decode without verification
decoded = jwt.decode(token, options={"verify_signature": False})
print("Token payload:")
print(json.dumps(decoded, indent=2))

# Check expiry
exp_timestamp = decoded.get('exp')
if exp_timestamp:
    exp_time = datetime.fromtimestamp(exp_timestamp)
    now = datetime.now()
    print(f"\nExpiry time: {exp_time}")
    print(f"Current time: {now}")
    print(f"Token valid: {now < exp_time}")
    print(f"Time remaining: {exp_time - now}")
