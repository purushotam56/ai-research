import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    documents = db.relationship('Document', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }


class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True, index=True)  # NULL for main URL, set for related URLs
    title = db.Column(db.String(255), nullable=False)
    source_type = db.Column(db.String(20), nullable=False)  # 'url' or 'file'
    source_url = db.Column(db.String(500), nullable=True)
    filename = db.Column(db.String(255), nullable=True)
    content = db.Column(db.Text, nullable=False)
    content_summary = db.Column(db.Text, nullable=True)
    url_grouped_content = db.Column(db.Text, nullable=True)  # JSON: {url: {title, content}, ...}
    vector_ids = db.Column(db.String(500), nullable=True)  # comma-separated ChromaDB IDs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship for parent-child hierarchy
    children = db.relationship('Document', remote_side=[id], backref='parent', cascade='all, delete-orphan', single_parent=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'source_type': self.source_type,
            'source_url': self.source_url,
            'filename': self.filename,
            'content': self.content,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat(),
            'has_vectors': bool(self.vector_ids)
        }
