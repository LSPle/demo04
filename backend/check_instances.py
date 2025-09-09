from app import create_app
from app.models import Instance

app = create_app()
app.app_context().push()

instances = Instance.query.all()
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"总共有 {len(instances)} 个实例:")
for i in instances:
    logger.info(f"ID: {i.id}, Name: {i.instance_name}, Host: {i.host}:{i.port}, Status: {i.status}")