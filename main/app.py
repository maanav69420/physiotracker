from flask import Flask, render_template, send_from_directory
import os

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), '..', 'static')
)

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/inventory')
def inventory():
    return render_template('inventory.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/report')
def report():
    return render_template('report.html')

# Serve favicon if present
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, '../static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

# Custom 404 error handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html'), 404

if __name__ == '__main__':
    app.run(debug=True)