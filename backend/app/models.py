from datetime import datetime
from . import db


class UserInfo(db.Model):
    __tablename__ = 'userinfo'

    # 映射到你的 MySQL 表结构
    user_id = db.Column('userId', db.String(255), primary_key=True)
    password = db.Column(db.String(255), nullable=True)

    def to_public(self):
        return {
            'id': self.user_id,
            'username': self.user_id,
        }

class Instance(db.Model):
    __tablename__ = 'instances'

    # 将 id 与表的 BIGINT 对齐
    id = db.Column(db.BigInteger, primary_key=True)
    # 映射到你的表字段
    instance_name = db.Column('instanceName', db.String(128), nullable=False)
    host = db.Column('instanceHost', db.String(255), nullable=False)

    # 与表结构一致：非空
    username = db.Column('instanceUserName', db.String(128), nullable=False)
    password = db.Column('instanceUserPassword', db.String(255), nullable=False)

    db_type = db.Column('instanceType', db.String(64), nullable=False, default='MySQL')

    # 新增：将端口从内存属性改为持久化列
    port = db.Column('instancePort', db.Integer, nullable=False, default=3306)

    # 与表结构一致：非空并建立索引
    user_id = db.Column('userId', db.String(255), nullable=False, index=True)

    # 新增：映射数据库中的 addTime 列（你已在 MySQL 添加 TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP）
    add_time = db.Column('addTime', db.DateTime, nullable=False)

    @property
    def status(self) -> str:
        return getattr(self, '_status_mem', 'running') or 'running'

    @status.setter
    def status(self, value: str):
        self._status_mem = str(value) if value else 'running'

    def to_dict(self):
        return {
            'id': self.id,
            'instanceName': self.instance_name,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'dbType': self.db_type,
            'status': self.status,
            'userId': self.user_id,
            'addTime': self.add_time.isoformat() if self.add_time else None,
        }