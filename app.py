from cs50 import SQL
from flask import Flask, flash, redirect, jsonify, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, usd

from datetime import datetime, timezone

app = Flask(__name__)

app.jinja_env.filters["usd"] = usd

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


db = SQL("sqlite:///favorites.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/", methods=["GET"])
@login_required
def index():
    return render_template("index.html")

@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect("/")

@app.route("/bookings", methods=["GET", "POST"])
@login_required
def bookings():

    if request.method == "GET":
        bookings_d = db.execute("SELECT course, date, time, price, party_count, name FROM bookings WHERE id = ?", session["user_id"])
        hold = []
        len1 = len(bookings_d)
        for t in range(len1):
           course = bookings_d[t]["course"]
           date = bookings_d[t]["date"]
           price = usd(bookings_d[t]["price"])
           name = bookings_d[t]["name"]
           party_count = bookings_d[t]["party_count"]
           time = bookings_d[t]["time"]
           table = {"course": course, "date": date, "price": price, "party_count": party_count, "time": time, "name": name}
           hold.append(table)
        upcoming_bookings = db.execute("SELECT date, course, time, price FROM bookings WHERE id = ?", session["user_id"])
        len4 = len(upcoming_bookings)
        upcomings = []
        for t in range(len4):
            upcoming_date = upcoming_bookings[t]["date"]
            date_obj = datetime.strptime(upcoming_date, "%m/%d/%Y")
            if date_obj > datetime.now():
                upcoming_price = upcoming_bookings[t]["price"]
                upcoming_course = upcoming_bookings[t]["course"]
                upcoming_time = upcoming_bookings[t]["time"]
                course_info = {"course": upcoming_course, "date": upcoming_date, "time": upcoming_time, "price": upcoming_price}
                upcomings.append(course_info)
        distance = len(upcomings)
        new_distance = 1
        if distance > 4:
            new_distance = distance
    elif request.method == "POST":
        course_n = request.form.get("course-n")
        course_d = request.form.get("course-d")
        course_p = int(request.form.get("course-p"))
        course_t = request.form.get("course-t")
        recall_funds = db.execute("SELECT funds FROM users WHERE id = ?", session["user_id"])
        recall_newfunds = recall_funds[0]["funds"]
        insert_funds = course_p + recall_newfunds
        updt_recallfunds = db.execute("UPDATE users SET funds = ? WHERE id = ?", insert_funds, session["user_id"])
        recall_delete = db.execute("DELETE FROM bookings WHERE id = ? AND course = ? AND date = ? AND time = ?", session["user_id"], course_n, course_d, course_t)
        return redirect("/bookings")

    return render_template("bookings.html", hold = hold, upcomings = upcomings, new_distance = new_distance)

@app.route("/courses", methods=["GET", "POST"])
@login_required
def courses():
    reserve_name = request.form.get("reserve-name")
    count = request.form.get("count")
    book_time = request.form.get("time-select")
    calendar = request.form.get("calendar")
    course_name = request.form.get("course-name")
    course_id = request.form.get("course-id")
    f_price = request.form.get("pricer")
    if request.method == "GET":
        return render_template("courses.html")
    elif request.method == "POST":
        if not reserve_name or not count or not book_time or not calendar:
            return apology("One or more fields missing", 403)
        else:
            new_price = int(f_price)
            check_price = db.execute("SELECT funds FROM users WHERE id = ?", session["user_id"])
            indexed_price = check_price[0]["funds"]
            updt_funds = indexed_price - new_price
            if new_price > indexed_price:
                return apology("Insufficient funds", 403)
            insert_funds = db.execute("UPDATE users SET funds = ? WHERE id = ?", updt_funds, session["user_id"])
            usd_price = new_price
            booking = db.execute("INSERT INTO bookings (course, date, time, price, party_count, name, course_id, id) VALUES (?,?,?,?,?,?,?,?)", course_name, calendar, book_time, usd_price, count, reserve_name, course_id, session["user_id"])
        return redirect("/bookings")





@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    name_chng = request.form.get("fullname")
    pswd_chng = request.form.get("pswd")
    loc_chng = request.form.get("location")
    spent: int = 0

    if request.method == "GET":
        full = db.execute("SELECT name, funds FROM users WHERE id = ?", session["user_id"])
        final = full[0]["name"]
        funds = full[0]["funds"]
        recent_booking = db.execute("SELECT * FROM bookings WHERE id = ?", session["user_id"])
        len2 = len(recent_booking)
        if recent_booking:
            for t in range(len2):
                recent_course = recent_booking[t]["course"]
            for l in range(len2):
                spend = int(recent_booking[l]["price"])
                spent = spent + spend
        else:
            recent_course = 1
        return render_template("account.html", fullname = final, funds = usd(funds), r_course = recent_course, spent = usd(spent))
    else:
        deposit = request.form.get("money")
        if name_chng:
            name_updt = db.execute("UPDATE users SET name = ? WHERE id = ?", name_chng, session["user_id"])
        if pswd_chng:
            new_hash = generate_password_hash(pswd_chng)
            pswd_updt = db.execute("UPDATE users SET hash = ? WHERE id = ?", new_hash, session["user_id"])
        if loc_chng:
            loc_updt = db.execute("UPDATE users SET location = ? WHERE id = ?", loc_chng, session["user_id"])
        if deposit:
            if int(deposit) < 0:
                return apology("Cannot deposit negative funds", 403)
            current_funds = db.execute("SELECT funds FROM users WHERE id = ?", session["user_id"])
            old_funds = current_funds[0]["funds"]
            final_funds = old_funds + int(deposit)
            deposit_updt = db.execute("UPDATE users SET funds = ? WHERE id = ?", final_funds, session["user_id"])

        return redirect("/account")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method=="POST":
        if not request.form.get("username") or not request.form.get("password"):
            return apology("one or more fields left blank", 403)

        quest = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(quest) != 1:
            return apology("user does not exist", 403)

        elif not check_password_hash(quest[0]["hash"], request.form.get("password")):
            return apology("incorrect password", 403)

        session["user_id"] = quest[0]["id"]

        return redirect("/")
    else:
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("password")
    confirm = request.form.get("confirmation")
    fullname = request.form.get("fullname")

    if request.method=="POST":
        check = db.execute("SELECT * FROM users WHERE username = ?", username)
        if not username or not password or not confirm or not fullname:
            return apology("one or more fields left incomplete", 400)
        elif check:
            return apology("must provide unique username", 400)
        elif confirm != password:
            return apology("passwords don't match", 400)

        hash = generate_password_hash(password)
        add_user =  db.execute("INSERT INTO users (username, hash, name) VALUES (?,?,?)", username, hash, fullname)

        session["user_id"] = add_user
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/delete")
@login_required
def delete():
    del_updt = db.execute("DELETE FROM users WHERE id = ?", session["user_id"])
    return jsonify({'message': 'Item deleted'})


@app.route("/forbusinesses", methods=["GET"])
@login_required
def businesses():
    if request.method == "GET":
        return render_template("business.html")


@app.route("/aboutus", methods=["GET"])
@login_required
def aboutus():
    if request.method == "GET":
        return render_template("aboutus.html")