from typing import Optional, List
from dataclasses import dataclass, asdict, is_dataclass
from datetime import datetime
from copy import deepcopy
from tinydb import TinyDB, Query
import uuid
import json


class EnhancedJSONEncoder(json.JSONEncoder):
    # Reference:
    # https://stackoverflow.com/questions/51286748/make-the-python-json-encoder-support-pythons-new-dataclasses
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        return super().default(o)


@dataclass
class Category:
    name: str
    subcategory: Optional[str] = None


@dataclass
class Item:
    item_id: str
    name: str
    amount: float
    description: str
    date: datetime
    category: Optional[Category] = None

    def __str__(self):
        return self.to_json_str(indent=4)

    @classmethod
    def create(cls, name: str, amount: float, description: str, date_str: str, category: Optional[Category] = None):
        item_id = str(uuid.uuid4())  # Generate a unique ID
        # item_id = str(name + '-' + date_str)  # Generate a unique ID
        date = datetime.strptime(date_str, "%Y-%m-%d")  # Parse the date string into a datetime object
        return cls(item_id=item_id, name=name, amount=amount, description=description, date=date, category=category)

    @classmethod
    def create_expense_item(cls, name: str, amount: float, description: str, date_str: str,
                            category: Optional[Category] = None):
        if amount >= 0:
            raise ValueError('Expense Item cannot be positive.')

        return cls.create(name, amount, description, date_str, category=category)

    @classmethod
    def create_income_item(cls, name: str, amount: float, description: str, date_str: str,
                           category: Optional[Category] = None):
        if amount <= 0:
            raise ValueError('Income Item cannot be negative.')

        return cls.create(name, amount, description, date_str, category=category)

    @classmethod
    def from_json_str(cls, json_str):
        data_dict = json.loads(json_str)

        # Convert date string back to datetime object
        data_dict['date'] = datetime.strptime(data_dict['date'], "%Y-%m-%d %H:%M:%S")

        # Check if category is present and reconstruct Category object
        if data_dict['category']:
            data_dict['category'] = Category(**data_dict['category'])

        return cls(**data_dict)

    def to_json_str(self, *args, **kwargs) -> str:
        return json.dumps(self.to_serializable_dict(), *args, cls=EnhancedJSONEncoder, **kwargs)

    def to_serializable_dict(self) -> dict:
        data_dct = deepcopy(self.__dict__)

        # Check if category is not None
        if data_dct['category']:
            data_dct['category'] = asdict(data_dct['category'])

        # Stringify Date
        data_dct['date'] = str(data_dct['date'])
        return data_dct


class ItemsDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db = TinyDB(self.db_path)

    def __len__(self):
        return len(self._db)

    def print_db(self):
        for item in self.get_all_items():
            print(item.to_json_str(indent=4))

    def insert_item(self, item: Item) -> None:
        data_dict = dict(json.loads(item.to_json_str()))
        self._db.insert(data_dict)

    def insert_items(self, items: List[Item]) -> None:
        self._db.insert_multiple([dict(json.loads(item.to_json_str())) for item in items])

    def update_items(self, update_dict: dict, query: Query) -> None:
        self._db.update(update_dict, query)

    def upsert_item(self, item: Item) -> None:
        dct = item.to_serializable_dict()
        self._db.upsert(dct, Query().item_id == str(dct['item_id']))

    def delete_items(self, cond: Query) -> None:
        self._db.remove(cond)

    def delete_item(self, item: Item) -> None:
        self.delete_items(Query().item_id == item.item_id)

    def delete_all_items(self):
        self._db.truncate()

    def get_all_items(self) -> List[Item]:
        return [Item.from_json_str(json.dumps(doc)) for doc in self._db.all()]

    def get_items_by_date_range(self, start: str, end: str):
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
        return [item for item in self.get_all_items() if start_date <= item.date <= end_date]
