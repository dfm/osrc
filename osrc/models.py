# -*- coding: utf-8 -*-

from flask.ext.sqlalchemy import SQLAlchemy

from .utils import load_resource

__all__ = ["db", "User", "Repo"]


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "gh_users"
    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.Text)
    name = db.Column(db.Text)
    login = db.Column(db.Text)
    location = db.Column(db.Text)
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    avatar_url = db.Column(db.Text)
    etag = db.Column(db.Text)

    # Computed by OSRC.
    timezone = db.Column(db.Integer)
    active = db.Column(db.Boolean, default=True)

    def short_dict(self):
        name = self.name if self.name is not None else self.login
        return dict(
            id=self.id,
            login=self.login,
            type=self.user_type,
            name=name,
            avatar_url=self.avatar_url,
        )

    def basic_dict(self, stopwords=["the", "dr", "mr", "mrs"]):
        short = self.short_dict()
        fn = [t for t in short["name"].split()
              if t.lower() not in stopwords]
        return dict(
            short,
            location=dict(
                name=self.location,
                lat=self.lat,
                lng=self.lng,
                timezone=self.timezone,
            ),
            firstname=fn[0] if len(fn) else None,
        )


class Repo(db.Model):
    __tablename__ = "gh_repos"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    fullname = db.Column(db.Text)
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

    def short_dict(self):
        return dict(
            id=self.id,
            name=self.fullname,
        )

    def basic_dict(self):
        return dict(
            self.short_dict(),
            description=self.description,
            language=self.language,
            stars=self.star_count,
            watchers=self.watcher_count,
            forks=self.fork_count,
            issues=self.issues_count,
        )

db.Index("ix_gh_users_login_lower",
         db.func.lower(db.metadata.tables["gh_users"].c.login))
db.Index("ix_gh_repos_fullaname_lower",
         db.func.lower(db.metadata.tables["gh_repos"].c.fullname))
