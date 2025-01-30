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

with open('config.json') as c:
    params = json.load(c)["database"]

with open('config.json') as c:
    data = json.load(c)['About']


localserver = True
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SECRET_KEY'] = 'thisisasecretkey'

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_USE_SSL=True,
    MAIL_PORT='465',
    MAIL_USERNAME=params['gmail_user'],
    MAIL_PASSWORD=params['gmail_password']
)

app.config['UPLOAD_FOLDER'] = params['upload_location']
mail = Mail(app)
if localserver:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
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
    password = db.Column(db.String(50), nullable=False)


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

# Homepage
@app.route('/')
def home():
    product = Products.query.all()
    return render_template('index.html', product=product[:5])

# Shop Page
@app.route('/shop')
def shop():
    products = Products.query.all()
    return render_template('shop.html', products=products)


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
    product = Products.query.filter_by(sno=id).first()
    return render_template('product.html', product=product)



@app.route('/about')
def about():
    return render_template('about.html', text=data['text'])


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
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image.filename)))
        image2.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image2.filename)))
        image3.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image3.filename)))
        entry = Products(productname=product_name, description=description, price=product_price, image=image.filename,
                         image2=image2.filename, image3=image3.filename)
        db.session.add(entry)
        db.session.commit()

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
        username = request.form.get('username')
        email = request.form.get('email')
        print(email)
        passw = request.form.get('pass')

        username1 = Register.query.filter_by(user=username).first()
        email1 = Register.query.filter_by(email=email).first()
        print(username1)
        print(email1)
        if(username1 or email1):
            flash('User Already Existed with this credentials')
        else:
            entry = Register(user=username, email=email, password=passw)
            db.session.add(entry)
            db.session.commit()

    return render_template('register.html')


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        user = Register.query.filter_by(user=username).first()
        print(user.password)
        if username == params['Admin'] and password == params['Pass']:
            session['admin'] = username
            flash('Hey! You are Successfully Logged in to Website as Admin', 'success')
            return redirect(url_for("home")) 
        
        
        if user and password == user.password:
            session['username'] = username
            flash('Youre Successfully Logged into our website', 'success')
            return redirect(url_for("home"))
        
        if user and password != user.password:
            flash('The Password you entered is not Correct please Try Again', 'success')
            # return redirect(url_for("login"))

        else:
            flash('Username and Password Does not Exist, Please Register your self first', 'success')
            return render_template('register.html')
    

    return render_template('login.html')



@app.route('/cart', defaults={'id': None}, methods=["GET", "POST"])
@app.route('/shop/<string:id>/cart', methods=["GET", "POST"])
def cart(id):
        if session.get('username'):
            user = session['username']
            print(session['username'])
            cartitems = Cart.query.filter_by(userid=user).all()
            if cartitems:
                product_ids = [item.productid for item in cartitems]
                product_detail = []
                for product_id in product_ids:
                    product_details = Products.query.filter_by(sno=product_id).first() 
                    if product_details:
                        product_detail.append(product_details)
                print(product_detail)
                return render_template('cart.html', cartitems=cartitems, product_detail=product_detail)
            else:
                flash('Your Cart is Empty', 'success')
                mark=True
                return render_template('cart.html', mark=mark)

        if session.get('admin'):
            flash('You need first login as Client', 'success')
            session.pop('admin', None)
            return redirect('/login')
        

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
        email = request.form.get('email')
        mess = request.form.get('text')
        entry = Contact_tb(email=email, message=mess, date=datetime.now())
        db.session.add(entry)
        db.session.commit()
        mail.send_message('New Message from ' + email,
                          sender=email,
                          recipients=[params['gmail_user']],
                          body=mess
                          )
    return render_template('contact.html')

@app.route('/cart/<int:id>')
def cart_product(id):
    product=Products.query.filter_by(sno=id).first()
    return render_template('product.html',product=product)


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



# @app.route('/checkout')
# def checkout():
#     if session.get('username'):
#      user=session['username']
#      return render_template('checkout.html', user=session['username'])
#     else:
#         flash('You first need to login', 'success')
#         return redirect('login')

if __name__ == '__main__':
    app.run(debug=True)
