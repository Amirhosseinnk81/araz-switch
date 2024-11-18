from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin , LoginManager
from datetime import datetime
import pytz
import jdatetime

db = SQLAlchemy()


# راه‌اندازی اپلیکیشن Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # برای امنیت جلسات
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# راه‌اندازی SQLAlchemy و Flask-Login
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # صفحه لاگین برای ورود کاربران


# مدل دیتابیس برای یوزرها
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# مدل دیتابیس برای توضیحات
class Description(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)  # محتوای توضیحات
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    Date = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Tehran')), nullable=False)
    
    # ارتباط با Device و User
    device = db.relationship('Device', backref=db.backref('descriptions', lazy=True, cascade="all, delete"))
    user = db.relationship('User', backref=db.backref('descriptions', lazy=True))

# مدل دیتابیس برای floors
class Floor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', backref=db.backref('floors', lazy=True))

# مدل دیتابیس برای devices
class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    ip = db.Column(db.String(50), nullable=False)
    vlan = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    floor_id = db.Column(db.Integer, db.ForeignKey('floor.id'), nullable=False)

    floor = db.relationship('Floor', backref=db.backref('devices', lazy=True))

with app.app_context():
    db.create_all()
    if not User.query.first():
        users = [
            User(username='superuser', password='1234'),
            User(username='admin', password='4321'),      
            User(username='user', password='user')
        ]
        db.session.bulk_save_objects(users)
        db.session.commit()


# تبدیل تاریخ میلادی به شمسی
@app.template_filter('to_jalali')
def to_jalali(datetime_obj):
    if datetime_obj is None:
        return "تاریخ نامعتبر"
    
    # تبدیل تاریخ میلادی به شمسی
    jalali_date = jdatetime.date.fromgregorian(
        day=datetime_obj.day, 
        month=datetime_obj.month, 
        year=datetime_obj.year
    )
    
    # تبدیل زمان میلادی به شمسی
    jalali_time = datetime_obj.strftime('%H:%M')  # ساعت و دقیقه میلادی
    
    # نمایش تاریخ و زمان شمسی به صورت 'YYYY/MM/DD HH:MM'
    return f"{jalali_date.strftime('%Y/%m/%d')} {jalali_time}"

