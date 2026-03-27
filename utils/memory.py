import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional


class MemoryStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _read(self) -> Dict[str, List[Dict[str, str]]]:
        with self._lock:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}

    def _write(self, data: Dict[str, List[Dict[str, str]]]) -> None:
        with self._lock:
            self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_history(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        data = self._read()
        return data.get(session_id, [])[-limit:]

    def get_full_history(self, session_id: str) -> List[Dict[str, str]]:
        data = self._read()
        return data.get(session_id, [])

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        image_url: Optional[str] = None,
    ) -> None:
        data = self._read()
        record = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if image_url:
            record["image_url"] = image_url

        data.setdefault(session_id, []).append(record)
        self._write(data)

    def clear(self, session_id: str) -> None:
        data = self._read()
        if session_id in data:
            del data[session_id]
            self._write(data)
