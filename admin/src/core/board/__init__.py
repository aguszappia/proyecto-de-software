from src.core.database import db
from src.core.board.issue import Issue

def list_issues():
    return db.session.query(Issue).all()

def create_issue(kwargs):
    issue = Issue(kwargs)
    db.session.add(issue)
    db.session.commit()

    return issue