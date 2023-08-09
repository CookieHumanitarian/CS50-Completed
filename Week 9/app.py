from flask import Flask, render_template, request

app = Flask(__name__)

COLOR = ['red', 'blue']

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")
    else:
        color = request.form.get("color")
        if color in COLOR:
            return render_template("color.html", color=color)
        else:
            return render_template("index.html")
