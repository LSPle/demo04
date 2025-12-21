from datetime import datetime
from app import db

'''核心业务模块都依赖的数据库模型，这是SQLAlchemy的模型类,通过python映射到数据库'''
class UserInfo(db.Model):
    __tablename__ = 'userinfo'

    user_id = db.Column('userId', db.String(255), primary_key=True)
    password = db.Column(db.String(255), nullable=True)

    # 在auth.py中被调用
    def to_public(self):
        return {
            'id': self.user_id,
            'username': self.user_id,
        }


class Instance(db.Model):
    __tablename__ = 'instances'

    id = db.Column(db.BigInteger, primary_key=True)
    instance_name = db.Column('instanceName', db.String(128), nullable=False)
    host = db.Column('instanceHost', db.String(255), nullable=False)
    username = db.Column('instanceUserName', db.String(128), nullable=False)
    password = db.Column('instanceUserPassword', db.String(255), nullable=False)
    db_type = db.Column('instanceType', db.String(64), nullable=False, default='MySQL')
    port = db.Column('instancePort', db.Integer, nullable=False, default=3306)
    user_id = db.Column('userId', db.String(255), nullable=False, index=True)
    add_time = db.Column('addTime', db.DateTime, nullable=False, default=datetime.utcnow)

    # instances.py中被调用
    def to_dict(self):
        return {
            'id': self.id,
            'instanceName': self.instance_name,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'dbType': self.db_type,
            'userId': self.user_id,
            'addTime': self.add_time.strftime('%Y-%m-%d %H:%M:%S') if self.add_time else None,
            # 兼容前端字段名：创建时间
            'createTime': self.add_time.strftime('%Y-%m-%d %H:%M:%S') if self.add_time else None,
        }
