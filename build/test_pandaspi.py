"""Test pandaspi import inside the PyInstaller bundle."""
import sys
import os

print(f"Python: {sys.version}")
print(f"Frozen: {getattr(sys, 'frozen', False)}")
print(f"MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")

# Test 1: importlib.metadata
try:
    from importlib.metadata import version
    v = version("pandaspi")
    print(f"pandaspi metadata version: {v}")
except Exception as e:
    print(f"pandaspi metadata FAILED: {e}")

# Test 2: direct import
try:
    import pandaspi
    print(f"import pandaspi: OK")
    print(f"  __file__: {pandaspi.__file__}")
    print(f"  HAS SessionWeb: {hasattr(pandaspi, 'SessionWeb')}")
except ImportError as e:
    print(f"import pandaspi FAILED: {e}")
except Exception as e:
    print(f"import pandaspi ERROR: {type(e).__name__}: {e}")

# Test 3: webapi submodule
try:
    import pandaspi.webapi
    print(f"import pandaspi.webapi: OK")
except Exception as e:
    print(f"import pandaspi.webapi FAILED: {type(e).__name__}: {e}")

# Test 4: SessionWeb
try:
    from pandaspi.webapi import SessionWeb
    print(f"from pandaspi.webapi import SessionWeb: OK")
except Exception as e:
    print(f"SessionWeb import FAILED: {type(e).__name__}: {e}")

input("Press Enter to exit...")
