from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

connection = sqlite3.connect('sqlite.db', check_same_thread=False)
cursor = connection.cursor()
app = Flask(__name__)
app.config['SECRET_KEY'] = 'kGI/T&w7iTW76t9'

login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    user = cursor.execute('select * from user where id = ?', (user_id,)).fetchone()
    if user is not None:
        return User(user[0], user[1], user[2])
    return None

def close_db(connection = None):
    if connection is not None:
        connection.close()


@app.teardown_appcontext
def close_connection(exception):
    close_db()


@app.route("/")
def index():
    cursor.execute('''select post.id, post.title, post.content, post.author_id,
    user.username, count(likes.id) as like_count from post join user on post.author_id = user.id
    left join likes on post.id = likes.post_id
    group by post.id, post.title, post.content, post.author_id, user.username''')
    result = cursor.fetchall()
    posts = []
    for post in reversed(result):
        posts.append({'id': post[0], 'title': post[1], 'content': post[2], 'author_id': post[3], 'username': post[4], 'likes': post[5]})
        if current_user.is_authenticated:
            cursor.execute('select post_id from likes where user_id = ?', (current_user.id,))
            likes_result = cursor.fetchall()
            liked_posts = []
            for like in likes_result:
                liked_posts.append(like[0])
            posts[-1]['liked_posts'] = liked_posts
    context = {'posts': posts}
    return render_template('blog.html', **context)

@app.route('/add/', methods=['GET', 'POST'])
@login_required
def add_post():
    if request.method == 'POST':
        print("OK")
        title = request.form['title']
        content = request.form['content']
        cursor.execute('insert into post (title, content, author_id) values (?, ?, ?)',
                       (title, content, current_user.id))
        connection.commit()
        return redirect(url_for("index"))
    return render_template('Add_Post.html')


@app.route('/delete/<post_id>', methods=['POST'])
def delete(post_id):
    delete_id = post_id
    cursor.execute('select * from post where id = ?', (delete_id,))
    del_res = cursor.fetchone()
    if del_res and del_res[3] == current_user.id:
        cursor.execute('delete from post where id = ?', (delete_id,))
        connection.commit()
        return redirect(url_for("index"))
    else:
        return redirect(url_for("index"))


@app.route('/post/<post_id>')
def post(post_id):
    select_id = post_id
    cursor.execute('select * from post where id = ?', (select_id,))
    res = cursor.fetchone()
    post_dict = {'id': res[0], 'title': res[1], 'content': res[2], 'author_id': res[3]}
    connection.commit()
    return render_template('post.html', post=post_dict)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        try:
            cursor.execute('insert into user (username, password_hash, email) values (?, ?, ?)',
                           (username, generate_password_hash(password, method="pbkdf2:sha256"), email)
                           )
            connection.commit()
            print("Registration was sucsessfull")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', message='Username already exists!')
    return render_template('Register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = cursor.execute('select * from user where username = ?', (username,)).fetchone()
        if user and User(user[0], user[1], user[2]).check_password(password):
            login_user(User(user[0], user[1], user[2]))
            return redirect(url_for('index'))
        else:
            return render_template('login.html', message='invalid username or password')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


def user_is_liking(user_id, post_id):
    like = cursor.execute('select * from likes where user_id = ? and post_id = ?',
                          (user_id, post_id)).fetchone()
    return bool(like)


@app.route('/like/<int:post_id>')
@login_required
def like_post(post_id):
    post = cursor.execute('select * from post where id = ?',
                          (post_id,)).fetchone()
    if post:
        if user_is_liking(current_user.id, post_id):
            cursor.execute(
                'delete from likes where user_id = ? and post_id = ?',
                (current_user.id, post_id)
            )
            connection.commit()
            print('You unliked this post.')
        else:
            cursor.execute(
                'insert into likes (user_id, post_id) values (?, ?)',
                (current_user.id, post_id)
            )
            connection.commit()
            print("You liked this post!")
        return redirect(url_for('index'))
    return 'Post not found', 404


if __name__ == "__main__":
    app.run()
