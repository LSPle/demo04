import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.models import Instance
from app.utils.db_connection import db_connection_manager

instance_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0

app = create_app()
with app.app_context():
    inst = Instance.query.get(instance_id)
    if not inst:
        print("Instance not found")
        sys.exit(1)
    print("Instance:", inst.id, inst.instance_name, inst.host, inst.port, inst.username, inst.db_type)
    ok, rows, err = db_connection_manager.execute_query(inst, "SHOW DATABASES")
    print("SHOW DATABASES ok:", ok, "err:", err, "rows:", len(rows) if rows else 0)
    if rows:
        print("First DBs:", [r[0] for r in rows][:10])
