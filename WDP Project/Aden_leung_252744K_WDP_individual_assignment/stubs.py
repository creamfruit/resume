from models import AdenUsers, RyanUsers


def demo_model_usage(row: dict) -> dict:
    user = AdenUsers.from_row(row)
    if user is None:
        return {}
    return user.to_dict()


def combine_users(aden: AdenUsers, ryan: RyanUsers) -> dict:
    return {
        'aden_user': aden.to_dict(),
        'ryan_user': ryan.to_dict(),
    }
