import base64
import runpy
import tempfile
import zlib
from pathlib import Path

payload = (Path(__file__).resolve().parents[2] / "shared" / "soql_to_oql_payload.b85").read_text(encoding="utf-8")
code = zlib.decompress(base64.b85decode(payload)).decode()
path = Path(tempfile.gettempdir()) / "soql_to_oql_impl.py"
path.write_text(code, encoding="utf-8")
runpy.run_path(str(path), run_name="__main__")
