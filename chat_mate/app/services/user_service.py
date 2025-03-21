from app.models.user import UserInDB

def get_all_users():
    # This would usually hit a database
    return [UserInDB(id=1, username="victor")]
