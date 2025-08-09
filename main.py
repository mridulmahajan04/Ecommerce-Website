from io import BytesIO
from flask import Flask, jsonify, render_template, request, send_file, session, url_for, g, redirect, flash
from flask_sqlalchemy import SQLAlchemy
import mysql.connector
from datetime import datetime
import json
from flask_mail import Mail
import os
from werkzeug.utils import secure_filename
from base64 import b64encode
from flask_session import Session
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import uuid

load_dotenv()
localserver = True
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SECRET_KEY'] = 'thisisasecretkey'

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_USE_SSL=True,
    MAIL_PORT='465',
    MAIL_USERNAME=os.getenv('GMAIL_USER'),
    MAIL_PASSWORD=os.getenv('GMAIL_PASSWORD')
)

app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_LOCATION')
mail = Mail(app)
if localserver:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('LOCAL_URI')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('LOCAL_URI')
db = SQLAlchemy(app)

# All Database
class Products(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    productname = db.Column(db.String(100), nullable=False)
    price = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(50), nullable=False)
    image2 = db.Column(db.String(50), nullable=False)
    image3 = db.Column(db.String(50), nullable=False)


class Register(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)


class Cart(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    productid = db.Column(db.String(50), nullable=False)
    userid = db.Column(db.String(50), nullable=False)


class Checkout(db.Model):
    orderid=db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    size = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.String(50), nullable=False)
    price=db.Column(db.String(50), nullable=False)

class Coupan(db.Model):
    sno=db.Column(db.Integer, primary_key=True)
    coupancode = db.Column(db.String(50), nullable=False)
    discount = db.Column(db.Integer, nullable=False)

# Test route
@app.route('/test')
def test():
    return "Application is working!"

# Homepage
@app.route('/')
def home():
    product = Products.query.all()
    return render_template('index.html', product=product[:5])

# Quicksort algorithm for sorting products

def quicksort_products(products, key, reverse=False):
    if len(products) <= 1:
        return products
    pivot = key(products[0])
    less = [p for p in products[1:] if key(p) < pivot]
    equal = [p for p in products if key(p) == pivot]
    greater = [p for p in products[1:] if key(p) > pivot]
    sorted_list = quicksort_products(less, key) + equal + quicksort_products(greater, key)
    return sorted_list[::-1] if reverse else sorted_list

# Shop Page
@app.route('/shop')
def shop():
    sort_by = request.args.get('sort', 'default')
    products = Products.query.all()
    # Use quicksort to sort products based on user selection
    if sort_by == 'price_asc':
        products = quicksort_products(products, key=lambda p: int(p.price))
    elif sort_by == 'price_desc':
        products = quicksort_products(products, key=lambda p: int(p.price), reverse=True)
    elif sort_by == 'name_asc':
        products = quicksort_products(products, key=lambda p: p.productname.lower())
    elif sort_by == 'name_desc':
        products = quicksort_products(products, key=lambda p: p.productname.lower(), reverse=True)
    # else: default order from DB
    return render_template('shop.html', products=products)

# Global dictionary to cache product details by their ID (sno)
product_cache = {}

# Helper function to get product by ID with caching
def get_product_by_id(product_id):
    """
    Returns the product with the given product_id (sno).
    Checks the cache first; if not found, fetches from the database and stores in cache.
    """
    # Check if product is already in cache
    if product_id in product_cache:
        # Return cached product
        return product_cache[product_id]
    # Fetch from database if not in cache
    product = Products.query.filter_by(sno=product_id).first()
    # Store in cache for future requests
    product_cache[product_id] = product
    return product

@app.route('/shop/<string:id>', methods=["GET", "POST"])
def shop_product(id):
    if request.method == 'POST':
        if session.get('username'):
            if request.form['action'] == "Add To cart":
                productid=id
                userid=session['username'] 
                print(id)
                check = Cart.query.filter_by(productid=productid,userid=userid).first()
                print(check)
                if check:
                    flash('Already  exist in Cart', 'success')
                    
                else:
                    cart = Cart(productid=productid, userid=userid)
                    db.session.add(cart)
                    db.session.commit()
                    print('Printing Data')   
                    print(userid)
                    print(productid)
                    flash('Your Product is succesfully added to cart', 'success')
            else:
                user=session['username']
                size=request.form.get('size')
                print(size)
                color=request.form.get('color')
                quantity=request.form.get('quantity')
                productprice = Products.query.filter_by(sno=id).first()
                price = int(productprice.price) * int(quantity)
                entry = Checkout(username=user, size=size, color=color, quantity=quantity, price=price)
                db.session.add(entry)
                db.session.commit()
                buy = Checkout.query.filter_by(username=user).first()
                coupan = Coupan.query.all()
                return render_template('checkout.html',productprice=productprice, quantity=int(quantity), user=user,coupan=coupan)

        else:
            flash('First login Then You can add to cart/Buy this product')
            return redirect(url_for('login'))
    product = get_product_by_id(id)  # Use cache-aware function
    return render_template('product.html', product=product)



@app.route('/about')
def about():
    return render_template('about.html', text="I want about my website")


# Admin Pannel
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin'):
        return redirect('login')
    else:
        checkout_data = Checkout.query.all()
        register_data = Register.query.all()
        products_data = Products.query.all()
        for i in checkout_data :
            print(i.price)
        count = 0
        for i in register_data:
            count= count + 1
        
        # Ensure prices are converted to float for calculation
        user_purchase = Checkout.query.with_entities(Checkout.username, func.sum(Checkout.price).label('Total_purchase'),func.sum(Checkout.quantity).label('total_quantity')).group_by(Checkout.username).all()
        total_revenue = sum([float(data.price) for data in checkout_data])
        print('checkout')
        sum_value = 0
        for i in user_purchase:
            sum_value = sum_value + i.Total_purchase
            print(i.Total_purchase)
        print(sum_value)
        average_revenue = sum_value / count
        print(f'The Average Purchase of Customers are {average_revenue}')
        return render_template('dashboard-Admin.html', total_revenue=total_revenue, register_data=count, average_revenue=average_revenue, products_data= products_data)



@app.route('/addproduct', methods=['GET', 'POST'])
def addproduct():
    if not session.get('admin'):
        return redirect('login')
    
    if request.method == "POST":
        product_name = request.form.get('productName')
        product_price = request.form.get('productPrice')
        description = request.form.get('productDescription')
        image = request.files['product_image1']
        image2 = request.files['product_image2']
        image3 = request.files['product_image3']
        
        # Input validation
        if not product_name or len(product_name) < 2:
            flash('Product name must be at least 2 characters long.', 'danger')
            return redirect(request.url)
        
        if not validate_price(product_price):
            flash('Please enter a valid price.', 'danger')
            return redirect(request.url)
        
        if not description or len(description) < 10:
            flash('Description must be at least 10 characters long.', 'danger')
            return redirect(request.url)
        
        # File validation
        if not all([image.filename, image2.filename, image3.filename]):
            flash('Please select all three images.', 'danger')
            return redirect(request.url)
        
        if not all(allowed_file(f.filename) for f in [image, image2, image3]):
            flash('Only image files (png, jpg, jpeg, gif) are allowed!', 'danger')
            return redirect(request.url)
        
        # Secure filenames with unique identifiers
        filename1 = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
        filename2 = f"{uuid.uuid4().hex}_{secure_filename(image2.filename)}"
        filename3 = f"{uuid.uuid4().hex}_{secure_filename(image3.filename)}"
        
        # Ensure upload folder exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Save images with error handling
        try:
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename1))
            image2.save(os.path.join(app.config['UPLOAD_FOLDER'], filename2))
            image3.save(os.path.join(app.config['UPLOAD_FOLDER'], filename3))
        except Exception as e:
            flash('Failed to save images. Please try again.', 'danger')
            print(f"Image save error: {e}")
            return redirect(request.url)
        
        # Create product entry with database error handling
        entry = Products(productname=product_name, description=description, price=product_price, image=filename1,
                         image2=filename2, image3=filename3)
        
        try:
            db.session.add(entry)
            db.session.commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('admin'))
        except Exception as e:
            db.session.rollback()
            flash('Failed to add product. Please try again.', 'danger')
            print(f"Product add error: {e}")
            return redirect(request.url)

    return render_template('AddProduct.html')


@app.route('/admin/delete/<int:id>', methods=['GET', 'POST'])
def delete(id):
    if not session.get('admin'):
        return render_template('login.html')
    else:
        item = Products.query.get(id)
        print(item)
        if not item:
            flash('Item is not in database')
            return redirect('/admin')
        else:
            db.session.delete(item)
            db.session.commit()
            return redirect('/admin')





@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        passw = request.form.get('pass', '').strip()

        # Input validation with specific error messages
        if not username:
            flash('Username is required.', 'danger')
            return render_template('register.html')
        
        if not validate_username(username):
            flash('Username must be 3-50 characters long and contain only letters, numbers, underscores, and hyphens.', 'danger')
            return render_template('register.html')
        
        if not email:
            flash('Email is required.', 'danger')
            return render_template('register.html')
        
        if not validate_email(email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('register.html')
        
        if not passw:
            flash('Password is required.', 'danger')
            return render_template('register.html')
        
        if len(passw) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html')

        # Check for existing users
        try:
            username1 = Register.query.filter_by(user=username).first()
            email1 = Register.query.filter_by(email=email).first()
            
            if username1:
                flash('Username already exists. Please choose a different username.', 'danger')
                return render_template('register.html')
            
            if email1:
                flash('Email already registered. Please use a different email or login.', 'danger')
                return render_template('register.html')
            
            # Hash the password before storing it
            hashed_pw = generate_password_hash(passw)
            entry = Register(user=username, email=email, password=hashed_pw)
            
            # Database error handling
            try:
                db.session.add(entry)
                db.session.commit()
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash('Registration failed. Please try again.', 'danger')
                print(f"Registration error: {e}")
                return render_template('register.html')
                
        except Exception as e:
            flash('Database connection error. Please try again.', 'danger')
            print(f"Database error: {e}")
            return render_template('register.html')

    return render_template('register.html')


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        print(f"Login attempt - Username: '{username}'")

        # Input validation
        if not username:
            flash('Username is required.', 'danger')
            return render_template('login.html')
        
        if not password:
            flash('Password is required.', 'danger')
            return render_template('login.html')

        try:
            user = Register.query.filter_by(user=username).first()
            
            # Use environment variables for admin credentials
            ADMIN_USER = os.getenv('ADMIN_USER')
            ADMIN_PASS = os.getenv('ADMIN_PASS')
            
            # Check admin login first
            if username == ADMIN_USER and password == ADMIN_PASS:
                session['admin'] = username
                flash('Successfully logged in as Admin!', 'success')
                return redirect(url_for("home")) 
            
            # Check regular user login
            if user and check_password_hash(user.password, password):
                session['username'] = username
                flash('Successfully logged in!', 'success')
                return redirect(url_for("home"))
            
            # Handle login failures
            if user:
                flash('Incorrect password. Please try again.', 'danger')
            else:
                flash('Username not found. Please register first.', 'danger')
                return render_template('register.html')
                
        except Exception as e:
            flash('Login error. Please try again.', 'danger')
            print(f"Login error: {e}")
            return render_template('login.html')

    return render_template('login.html')
 

@app.route('/cart', defaults={'id': None}, methods=["GET", "POST"])
@app.route('/shop/<string:id>/cart', methods=["GET", "POST"])
def cart(id):
    if session.get('username'):
        user = session['username']
        print(session['username'])
        # Query cart items based on user
        cartitems = Cart.query.filter_by(userid=user).all()
        if cartitems:
            # Get all product IDs in the cart
            product_ids = [item.productid for item in cartitems]
            # Fetch all products in one query to avoid N+1 problem
            products = Products.query.filter(Products.sno.in_(product_ids)).all()
            # Build a mapping from product id to product
            product_map = {str(product.sno): product for product in products}
            # Match products to cart order
            product_detail = [product_map.get(str(pid)) for pid in product_ids if str(pid) in product_map]
            print(product_detail)
            # Return the cart page with cart details
            return render_template('cart.html', cartitems=cartitems, product_detail=product_detail)
        else:
            # If cart is empty, flash a message and return cart page
            flash('Your Cart is Empty', 'success')
            mark = True  # Use 'mark' to indicate cart is empty
            return render_template('cart.html', mark=mark)
    
    elif session.get('admin'):
        # If admin is logged in, ask them to log in as a client first
        flash('You need first login as Client', 'success')
        session.pop('admin', None)
        return redirect('/login')
    
    else:
        # If no user or admin session is found, redirect to login page
        return render_template('login.html')



@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('admin', None)
    flash("You are succefull logout from our Website", 'success')
    return redirect(url_for('home'))


@app.route('/product')
def product():
    return render_template('product.html')


class Contact_tb(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(12), nullable=True)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == "POST":
        email = request.form.get('email', '').strip()
        mess = request.form.get('text', '').strip()
        
        print(f"Contact form submission - Email: '{email}'")
        
        # Input validation
        if not email:
            flash('Email is required.', 'danger')
            return render_template('contact.html')
        
        if not validate_email(email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('contact.html')
        
        if not mess:
            flash('Message is required.', 'danger')
            return render_template('contact.html')
        
        if len(mess) < 10:
            flash('Message must be at least 10 characters long.', 'danger')
            return render_template('contact.html')
        
        if len(mess) > 1000:  # Reasonable limit
            flash('Message is too long. Please keep it under 1000 characters.', 'danger')
            return render_template('contact.html')
        
        try:
            entry = Contact_tb(email=email, message=mess, date=datetime.now())
            db.session.add(entry)
            db.session.commit()
            
            # Email error handling
            try:
                mail.send_message('New Message from ' + email,
                                  sender=email,
                                  recipients=[os.getenv('GMAIL_USER')],
                                  body=mess
                                  )
                flash('Message sent successfully!', 'success')
            except Exception as e:
                flash('Message saved but email delivery failed. We will contact you soon.', 'warning')
                print(f"Email error: {e}")
                
        except Exception as e:
            db.session.rollback()
            flash('Failed to send message. Please try again.', 'danger')
            print(f"Contact error: {e}")
            
    return render_template('contact.html')

@app.route('/cart/<int:id>')
def cart_product(id):
    product = get_product_by_id(id)  # Use cache-aware function
    return render_template('product.html', product=product)


@app.route('/validate_coupon', methods=['POST'])
def validate_coupon():
    data = request.get_json()
    coupon_code = data.get('coupon_code', '')
    coupon = Coupan.query.filter_by(coupancode=coupon_code).first()
    
    if coupon:
        # return jsonify({'success': f'Coupon is valid. Discount: {coupon.discount}%.'})
        return jsonify({'success': 'Coupon is valid.', 'discount': coupon.discount})
    else:
        return jsonify({'error': 'Invalid coupon code.'})


# Validation functions
def validate_username(username):
    """Validate username: 3-50 characters, alphanumeric only"""
    if not username or not isinstance(username, str):
        return False
    username = username.strip()
    if len(username) < 3 or len(username) > 50:
        return False
    # Allow alphanumeric characters, underscores, and hyphens
    import re
    return re.match(r'^[a-zA-Z0-9_-]+$', username) is not None

def validate_email(email):
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False
    email = email.strip()
    if len(email) > 254:  # RFC 5321 limit
        return False
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_price(price):
    """Validate price: must be a positive number"""
    if not price:
        return False
    try:
        price_float = float(price)
        return price_float > 0 and price_float < 1000000  # Reasonable upper limit
    except (ValueError, TypeError):
        return False

def allowed_file(filename):
    """Check if file extension is allowed"""
    if not filename or not isinstance(filename, str):
        return False
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Global error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)
