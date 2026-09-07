from flask import Flask, render_template, request, redirect
import pymysql
import os

app = Flask(__name__)


def get_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )


def get_users():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT name FROM Users")
    users = cursor.fetchall()

    cursor.close()
    connection.close()

    return users


@app.route("/")
def home():
    users = get_users()
    return render_template(
        os.getenv("APP_TEMPLATE", "index.html"),
        messages=users
    )


@app.route("/add", methods=["POST"])
def add_message():
    message = request.form["message"]

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO Users (name) VALUES (%s)",
        (message,)
    )

    connection.commit()

    cursor.close()
    connection.close()

    return redirect("/")

@app.route("/delete/<int:user_id>", methods=["POST"])
def delete_message(user_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM Users WHERE id = %s",
        (user_id,)
    )

    connection.commit()

    cursor.close()
    connection.close()

    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
