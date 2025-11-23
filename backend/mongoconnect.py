import os
import sys
from pymongo import MongoClient
from pymongo.errors import ConfigurationError, PyMongoError

FALLBACK_URI = None  # No hardcoded URI; require MONGO_URI environment variable

def _mask_uri(uri: str) -> str:
    try:
        if "@" in uri and "://" in uri:
            scheme, rest = uri.split("://", 1)
            creds, host = rest.split("@", 1)
            user = creds.split(":", 1)[0] if ":" in creds else creds
            return f"{scheme}://{user}:***@{host}"
    except Exception:
        pass
    return uri

def check_dns_lib():
    try:
        import dns.resolver  # from dnspython
        import dns
        print("dnspython available:", getattr(dns, "__version__", "version unknown"))
        return True
    except Exception:
        print("dnspython NOT installed. Install it with: py -m pip install dnspython")
        return False

def main():
    # Optionally load a .env file if python-dotenv is installed
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print(".env loaded (if present)")
    except Exception:
        pass

    uri = os.environ.get("MONGO_URI") or FALLBACK_URI
    if not uri:
        print("MONGO_URI environment variable is not set.")
        print("Set it in your environment or create a .env file with:")
        print("  MONGO_URI='mongodb+srv://<user>:<password>@cluster0.example.net/...'\n")
        sys.exit(1)

    print("Testing Mongo URI:", _mask_uri(uri))
    check_dns_lib()

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        print("Connected OK")
        print("Databases (sample):", client.list_database_names()[:10])
        sys.exit(0)
    except ConfigurationError as ce:
        print("ConfigurationError:", ce)
        print("Likely SRV/DNS parsing issue. Actions:")
        print("  1) Ensure dnspython is installed: py -m pip install dnspython")
        print("  2) Verify MONGO_URI exactly matches Atlas 'Connect -> Connect your application' (use full host)")
        print("  3) Use Standard (mongodb://...) connection string if SRV lookups are blocked by network")
        sys.exit(2)
    except PyMongoError as pe:
        print("PyMongoError:", pe)
        sys.exit(3)
    except Exception as e:
        print("Unexpected error:", e)
        sys.exit(4)

if __name__ == "__main__":
    main()