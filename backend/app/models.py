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

    id = db.Column(db.Integer, primary_key=True)
    # 映射到你的表字段
    instance_name = db.Column('instanceName', db.String(128), nullable=False)
    host = db.Column('instanceHost', db.String(255), nullable=False)
    username = db.Column('instanceUserName', db.String(128), nullable=True)
    password = db.Column('instanceUserPassword', db.String(255), nullable=True)
    db_type = db.Column('instanceType', db.String(64), nullable=False, default='MySQL')
    # 端口与状态：你的表中无对应列，这里用内存属性并提供默认值
    # 如需持久化，请在数据库中增加相应列并改为 db.Column
    # 归属用户
    user_id = db.Column('userId', db.String(255), nullable=True, index=True)

    # 不映射 create_time 到数据库（你的表没有该列）

    @property
    def port(self) -> int:
        try:
            return int(getattr(self, '_port_mem', 3306))
        except Exception:
            return 3306

    @port.setter
    def port(self, value):
        try:
            self._port_mem = int(value)
        except Exception:
            self._port_mem = 3306

    @property
    def status(self) -> str:
        return getattr(self, '_status_mem', 'running') or 'running'

    @status.setter
    def status(self, value: str):
        self._status_mem = str(value) if value else 'running'

    def to_dict(self):
        # 返回前端预期的驼峰命名字段
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

            'createTime': None,
        }