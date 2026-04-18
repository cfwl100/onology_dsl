import base64
import zlib
from pathlib import Path

payload = (Path(__file__).resolve().parents[2] / "shared" / "soql_to_oql_payload.b85").read_text(encoding="utf-8")
exec(zlib.decompress(base64.b85decode(payload)).decode())
