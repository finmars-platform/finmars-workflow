from workflow.deprecated.extensions import db
from workflow.exceptions import UserNotFound
from workflow.models import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

    def update(self):
        user = self.query.filter_by(username=self.username).first()
        if not user:
            raise UserNotFound(f"User {self.username} not found")

        user.password = self.password

        self.commit()

    def delete(self):
        db.session.delete(self)

        self.commit()

    def to_dict(self):
        d = super().to_dict()
        d.update({"username": self.username, "password": self.password})
        return d
