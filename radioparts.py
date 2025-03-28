from app import create_app

app = create_app()

# The following creates the database from models.
#from app import db
# with app.app_context():
#     db.drop_all()
#     db.create_all()
#     print("Database created with proper table references!")

    
if __name__ == '__main__':
    app.run(debug=True)
