"""
Production Folder Reorganization Script
Organizes scattered files into proper production structure
"""
import os
import shutil
from pathlib import Path

# Get project root
ROOT = Path(__file__).parent

# Create directory structure
DIRS_TO_CREATE = [
    "scripts/setup",
    "scripts/utils", 
    "bridges",
    "tests/api",
    "tests/integration",
    "tests/unit",
    "archive"  # For old files
]

# Files to move
MOVES = {
    "scripts/setup": [
        "setup_database.py",
        "create_admin.py",
        "setup_tmdialer.py"
    ],
    "scripts/utils": [
        "check_admin.py",
        "check_db_agent.py",
        "check_hume_config.py",
        "check_manual_update.py",
        "check_password.py",
        "check_prompt.py",
        "decode_token.py",
        "get_voices.py",
        "list_recent_configs.py",
        "verify_config.py",
        "find_correct_structure.py"
    ],
    "bridges": [
        "calltools_webrtc_bridge.py",
        "calltools_audio_bridge.py"
    ],
    "tests": [
        "test_agent_creation.ps1",
        "test_ai_learning.py",
        "test_api.py",
        "test_builtin_tools.py",
        "test_calltools_humeai_integration.py",
        "test_create_agent_with_hume.ps1",
        "test_create_agent.ps1",
        "test_create_hume_agent.py",
        "test_dashboard_configs.py",
        "test_fixed.py",
        "test_hume_agent.ps1",
        "test_hume_direct.py",
        "test_hume_integration.ps1",
        "test_hume_key.py",
        "test_hume_models.py",
        "test_login_fixed.py",
        "test_login_simple.py",
        "test_login.ps1",
        "test_production_ready.py",
        "test_service.py",
        "test_system_simple.py",
        "test_tmdialer_complete.py",
        "test_tmdialer_final.py",
        "test_tmdialer_login.py",
        "test_verify.py",
        "test3.py",
        "final_complete_test.py",
        "final_test.py",
        "quick_test.py",
        "direct_service_test.py"
    ],
    "archive": [
        "DASHBOARD_UI_EXPLANATION.py",
        "hume_agent_config.json",
        "MANUAL_CONFIG_INSTRUCTIONS.txt",
        "create_test_agent.ps1"
    ]
}


def create_directories():
    """Create necessary directories"""
    print("📁 Creating directory structure...")
    for dir_path in DIRS_TO_CREATE:
        full_path = ROOT / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {dir_path}")


def move_files():
    """Move files to appropriate directories"""
    print("\n📦 Moving files...")
    
    for dest_dir, files in MOVES.items():
        dest_path = ROOT / dest_dir
        
        for filename in files:
            src = ROOT / filename
            
            if src.exists() and src.is_file():
                dest = dest_path / filename
                
                try:
                    shutil.move(str(src), str(dest))
                    print(f"   ✅ {filename} → {dest_dir}/")
                except Exception as e:
                    print(f"   ❌ Failed to move {filename}: {e}")
            else:
                print(f"   ⚠️  {filename} not found (may be already moved)")


def create_init_files():
    """Create __init__.py files for Python packages"""
    print("\n📝 Creating __init__.py files...")
    
    init_dirs = [
        "scripts",
        "scripts/setup",
        "scripts/utils",
        "bridges",
        "tests"
    ]
    
    for dir_path in init_dirs:
        init_file = ROOT / dir_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Package initialization\n")
            print(f"   ✅ {dir_path}/__init__.py")


def update_imports():
    """Show import changes needed"""
    print("\n⚠️  IMPORTANT: Update imports in your code!")
    print("\n   Old imports:")
    print("   from calltools_webrtc_bridge import WebRTCAudioBridge")
    print("\n   New imports:")
    print("   from bridges.calltools_webrtc_bridge import WebRTCAudioBridge")


def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║  Production Folder Reorganization                        ║
║  Organizing files into proper structure...               ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    try:
        create_directories()
        move_files()
        create_init_files()
        update_imports()
        
        print("\n✅ Reorganization complete!")
        print("\n📋 Next steps:")
        print("   1. Test the application: python app/main.py")
        print("   2. Update any hardcoded imports")
        print("   3. Update documentation paths")
        print("   4. Commit changes to version control")
        
    except Exception as e:
        print(f"\n❌ Error during reorganization: {e}")
        print("   Please fix errors and run again")


if __name__ == "__main__":
    main()
