from abc import ABC, abstractmethod
from typing import Optional

from app.backend.schemas.dispute import ComplaintSchema, TransactionSchema


class BaseDatabase(ABC):
    @abstractmethod
    def get_customer(self, customer_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def get_customer_by_document(
        self, document_type: str, document_number: str
    ) -> Optional[dict]:
        pass

    @abstractmethod
    def get_product(self, product_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def get_transaction(self, transaction_id: str) -> Optional[TransactionSchema]:
        pass

    @abstractmethod
    def get_customer_transactions(self, customer_id: str) -> list[TransactionSchema]:
        pass

    @abstractmethod
    def create_complaint(self, complaint: ComplaintSchema) -> ComplaintSchema:
        pass

    @abstractmethod
    def get_complaint(self, complaint_id: str) -> Optional[ComplaintSchema]:
        pass
