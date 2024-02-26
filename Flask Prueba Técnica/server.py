from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///usuarios.db'
app.config['SECRET_KEY'] = 'mysecretkey'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Modelo de Usuario
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    date_hired = db.Column(db.DateTime, nullable=False) 

class WishlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    added_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('wishlist_items', lazy=True))


# Configuración de Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Rutas
@app.route("/")
def home():
    if current_user.is_authenticated:
        users = User.query.filter(User.id != current_user.id).all()
        current_user_wishlist = current_user.wishlist_items
        other_users_wishlist = WishlistItem.query.filter(WishlistItem.added_by != current_user.id).all()
        return render_template("home.html", users=users, current_user_wishlist=current_user_wishlist, other_users_wishlist=other_users_wishlist)
    return redirect(url_for('login'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        
        username = request.form.get('username')
        name = request.form.get('name')
        password = request.form.get('password')
        date_hired = request.form.get('date_hired')
        today = datetime.now().date()

        # Validaciones
        error = None
        if len(password) < 8:
            error = 'La contraseña debe tener más de 8 caracteres.'
        elif len(username) < 4:
            error = 'El nombre de usuario debe tener más de 3 caracteres.'
        elif datetime.strptime(date_hired, '%Y-%m-%d').date() != today:
            error = 'La fecha de contratación debe ser hoy.'

        if error is not None:
            flash(error)
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(
                        name=name,
                        username=username,
                        password=hashed_password,
                        date_hired=datetime.strptime(date_hired, '%Y-%m-%d')
                        )
        
        db.session.add(new_user)
        db.session.commit()
        session['registration_success'] = True
        flash('¡Registro exitoso! Por favor, inicia sesión.')
        return redirect(url_for('login'))

    return render_template("home.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', None)
        password = request.form.get('password', None)
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('¡Inicio de sesión exitoso!')
            return redirect(url_for('home'))

        flash('Nombre de usuario o contraseña incorrectos. Por favor, inténtalo de nuevo.')

    return render_template("inicio.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/add_item", methods=['POST', 'GET'])
@login_required
def add_item():
    if request.method == 'POST':
        item_name = request.form.get('item_name')
        if item_name:
            new_item = WishlistItem(name=item_name, added_by=current_user.id)
            db.session.add(new_item)
            db.session.commit()
            flash('Ítem agregado exitosamente.')
            return redirect(url_for('home'))
        else:
            flash('El nombre del ítem no puede estar vacío.')
    return render_template("add_item.html")


@app.route("/add_wishlist_item/<int:item_id>")
@login_required
def add_wishlist_item(item_id):
    existing_item = WishlistItem.query.get(item_id)
    
    if existing_item:
        if current_user.id == existing_item.added_by:
            flash('This item is already in your wishlist.', 'info')
        else:
            new_item = WishlistItem(name=existing_item.name, added_by=current_user.id)
            db.session.add(new_item)
            db.session.commit()
            flash('Item added to your wishlist successfully.', 'success')
    else:
        flash('Item does not exist.', 'danger')

    return redirect(url_for('home'))

@app.route("/item_details/<int:item_id>")
@login_required
def item_details(item_id):
    item = WishlistItem.query.get(item_id)
    current_user_wishlist = current_user.wishlist_items
    return render_template("item_details.html", item=item)

    
@app.route("/remove_wishlist_item/<int:item_id>")
@login_required
def remove_wishlist_item(item_id):
    item = WishlistItem.query.get_or_404(item_id)
    if item.added_by == current_user.id:
        # El current_user es el creador del item, procede a eliminarlo.
        db.session.delete(item)
        db.session.commit()
        flash('Item removed successfully.', 'success')
    else:
        # El item no fue añadido por el current_user, no se permite la eliminación.
        flash('You do not have permission to delete this item.', 'danger')
    return redirect(url_for('home'))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)