# test_db.py
from database.models import Session, Influencer, Base, engine

def test():
    try:
        # Check connection and create tables
        Base.metadata.create_all(engine)
        print("Successfully connected to PostgreSQL and created tables (if they didn't exist).")
        
        with Session() as session:
            count = session.query(Influencer).count()
            print(f"Current influencers in DB: {count}")
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    test()
