# -*- coding: utf-8 -*-

from flask_sqlalchemy import SQLAlchemy

from .utils import load_json_resource

__all__ = ["db", "User", "Repo"]


db = SQLAlchemy()

STOPWORDS = ["the", "dr", "mr", "mrs"]


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

    @property
    def is_active(self):
        if not self.active:
            return False
        names = load_json_resource("optout.json")
        return not (self.login.lower() in names)

    @property
    def render_name(self):
        return self.name if self.name is not None else self.login

    @property
    def firstname(self):
        fn = [t for t in self.render_name.split()
              if t.lower() not in STOPWORDS]
        return fn[0] if len(fn) else None

    def short_dict(self):
        return dict(
            id=self.id,
            login=self.login,
            type=self.user_type,
            name=self.render_name,
            avatar_url=self.avatar_url,
        )

    def basic_dict(self, ):
        short = self.short_dict()
        return dict(
            short,
            location=dict(
                name=self.location,
                lat=self.lat,
                lng=self.lng,
                timezone=self.timezone,
            ),
            firstname=self.firstname,
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
            username=self.fullname.split("/")[0],
            reponame="/".join(self.fullname.split("/")[1:]),
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
