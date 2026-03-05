import os
import sys
from inspect import signature

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.utils.db_connection import db_connection_manager

params = signature(db_connection_manager.create_connection).parameters
print("connect_timeout" in params)
