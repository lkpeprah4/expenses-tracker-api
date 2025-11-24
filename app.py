from flask import Flask, jsonify, request
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from models import db, User, Category ,Expense
from datetime import datetime



app = Flask(__name__)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

app.config['JWT_SECRET_KEY'] = "87654Q34567890987654323456789REDFBVGFDX"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return jsonify({"msg": "Hello, your database is ready!"})


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"msg": "ALL FIELDS ARE REQUIRED FROM THE USER"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, email=email, password=hashed_password)

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "EMAIL ALREADY REGISTERED"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "USERNAME ALREADY TAKEN"}), 400

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "User created successfully"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"msg": "ALL FIELDS ARE REQUIRED "}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"msg": "USER NOT FOUND,INVALID EMAIL"}), 401
    if not bcrypt.check_password_hash(user.password, password):
        return jsonify({"msg": "WRONG PASSWORD"}), 401

    access_token = create_access_token(identity=str(user.id))

    return jsonify({"msg": "LOGIN SUCCESSFUL", "access_token": access_token}), 200


@app.route("/protect", methods=["GET"])
@jwt_required()
def protect():
    user_id = get_jwt_identity()
    return jsonify({"msg": f"Hello user {user_id}, you are logged in!"}), 200


@app.route("/category", methods=["POST"])
@jwt_required()
def create_category():
    data = request.get_json()
    name = data.get("name")

    if not name:
        return jsonify({"msg": "Category field is required"}),400

    user_id = get_jwt_identity()

    if Category.query.filter_by(name=name, user_id=user_id).first():
        return jsonify({"msg": "Category already exists"}), 400

    new_category = Category(name=name, user_id=user_id)
    db.session.add(new_category)
    db.session.commit()

    return jsonify({"msg": "Category added successfully", "category": {"id": new_category.id, "name": new_category.name}}), 201

@app.route("/category", methods=["GET"])
@jwt_required()
def get_categories():
    user_id = get_jwt_identity()

    categories = Category.query.filter_by(user_id = user_id).all()

    results = [
        {
            "id": category.id,
            "name": category.name
        } for category in categories
    ]

    return jsonify({"categories": results}), 200

@app.route('/category/<int:id>', methods=['PUT'])
def update_category(id):
    
    category = Category.query.get(id)
    if not category:
        return jsonify({"message": "Category not found"}), 404

    
    data = request.get_json()
    new_name = data.get("name")

    if not new_name:
        return jsonify({"message": "Name is required"}), 400
    
    #WHAT IF THERES NAME EXISTS ALREADY
    check_if_same=Category.query.filter_by(Category.name==new_name).first()

    if check_if_same:
        return jsonify({"msg":"Category name already exists"}),400
    
    category.name = new_name
    db.session.commit()

    return jsonify({"message": "Category updated successfully", "category": {"id": category.id, "name": category.name}})

@app.route('/category/<int:id>', methods=['DELETE'])
def delete_category(id):
    category = Category.query.get(id)
    if not category:
        return jsonify({"message": "Category not found"}), 404
    
    db.session.delete(category)
    db.session.commit()

    return jsonify({"message": "Category deleted successfully"})

def serialize_expense(expense):
    return {
        "id": expense.id,
        "amount": expense.amount,
        "notes": expense.notes,
        "date": str(expense.date),
        "category_id": expense.category_id
    }

@app.route("/expenses",methods=["POST"])
@jwt_required()
def addexpense():
    data=request.get_json()

    amount=data.get("amount")
    notes=data.get("notes")
    date=data.get("date")
    category_id=data.get("category_id")

    if not amount or not notes or not date or not category_id :
        return jsonify({"msg":"All fields are required"}),400
    
    try:
        category_id = int(category_id)
    except:
        return jsonify({"msg": "category_id must be a number"}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"msg": "Amount must be greater than 0"}), 400
    except:
        return jsonify({"msg": "Amount must be a valid number"}), 400
    
    user_id=get_jwt_identity()

    from datetime import datetime
    try:
        date = datetime.strptime(date, "%Y-%m-%d").date()
    except:
        return jsonify({"msg": "Date must be in format YYYY-MM-DD"}), 400
    
    category=Category.query.filter_by(id=category_id,user_id=user_id).first()
    if not category:
        return jsonify({"msg":"Category not found"}),404
    
    new_expense = Expense(
        amount=amount,
        notes=notes,
        date=date,
        user_id=user_id,
        category_id=category_id
    )
    
    db.session.add(new_expense)
    db.session.commit()

    return jsonify ({
        "msg": "Expense added successfully",
        "expense" :serialize_expense(new_expense)
        }
          ), 201

@app.route("/expenses" ,methods=["GET"] )
@jwt_required()
def get_expenses():
    user_id=get_jwt_identity()

    category_id = request.args.get("category_id", type=int)
    min_amount = request.args.get("min_amount", type=float)
    max_amount = request.args.get("max_amount", type=float)
    start_date = request.args.get("start_date")  
    end_date = request.args.get("end_date")      
    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("limit", default=10, type=int)

    query = Expense.query.filter_by(user_id=user_id)

    if category_id:
        query = query.filter_by(category_id=category_id)
    if min_amount is not None:
        query = query.filter(Expense.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Expense.amount <= max_amount)
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Expense.date >= start_date_obj)
        except:
            return jsonify({"msg": "start_date must be YYYY-MM-DD"}), 400
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Expense.date <= end_date_obj)
        except:
            return jsonify({"msg": "end_date must be YYYY-MM-DD"}), 400
        
    total_expenses = query.count()
    expenses = query.order_by(Expense.date.desc()).offset((page - 1) * limit).limit(limit).all()
    total_pages = (total_expenses + limit - 1) // limit

    results = [serialize_expense(expense) for expense in expenses]

    return jsonify({
        "expenses": results,
        "pagination": {
            "current_page": page,
            "limit": limit,
            "total_pages": total_pages,
            "total_expenses": total_expenses
        }
    }), 200

@app.route("/expenses/<int:expense_id>", methods=["PUT"])
@jwt_required()
def update_expense(expense_id):
    user_id = get_jwt_identity()
    expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
    
    if not expense:
        return jsonify({"msg": "Expense not found"}), 404

    data = request.get_json()
    amount = data.get("amount")
    notes = data.get("notes")
    date = data.get("date")
    category_id = data.get("category_id")

    
    if amount is not None:
        try:
            amount = float(amount)
            if amount <= 0:
                return jsonify({"msg": "Amount must be greater than 0"}), 400
            expense.amount = amount
        except:
            return jsonify({"msg": "Amount must be a valid number"}), 400

    if notes is not None:
        expense.notes = notes

    if date is not None:
        from datetime import datetime
        try:
            expense.date = datetime.strptime(date, "%Y-%m-%d").date()
        except:
            return jsonify({"msg": "Date must be in format YYYY-MM-DD"}), 400

    if category_id is not None:
        try:
            category_id = int(category_id)
            category = Category.query.filter_by(id=category_id, user_id=user_id).first()
            if not category:
                return jsonify({"msg": "Category not found"}), 404
            expense.category_id = category_id
        except:
            return jsonify({"msg": "category_id must be a number"}), 400

    db.session.commit()
    return jsonify({"msg": "Expense updated successfully", "expense": serialize_expense(expense)}), 200

@app.route("/expenses/<int:expense_id>", methods=["DELETE"])
@jwt_required()
def delete_expense(expense_id):
    user_id = get_jwt_identity()
    expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
    
    if not expense:
        return jsonify({"msg": "Expense not found"}), 404

    db.session.delete(expense)
    db.session.commit()
    return jsonify({"msg": "Expense deleted successfully"}), 200



if __name__ == "__main__":
    app.run(debug=True)

