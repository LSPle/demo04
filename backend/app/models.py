from datetime import datetime
from . import db


class UserInfo(db.Model):
    __tablename__ = 'userinfo'

    user_id = db.Column('userId', db.String(255), primary_key=True)
    password = db.Column(db.String(255), nullable=True)

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
    status = db.Column('instanceStatus', db.String(32), nullable=False, default='running')

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
            'addTime': self.add_time.strftime('%Y-%m-%d %H:%M:%S') if self.add_time else None,
        }