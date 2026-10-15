# test_extract_debug.py
import json
from config.settings import settings
from extraction.extractor import SchemeGraphExtractor

with open(settings.DATA_DIR / "tn_agriculture_schemes.json", "r", encoding="utf-8") as f:
    schemes = json.load(f)

print(f"Loaded {len(schemes)} schemes from disk.")
first_scheme = schemes[0]
print(f"Testing extraction on: {first_scheme.get('title')}")

extractor = SchemeGraphExtractor()
try:
    result = extractor.extract_from_record(first_scheme)
    print(f"Success! Extracted {len(result.nodes)} nodes and {len(result.relationships)} relationships.")
    print("Sample node:", result.nodes[0] if result.nodes else "None")
except Exception as e:
    import traceback
    print("FAILED with error:")
    traceback.print_exc()