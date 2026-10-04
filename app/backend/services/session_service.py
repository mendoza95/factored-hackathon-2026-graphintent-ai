# app/backend/services/session_service.py
from typing import Any, Dict


class SessionService:
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get_session(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "active_dispute": False,
                "dispute_type": None,
                "claimed_amount": None,
                "currency": None,
                "step": None,
                "disputed_transaction_ids": [],  # Historial en memoria de la sesión
            }
        return self._sessions[session_id]

    def add_disputed_transaction(self, session_id: str, transaction_id: str) -> None:
        """Agrega un ID de transacción a la lista de disputadas en la sesión."""
        session = self.get_session(session_id)
        disputed_ids = session.get("disputed_transaction_ids", [])

        tx_id_str = str(transaction_id)
        if tx_id_str not in disputed_ids:
            disputed_ids.append(tx_id_str)
            self.update_session(session_id, {"disputed_transaction_ids": disputed_ids})

    def is_transaction_disputed(self, session_id: str, transaction_id: str) -> bool:
        session = self.get_session(session_id)
        return transaction_id in session["disputed_transaction_ids"]

    def update_session(self, session_id: str, data: Dict[str, Any]) -> None:
        session = self.get_session(session_id)
        session.update(data)

    def clear_session(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]


session_service = SessionService()
