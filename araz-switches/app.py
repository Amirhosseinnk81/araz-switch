from flask import Flask, render_template,session, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import pytz
import jdatetime
from functools import wraps

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

def get_description_for_device(device_id):
    return Description.query.filter_by(device_id=device_id).order_by(Description.Date.desc()).all()

#گرفتن دستگاه ها خاص توسط id 
def get_device_by_id(id):    
    return  Device.query.get_or_404(id)



# ایجاد جدول‌ها در دیتابیس
with app.app_context():
    db.create_all()

    if not User.query.first():
        users = [
            User(username='superuser', password='password1'),
            User(username='admin', password='password2'),
            User(username='user3', password='password3'),
            User(username='user4', password='password4')
        ]
        db.session.bulk_save_objects(users)
        db.session.commit()

@app.route("/")
def home():
    return render_template("login.html")

# تنظیمات لاگین
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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


#ویرایش تو ضیحات


@app.route('/edit_description/<int:description_id>', methods=['GET', 'POST'])
@login_required
def edit_description(description_id):
    # دریافت توضیحات از پایگاه داده
    description = Description.query.get_or_404(description_id)

    # دریافت دستگاه مرتبط با توضیحات
    device = Device.query.get(description.device_id)

    # دیگر نیازی به بررسی مالکیت نیست
    # بررسی دسترسی کاربر به ویرایش توضیحات (این شرط حذف می‌شود)
    # if description.user_id != current_user.id and current_user.username not in ['user1', 'user2']:
    #     flash('شما دسترسی به ویرایش این توضیحات را ندارید.', 'danger')
    #     return redirect(url_for('view_device', device_id=description.device_id))

    # اگر درخواست POST بود، تغییرات را ذخیره می‌کنیم
    if request.method == 'POST':
        # دریافت محتوای جدید توضیحات از فرم
        description.content = request.form['content']

        # به روز رسانی تاریخ و زمان ویرایش
        description.Date = datetime.now(pytz.timezone('Asia/Tehran'))

        # ذخیره تغییرات در پایگاه داده
        db.session.commit()

        # نمایش پیام موفقیت
        flash('توضیحات با موفقیت ویرایش شد.', 'success')

        # هدایت به صفحه جزئیات دستگاه
        return redirect(url_for('device_details', device_id=description.device_id))

    # اگر درخواست GET بود، فرم ویرایش را نمایش می‌دهیم
    return render_template('edit_description.html', description=description, device=device)


# صفحه لاگین
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            login_user(user)
            next_url = session.pop('next_url', None)
            return redirect(next_url or url_for('dashboard'))  # به صفحه‌ی مورد نظر یا داشبورد هدایت می‌شود
        else:
            flash('نام کاربری یا رمز عبور اشتباه است', 'danger')
    
    return render_template('login.html')

def require_login_and_redirect(f):
    """دکوراتوری که کاربر را به صفحه ورود هدایت می‌کند و پس از لاگین به صفحه قبلی بازمی‌گرداند."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:  # بررسی وضعیت لاگین
            # ذخیره URL فعلی در سشن برای هدایت بعد از لاگین
            session['next_url'] = request.url
            flash('لطفاً برای ادامه لاگین کنید.', 'warning')
            return redirect(url_for('login'))  # هدایت به صفحه لاگین
        return f(*args, **kwargs)
    return decorated_function


# صفحه داشبورد پس از ورود
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# صفحه اضافه کردن floor
@app.route('/add_floor', methods=['GET', 'POST'])
@login_required
def add_floor():
    if request.method == 'POST':
        floor_name = request.form['floor_name']
        new_floor = Floor(name=floor_name, user_id=current_user.id)
        db.session.add(new_floor)
        db.session.commit()
        return redirect(url_for('view_floors'))

    return render_template('add_floor.html')

# نمایش لیست floor ها
@app.route('/view_floors')
@login_required
def view_floors():
    floors = Floor.query.all()
    return render_template('view_floors.html', floors=floors)

# صفحه افزودن دستگاه
@app.route('/add_device/<int:floor_id>', methods=['GET', 'POST'])
@login_required
def add_device(floor_id):
    floor = Floor.query.get_or_404(floor_id)
    
    if request.method == 'POST':
        device_name = request.form['device_name']
        device_ip = request.form['device_ip']
        device_vlan = request.form['device_vlan']
        device_description = request.form['device_description']
        
        new_device = Device(
            name=device_name,
            ip=device_ip,
            vlan=device_vlan,
            description=device_description,
            floor_id=floor.id
        )
        
        db.session.add(new_device)
        db.session.commit()
        return redirect(url_for('view_devices', floor_id=floor.id))

    return render_template('add_device.html', floor=floor)

# نمایش  همه دستگاه‌های یک طبقه
@app.route('/view_devices/<int:floor_id>')
@login_required
def view_devices(floor_id):
    floor = Floor.query.get_or_404(floor_id)
    devices = Device.query.filter_by(floor_id=floor.id).all()
    return render_template('view_devices.html', floor=floor, devices=devices)



#نمایش دستگاه مد نظر
@app.route('/device/<int:device_id>', methods=['GET'])
@require_login_and_redirect
def device_details(device_id):
    
    device = get_device_by_id(device_id) 
    description = get_description_for_device(device_id)  
    return render_template('device_details.html', device=device, description=description)

# صفحه ویرایش دستگاه
@app.route('/edit_device/<int:device_id>', methods=['GET', 'POST'])
@login_required
def edit_device(device_id):
    device = Device.query.get_or_404(device_id)
    
    if request.method == 'POST':
        device.name = request.form['device_name']
        device.ip = request.form['device_ip']
        device.vlan = request.form['device_vlan']
        device.description = request.form['device_description']
        db.session.commit()
        return redirect(url_for('view_devices', floor_id=device.floor_id))

    return render_template('edit_device.html', device=device)


# روت برای افزودن کاربر جدید
@app.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():   
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('این نام کاربری وجود دارد', 'danger')
        else:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash('کاربر با موفقیت اضافه شد', 'success')
            return redirect(url_for('dashboard'))

    return render_template('add_user.html')


@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        new_username = request.form['username']
        new_password = request.form['password']

        # بررسی اینکه آیا نام کاربری جدید تکراری است
        existing_user = User.query.filter_by(username=new_username).first()
        if existing_user and existing_user.id != user.id:
            flash('این نام کاربری قبلاً استفاده شده است.', 'danger')
            return redirect(url_for('edit_user', user_id=user.id))

        # بروزرسانی اطلاعات کاربر
        user.username = new_username
        user.password = new_password
        db.session.commit()

        flash('اطلاعات کاربری با موفقیت به روز شد.', 'success')
        return redirect(url_for('show_users'))  # هدایت به صفحه لیست کاربران

    return render_template('edit_user.html', user=user)


# روت برای نمایش لیست کاربران
@app.route('/show_users')
@login_required
def show_users():


    users = User.query.all()  # دریافت لیست تمام کاربران
    return render_template('show_users.html', users=users)


# صفحه افزودن توضیحات به دستگاه
@app.route('/add_description/<int:device_id>', methods=['GET', 'POST'])
@login_required
def add_description(device_id):
    device = Device.query.get_or_404(device_id)
    
    if request.method == 'POST':
        description_content = request.form['description']
        
        # ایجاد یک توضیح جدید
        new_description = Description(content=description_content, device_id=device.id, user_id=current_user.id)
        db.session.add(new_description)
        db.session.commit()
        
        flash('توضیحات با موفقیت اضافه شد!', 'success')
        return redirect(url_for('view_devices', floor_id=device.floor_id))

    return render_template('add_description.html', device=device)

# صفحه خروج
@app.route('/logout', methods=['POST'])
def logout():
    logout_user()  # عملیات logout
    flash('شما با موفقیت از سیستم خارج شدید!', 'success')
    return redirect(url_for('login'))  # هدایت به صفحه ورود

# روت برای حذف طبقه
@app.route('/delete_floor/<int:floor_id>', methods=['POST'])
@login_required
def delete_floor(floor_id):
    floor = Floor.query.get_or_404(floor_id)
    
    # چک کردن اینکه طبقه متعلق به کاربر وارد شده است
    if floor.user_id != current_user.id:
        flash('شما اجازه حذف این طبقه را ندارید', 'danger')
        return redirect(url_for('view_floors'))
    
    # حذف دستگاه‌های مرتبط با طبقه قبل از حذف طبقه
    Device.query.filter_by(floor_id=floor.id).delete()
    db.session.delete(floor)
    db.session.commit()
    flash('طبقه با موفقیت حذف شد', 'success')
    return redirect(url_for('view_floors'))

# روت برای حذف دستگاه
@app.route('/delete_device/<int:device_id>', methods=['POST'])
@login_required
def delete_device(device_id):
    device = Device.query.get_or_404(device_id)
    
    # چک کردن اینکه دستگاه متعلق به طبقه‌ای است که به کاربر وارد شده تعلق دارد
    if device.floor.user_id != current_user.id:
        flash('شما اجازه حذف این دستگاه را ندارید', 'danger')
        return redirect(url_for('view_devices', floor_id=device.floor.id))
                        
    db.session.delete(device)
    db.session.commit()
    flash('دستگاه با موفقیت حذف شد', 'success')
    return redirect(url_for('view_devices', floor_id=device.floor.id))

if __name__ == "__main__":
    app.run(debug=True)

#host='192.168.143.233', port=5000