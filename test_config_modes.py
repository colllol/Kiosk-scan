#!/usr/bin/env python3
"""
Test config.py in different modes (script vs EXE simulation)
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

def test_script_mode():
    """Test config loading in script mode"""
    print("🧪 Testing SCRIPT mode...")
    
    # Temporarily rename config.json to test fallback
    config_path = Path("config.json")
    backup_path = None
    
    if config_path.exists():
        backup_path = Path("config.json.backup")
        config_path.rename(backup_path)
        print("  Temporarily moved config.json to test defaults")
    
    try:
        # Import config module (should use defaults)
        import config
        print(f"  ✓ Config loaded in script mode")
        print(f"  • Queue API: {config.QUEUE_SYSTEM_API}")
        print(f"  • Host: {config.SERVER_HOST}")
        print(f"  • Port: {config.SERVER_PORT}")
        
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False
    finally:
        # Restore config.json
        if backup_path and backup_path.exists():
            backup_path.rename(config_path)
            print("  Restored config.json")

def test_exe_mode_simulation():
    """Simulate EXE mode by setting frozen attribute"""
    print("\n🧪 Testing EXE mode simulation...")
    
    # Create a temporary directory for EXE simulation
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create a fake EXE
        fake_exe = tmpdir / "fake_backend.exe"
        fake_exe.write_bytes(b"fake exe")
        
        # Create config.json in temp dir
        test_config = {
            "apiEndpoints": {
                "queueSystem": "http://test-server:9999/api/ticket/create"
            },
            "backendSettings": {
                "host": "127.0.0.1",
                "port": 9999,
                "uploadDir": "test_uploads",
                "pdfDir": "test_pdfs"
            }
        }
        
        config_file = tmpdir / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, indent=2)
        
        print(f"  Created test config at: {config_file}")
        
        # Save original sys attributes
        original_frozen = getattr(sys, 'frozen', False)
        original_executable = sys.executable
        
        try:
            # Simulate EXE mode
            sys.frozen = True
            sys.executable = str(fake_exe)
            
            # Mock the config module to reload
            if 'config' in sys.modules:
                del sys.modules['config']
            
            # Import config module
            import config
            print(f"  ✓ Config loaded in EXE mode simulation")
            print(f"  • Queue API: {config.QUEUE_SYSTEM_API}")
            print(f"  • Host: {config.SERVER_HOST}")
            print(f"  • Port: {config.SERVER_PORT}")
            print(f"  • Upload Dir: {config.UPLOAD_DIR}")
            print(f"  • PDF Dir: {config.PDF_DIR}")
            
            # Verify values from test config
            assert config.QUEUE_SYSTEM_API == "http://test-server:9999/api/ticket/create", "Queue API mismatch"
            assert config.SERVER_HOST == "127.0.0.1", "Host mismatch"
            assert config.SERVER_PORT == 9999, "Port mismatch"
            assert config.UPLOAD_DIR == "test_uploads", "Upload dir mismatch"
            assert config.PDF_DIR == "test_pdfs", "PDF dir mismatch"
            
            print("  ✓ All values match test configuration")
            return True
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Restore original sys attributes
            sys.frozen = original_frozen
            sys.executable = original_executable

def test_config_paths():
    """Test config path resolution"""
    print("\n🧪 Testing config path resolution...")
    
    from backend.config import get_config_paths
    
    # Test script mode paths
    print("  Script mode paths:")
    paths = get_config_paths()
    for i, path in enumerate(paths, 1):
        exists = "✓" if os.path.exists(path) else "✗"
        print(f"    {i}. {exists} {path}")
    
    return True

def main():
    print("🔍 Testing Configuration System")
    print("=" * 50)
    
    tests_passed = 0
    tests_total = 0
    
    # Run tests
    tests = [
        ("Script Mode", test_script_mode),
        ("EXE Mode Simulation", test_exe_mode_simulation),
        ("Config Paths", test_config_paths),
    ]
    
    for test_name, test_func in tests:
        tests_total += 1
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED\n")
                tests_passed += 1
            else:
                print(f"❌ {test_name}: FAILED\n")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}\n")
    
    print("=" * 50)
    print(f"📊 Results: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("✅ All tests passed! Configuration system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the configuration system.")

if __name__ == "__main__":
    main()