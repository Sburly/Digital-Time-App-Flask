from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    session,
    request,
    url_for,
    flash,
    Response
)
from datetime import datetime
import uuid
from dataclasses import asdict
from digital_time_app.forms import AddDateForm, RegisterForm, LoginForm
from digital_time_app.models import Date, User
import re
from passlib.hash import pbkdf2_sha256
import functools


pages = Blueprint(
    "pages", __name__, template_folder="templates", static_folder="static"
)


def login_required(route):
    @functools.wraps(route)
    def route_wrapper(*args, **kwargs):
        if session.get("email") is None:
            return redirect(url_for(".login"))

        return route(*args, **kwargs)

    return route_wrapper


def pretty_timedelta(selected_date):
    try:
        today = datetime.today()
        x = selected_date.split("-")
        year, month, day = x
        sel_date = datetime(int(year), int(month), int(day))
        if str((today - sel_date).days)[0] == "-":
            return str((today - sel_date).days).lstrip("-") + " days left"
        return str((today - sel_date).days) + " days ago"
    except Exception as e:
        print(e)


def pretty_date(selected_date):
    # When a date from the input type="date" is selected, the string looks like this: "year-month-day". This function transforms this string into: day/month/year
    return "/".join(map(str, selected_date.split("-")[::-1])).strip("/")


@ pages.get("/get_time")
# Update time on the screen realtime (every second)
# >>> index.html (HTML script -> JavaScript)
def get_time():
    def update_time():
        yield datetime.now().strftime("%H:%M:%S")
    return Response(update_time(), mimetype='text')


@ pages.get("/get_date")
# Update time on the screen realtime (every 5 seconds)
# >>> index.html (HTML script -> JavaScript)
def get_date():
    def update_date():
        yield datetime.now().strftime("%A %d %B %Y")
    return Response(update_date(), mimetype='text')


@ pages.get("/toggle-theme")
# Function for the dark-mode
# In the session we store a value called theme, which can be modified when clicking on a button. This action triggers the change in the HTML root
# >>> layout.html -> macros/header.html
# >>> css/main.css
def toggle_theme():
    current_theme = session.get("theme")
    if current_theme == "dark":
        session["theme"] = "light"
    else:
        session["theme"] = "dark"
    return redirect(request.args.get("current_page"))


@pages.get("/delete_date/<string:_id>")
@login_required
# This function is connected to an html link. This allows us to get the link as a querystring parameter and to use it to delete specific dates from our database
# >>> index.html
def delete_date(_id):
    current_app.db.dates.delete_one({"_id": _id})
    return redirect(url_for(".index"))


@pages.get("/update_timedelta/<string:_id>")
@login_required
# Update timedelta on real time for every date
def update_timedelta(_id: str):
    # We have to modify the output in order for it to be acceptable by the pretty_timedelta function
    match = current_app.db.dates.find_one({"_id": _id})
    selected_date = (
        "-".join(map(str, match.get("selected_date").split("/")[::-1]))).strip("-")
    current_app.db.dates.update_one(
        {"_id": _id},
        {"$set": {"time_delta": (pretty_timedelta(selected_date))}}
    )
    return redirect(url_for(".index"))


@pages.route("/register", methods=["GET", "POST"])
def register():
    if session.get("email"):
        return redirect(url_for(".index"))
    # Thi means that the user is already logged in
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            _id=uuid.uuid4().hex,
            email=form.email.data,
            password=pbkdf2_sha256.hash(form.password.data)
        )
        current_app.db.user.insert_one(asdict(user))
        flash("User registered succesfully", "Success")
        return redirect(url_for(".login"))
    return render_template(
        "register.html",
        title="Digital Time App - Register",
        form=form
    )


@pages.route("/login", methods=["GET", "POST"])
def login():
    if session.get("email"):
        return redirect(url_for(".index"))

    form = LoginForm()

    if form.validate_on_submit():
        user_data = current_app.db.user.find_one({"email": form.email.data})
        if not user_data:
            flash("Login credentials not correct", category="danger")
            return redirect(url_for(".login"))
        user = User(**user_data)

        if user and pbkdf2_sha256.verify(form.password.data, user.password):
            session["user_id"] = user._id
            session["email"] = user.email

            return redirect(url_for(".index"))

        flash("Login credentials not correct", category="danger")

    return render_template("login.html", title="Digital Time App - Login", form=form)


@pages.route("/logout")
@login_required
def logout():
    current_theme = session.get("theme")
    session.clear()
    session["theme"] = current_theme
    # We do this because we wanna keep the dark or light theme even after the log out
    return redirect(url_for(".login"))


@ pages.route("/", methods=['GET', 'POST'])
@login_required
# Main page where most things happen
def index():
    # Create an instance of the form we created in forms.py
    form = AddDateForm()
    # Helps us display the dates stored in our database even before the form is submitted
    user_data = current_app.db.user.find_one({"email": session["email"]})
    user = User(**user_data)
    dates_data = current_app.db.dates.find({"_id": {"$in": user.dates}})
    displayed_dates = [Date(**date) for date in dates_data]

    if form.validate_on_submit():
        # When the form is submitted, we create an instance of the Date object (that we created into the models.py file), and we pass down the arguments that the user inserted
        try:
            date = Date(
                _id=uuid.uuid4().hex,
                title=form.title.data,
                selected_date=pretty_date(form.selected_date.data),
                time_delta=pretty_timedelta(form.selected_date.data)
            )
            current_app.db.user.update_one(
                {"_id": session["user_id"]}, {"$push": {"dates": date._id}}
            )
            # We then insert this object as a dictionary into the database
            current_app.db.dates.insert_one(asdict(date))
            # Refreshes the page for us
            return redirect("/")
        except Exception as e:
            # If there is an error in the page, instead of making the whole thing crash, we display a simple error message
            print(e)
            flash("An issue was found in the formatting of the input")
    return render_template(
        "index.html",
        current_time=datetime.now().strftime("%H:%M:%S"),
        current_date=datetime.now().strftime("%A %d %B %Y"),
        form=form,
        dates=displayed_dates
    )
