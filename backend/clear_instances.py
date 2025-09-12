import argparse
from app import create_app
from app.models import db, Instance


def main():
    parser = argparse.ArgumentParser(description='Clear instances from database')
    parser.add_argument('--user-id', dest='user_id', help='Only delete instances for this userId')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        q = db.session.query(Instance)
        if args.user_id:
            q = q.filter(Instance.user_id == args.user_id)
        deleted = q.delete(synchronize_session=False)
        db.session.commit()
        scope = f" for user_id={args.user_id}" if args.user_id else ""
        print(f"Deleted {deleted} instance(s){scope}.")


if __name__ == '__main__':
    main()