from flask import  render_template,session, request, redirect, url_for, flash
from flask_login import  login_user, login_required, logout_user, current_user
from datetime import datetime
import pytz
from functools import wraps
from models import User, Device, Floor, Description, app,db, login_manager


@app.route("/")
def home():
    return render_template("login.html")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def require_login_and_redirect(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            session['next_url'] = request.url
            flash('لطفاً برای ادامه لاگین کنید.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            login_user(user)
            next_url = session.pop('next_url', None)
            return redirect(next_url or url_for('dashboard'))
        else:
            flash('نام کاربری یا رمز عبور اشتباه است', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

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

@app.route('/view_floors')
@login_required
def view_floors():
    floors = Floor.query.all()
    return render_template('view_floors.html', floors=floors)

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

@app.route('/view_devices/<int:floor_id>')
@login_required
def view_devices(floor_id):
    floor = Floor.query.get_or_404(floor_id)
    devices = Device.query.filter_by(floor_id=floor.id).all()
    return render_template('view_devices.html', floor=floor, devices=devices)

def get_description_for_device(device_id):
    return Description.query.filter_by(device_id=device_id).order_by(Description.Date.desc()).all()

def get_device_by_id(id):    
    return  Device.query.get_or_404(id)

@app.route('/device/<int:device_id>', methods=['GET'])
@require_login_and_redirect
def device_details(device_id):    
    device = get_device_by_id(device_id) 
    description = get_description_for_device(device_id)  
    return render_template('device_details.html', device=device, description=description)

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

@app.route('/delete_device/<int:device_id>', methods=['POST'])
@login_required
def delete_device(device_id):
    device = Device.query.get_or_404(device_id)
    
    if device.floor.user_id != current_user.id:
        flash('شما اجازه حذف این دستگاه را ندارید', 'danger')
        return redirect(url_for('view_devices', floor_id=device.floor.id))                        
    
    db.session.delete(device)
    db.session.commit()
    flash('دستگاه با موفقیت حذف شد', 'success')
    return redirect(url_for('view_devices', floor_id=device.floor.id))

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

@app.route('/show_users')
@login_required
def show_users():
    users = User.query.all()  
    return render_template('show_users.html', users=users)

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        new_username = request.form['username']
        new_password = request.form['password']
        existing_user = User.query.filter_by(username=new_username).first()

        if existing_user and existing_user.id != user.id:
            flash('این نام کاربری قبلاً استفاده شده است.', 'danger')
            return redirect(url_for('edit_user', user_id=user.id))
        
        user.username = new_username
        user.password = new_password
        db.session.commit()
        flash('اطلاعات کاربری با موفقیت به روز شد.', 'success')
        return redirect(url_for('show_users'))
    return render_template('edit_user.html', user=user)

@app.route('/add_description/<int:device_id>', methods=['GET', 'POST'])
@login_required
def add_description(device_id):
    device = Device.query.get_or_404(device_id)
    if request.method == 'POST':
        description_content = request.form['description']
        new_description = Description(content=description_content, device_id=device.id, user_id=current_user.id)
        db.session.add(new_description)
        db.session.commit()
        flash('توضیحات با موفقیت اضافه شد!', 'success')
        return redirect(url_for('view_devices', floor_id=device.floor_id))
    return render_template('add_description.html', device=device)

@app.route('/edit_description/<int:description_id>', methods=['GET', 'POST'])
@login_required
def edit_description(description_id):
    description = Description.query.get_or_404(description_id)
    device = Device.query.get(description.device_id)
    if request.method == 'POST':
        description.content = request.form['content']
        description.Date = datetime.now(pytz.timezone('Asia/Tehran'))
        db.session.commit()
        flash('توضیحات با موفقیت ویرایش شد.', 'success')
        return redirect(url_for('device_details', device_id=description.device_id))
    return render_template('edit_description.html', description=description, device=device)

@app.route('/logout', methods=['POST'])
def logout():
    logout_user()
    flash('شما با موفقیت از سیستم خارج شدید!', 'success')
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)

#       host='192.168.143.233', port=5000