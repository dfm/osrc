# -*- coding: utf-8 -*-

from flask.ext.sqlalchemy import SQLAlchemy

__all__ = ["db", "User", "Repo"]


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "gh_users"
    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.Text)
    name = db.Column(db.Text)
    login = db.Column(db.Text, index=True)
    location = db.Column(db.Text)
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    avatar_url = db.Column(db.Text)
    etag = db.Column(db.Text)

    # Computed by OSRC.
    timezone = db.Column(db.Integer)
    active = db.Column(db.Boolean, default=True)

    def basic_dict(self):
        return dict(
            id=self.id,
            username=self.login,
            type=self.user_type,
            timezone=self.timezone,
            location=dict(
                name=self.location,
                lat=self.lat,
                lng=self.lng,
            ),
            avatar_url=self.avatar_url,
            fullname=self.name if self.name is not None else self.login,
        )


class Repo(db.Model):
    __tablename__ = "gh_repos"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    fullname = db.Column(db.Text, index=True)
    description = db.Column(db.Text)
    language = db.Column(db.Text)
    fork = db.Column(db.Boolean)
    etag = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)

    # `stargazers_count`
    star_count = db.Column(db.Integer)
    # `subscribers_count`
    watcher_count = db.Column(db.Integer)
    # `forks_count`
    fork_count = db.Column(db.Integer)
    # `open_issues_count`
    issues_count = db.Column(db.Integer)
    # `updated_at`
    last_updated = db.Column(db.DateTime)

    owner_id = db.Column(db.Integer, db.ForeignKey("gh_users.id"))
    owner = db.relationship(User, backref=db.backref("repos", lazy="dynamic"))

    def basic_dict(self):
        return dict(
            id=self.id,
            name=self.fullname,
            description=self.description,
            language=self.language,
            stars=self.star_count,
            watchers=self.watcher_count,
            forks=self.fork_count,
            issues=self.issues_count,
        )
