from flask import Flask, render_template, request
from text_summarizer import summarize_nltk_text
from text_summarizer import fake_news_or_not
import spacy
import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


nlp = spacy.load('en')
app = Flask(__name__)
app.static_folder = 'static'


# Set up SQL_lite db
basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+os.path.join(basedir, 'data.sqlite')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
Migrate(app, db)
# -----------------------------------------------------------------------------------------


class URLS(db.Model):

    # Manual Table name overwrite
    __tablename__ = 'urls'
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.Text)

    def __init__(self, url):
        self.url = url

    def __repr__(self):
        return f"url is {self.url}"

# ----------------------------------------------------------------------------


db.create_all()

raw_url = ""
final_summary = ""
reliable_source = ""


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze_url', methods=['GET', 'POST'])
def analyze_url():
    if request.method == 'POST':
        raw_url = request.form['raw_url']
        final_summary = summarize_nltk_text(raw_url)
        reliable_source = fake_news_or_not(raw_url)
        db.session.add(URLS(raw_url))
        db.session.commit()

        urls = URLS.query.all()
        return render_template('index.html', urls=urls, final_summary=final_summary, raw_url=raw_url, reliable_source=reliable_source)


@app.route('/clear_urls', methods=['GET', 'POST'])
def del_urls():
    if request.method == 'POST':
        row_exists = bool(db.session.query(URLS).first())
        urls = ""
        if row_exists:
            db.session.query(URLS).delete()
            db.session.commit()
        return render_template('index.html', urls=urls, final_summary=final_summary, raw_url=raw_url, reliable_source=reliable_source)


if __name__ == '__main__':
    app.run(debug=True)
