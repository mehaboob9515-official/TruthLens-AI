from flask import Flask, render_template, request, redirect, url_for, send_file, session
import joblib
from newspaper import Article
import sqlite3
import io
from textblob import TextBlob
import yake
import spacy
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import feedparser
import requests
from urllib.parse import quote
from config import NEWS_API_KEY

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from openpyxl import Workbook
from trusted_sources import check_source
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = "truthlens-secret-key"

# Load NLP model
nlp = spacy.load("en_core_web_sm")
def generate_summary(text):

    try:
        text = text.strip()

        if not text:
            return "No article text available for summary."

        # Try Sumy summarization
        parser = PlaintextParser.from_string(
            text,
            Tokenizer("english")
        )

        summarizer = LsaSummarizer()

        sentences = summarizer(parser.document, 3)

        summary = " ".join(
            str(sentence) for sentence in sentences
        )

        if summary.strip():
            return summary

    except Exception:
        pass

    # Fallback summary
    try:
        clean_text = text.replace("\n", " ")

        sentences = clean_text.split(". ")

        sentences = [
            sentence.strip()
            for sentence in sentences
            if len(sentence.strip()) > 30
        ]

        if sentences:
            summary = ". ".join(sentences[:3])

            if not summary.endswith("."):
                summary += "."

            return summary

        return "The article is too short to generate a summary."

    except Exception:
       return "Summary could not be generated."


def check_evidence(claim):
    try:
        query = quote(claim)

        url = f"https://news.google.com/rss/search?q={query}"
        print("Google News URL:", url)

        feed = feedparser.parse(url)

        print("Feed entries:", len(feed.entries))

        if not feed.entries:
            return "🔴 No supporting evidence found.", []

        articles = []

        for entry in feed.entries[:5]:
            articles.append({
                "title": entry.title,
                "link": entry.link
            })

        return "🟢 Related news articles found.", articles

    except Exception as e:
        print("Evidence Error:", e)
        return "⚠ Unable to verify the claim.", []


# ===========================
# Keyword Extraction
# ===========================
def extract_keywords(text):

    try:
        if not text or len(text.strip()) < 20:
            return []

        kw_extractor = yake.KeywordExtractor(
            lan="en",
            n=2,
            dedupLim=0.7,
            top=8
        )

        keywords = kw_extractor.extract_keywords(text)

        return [keyword for keyword, score in keywords]

    except Exception as e:
        print("Keyword extraction error:", e)
        return []
    
# Load the trained AI model
model = joblib.load("model.pkl")
print("Supports predict_proba:", hasattr(model, "predict_proba"))

# ===========================
# Named Entity Recognition
# ===========================
def extract_entities(text):

    try:
        if not text or len(text.strip()) < 20:
            return {
                "people": [],
                "organizations": [],
                "locations": []
            }

        doc = nlp(text)

        people = []
        organizations = []
        locations = []

        for ent in doc.ents:

            if ent.label_ == "PERSON":
                people.append(ent.text)

            elif ent.label_ == "ORG":
                organizations.append(ent.text)

            elif ent.label_ in ["GPE", "LOC"]:
                locations.append(ent.text)

        return {
            "people": list(dict.fromkeys(people))[:10],
            "organizations": list(dict.fromkeys(organizations))[:10],
            "locations": list(dict.fromkeys(locations))[:10]
        }

    except Exception as e:
        print("Entity extraction error:", e)

        return {
            "people": [],
            "organizations": [],
            "locations": []
        }

   
        return 0, "⚪ Unable to calculate"
# ===========================
# Overall Trust Score
# ===========================
def calculate_trust_score(
    prediction,
    confidence,
    credibility,
    sentiment_score,
    keywords,
    entities
):

    try:
        # 1. AI Prediction — 40%
        if prediction == 1:
            ai_score = confidence
        else:
            ai_score = 100 - confidence

        # 2. Source Credibility — 30%
        credibility_text = str(credibility).lower()

        if (
            "high" in credibility_text
            or "trusted" in credibility_text
            or "reliable" in credibility_text
        ):
            source_score = 100

        elif (
            "medium" in credibility_text
            or "moderate" in credibility_text
        ):
            source_score = 65

        elif (
            "low" in credibility_text
            or "untrusted" in credibility_text
        ):
            source_score = 25

        else:
            source_score = 50

        # 3. Article Tone — 10%
        tone_score = 100 - (abs(sentiment_score) * 100)

        tone_score = max(0, min(tone_score, 100))

        # 4. Content Signals — 10%
        keyword_score = min(len(keywords) * 12.5, 100)

        # 5. Entity Detection — 10%
        entity_count = (
            len(entities.get("people", []))
            + len(entities.get("organizations", []))
            + len(entities.get("locations", []))
        )

        entity_score = min(entity_count * 10, 100)

        # Final weighted score
        score = (
            ai_score * 0.40
            + source_score * 0.30
            + tone_score * 0.10
            + keyword_score * 0.10
            + entity_score * 0.10
        )

        score = max(0, min(round(score), 100))

        # Assessment
        if score >= 80:
            assessment = "🟢 Relatively Trustworthy"
        elif score >= 60:
            assessment = "🟡 Needs Verification"
        else:
            assessment = "🔴 Low Trust"

        return score, assessment

    except Exception as e:
        print("Trust score error:", e)

        # ===========================
# AI Explainability
# ===========================
def generate_ai_explanation(
    prediction,
    confidence,
    credibility,
    sentiment_score,
    trust_score,
    keywords,
    entities
):
    explanation = []

    if confidence >= 90:
        explanation.append(
            f"High AI confidence ({confidence}%)."
        )
    elif confidence >= 70:
        explanation.append(
            f"Moderate AI confidence ({confidence}%)."
        )
    else:
        explanation.append(
            f"Low AI confidence ({confidence}%)."
        )

    if credibility == "High":
        explanation.append(
            "The news source is considered reliable."
        )
    elif credibility == "Low":
        explanation.append(
            "The news source has low credibility."
        )
    else:
        explanation.append(
            "Source credibility could not be verified."
        )

    if abs(sentiment_score) > 0.6:
        explanation.append(
            "The article uses highly emotional language."
        )
    else:
        explanation.append(
            "The language is mostly neutral."
        )

    if len(keywords) >= 8:
        explanation.append(
            "The article contains many important keywords."
        )

    if len(entities) >= 5:
        explanation.append(
            "Multiple named entities were detected."
        )

    explanation.append(
        f"Overall Trust Score: {trust_score}/100."
    )

    return explanation

# ===========================
# Suspicious Word Highlighting
# ===========================
def highlight_suspicious_words(text):

    suspicious_words = [
        "breaking",
        "shocking",
        "exclusive",
        "secret",
        "miracle",
        "viral",
        "urgent",
        "must read",
        "100%",
        "guaranteed",
        "click here",
        "unbelievable",
        "warning",
        "exposed",
        "scandal"
    ]

    highlighted_text = text

    for word in suspicious_words:

        highlighted_text = highlighted_text.replace(
            word,
            f'<mark style="background:#ff5252;color:white;padding:2px 5px;border-radius:4px;">{word}</mark>'
        )

        highlighted_text = highlighted_text.replace(
            word.capitalize(),
            f'<mark style="background:#ff5252;color:white;padding:2px 5px;border-radius:4px;">{word.capitalize()}</mark>'
        )

        highlighted_text = highlighted_text.replace(
            word.upper(),
            f'<mark style="background:#ff5252;color:white;padding:2px 5px;border-radius:4px;">{word.upper()}</mark>'
        )

    return highlighted_text

# ===========================
# Home Page
# ===========================
@app.route("/")
def home():

    connection = sqlite3.connect("truthlens.db")
    cursor = connection.cursor()

    # Total analyses
    cursor.execute("SELECT COUNT(*) FROM history")
    total = cursor.fetchone()[0]

    # Real News
    cursor.execute("""
        SELECT COUNT(*) FROM history
        WHERE prediction='Real News'
    """)
    real = cursor.fetchone()[0]

    # Fake News
    cursor.execute("""
        SELECT COUNT(*) FROM history
        WHERE prediction='Fake News'
    """)
    fake = cursor.fetchone()[0]

    # Average Confidence
    cursor.execute("""
        SELECT AVG(confidence)
        FROM history
    """)

    average = cursor.fetchone()[0]

    if average is None:
        average = 0

    average = round(average, 2)

    connection.close()

    return render_template(
        "index.html",
        total=total,
        real=real,
        fake=fake,
        average=average
    )

# ===========================
# About Page
# ===========================

@app.route("/about")
def about():
    return render_template("about.html")

# ===========================
# Contact Page
# ===========================

@app.route("/contact")
def contact():
    return render_template("contact.html")

   # ===========================
# Analytics Dashboard
# ===========================

@app.route("/analytics")
def analytics():

    # Only logged-in users can access analytics
    if not session.get("user_id"):
        return redirect(url_for("login"))

    connection = sqlite3.connect("truthlens.db")
    cursor = connection.cursor()

    user_id = session.get("user_id")

    # Total articles for current user
    cursor.execute("""
        SELECT COUNT(*)
        FROM history
        WHERE user_id = ?
    """, (user_id,))

    total_articles = cursor.fetchone()[0]

    # Real news count
    cursor.execute("""
        SELECT COUNT(*)
        FROM history
        WHERE user_id = ?
        AND prediction LIKE '%Real%'
    """, (user_id,))

    real_count = cursor.fetchone()[0]

    # Fake news count
    cursor.execute("""
        SELECT COUNT(*)
        FROM history
        WHERE user_id = ?
        AND prediction LIKE '%Fake%'
    """, (user_id,))

    fake_count = cursor.fetchone()[0]

    # Average confidence
    cursor.execute("""
        SELECT AVG(confidence)
        FROM history
        WHERE user_id = ?
    """, (user_id,))

    average_confidence = cursor.fetchone()[0] or 0

    connection.close()

    average_confidence = round(average_confidence, 2)

    return render_template(
        "analytics.html",
        total_articles=total_articles,
        real_count=real_count,
        fake_count=fake_count,
        average_confidence=average_confidence
    )

# ===========================
# History Page (with Search)
# ===========================

@app.route("/history")
def history():

    # Only logged-in users can view history
    if not session.get("user_id"):
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()

    connection = sqlite3.connect("truthlens.db")
    cursor = connection.cursor()

    if search:
        cursor.execute("""
            SELECT id, news, prediction, confidence
            FROM history
            WHERE user_id = ?
              AND (
                    news LIKE ?
                    OR prediction LIKE ?
                  )
            ORDER BY id DESC
        """, (
            session.get("user_id"),
            f"%{search}%",
            f"%{search}%"
        ))

    else:
        cursor.execute("""
            SELECT id, news, prediction, confidence
            FROM history
            WHERE user_id = ?
            ORDER BY id DESC
        """, (
            session.get("user_id"),
        ))

    history = cursor.fetchall()

    connection.close()

    return render_template(
        "history.html",
        history=history,
        search=search
    )

connection = sqlite3.connect("truthlens.db")
cursor = connection.cursor()

# History table
cursor.execute("""
CREATE TABLE IF NOT EXISTS history (

    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news TEXT,
    prediction TEXT,
    confidence REAL

)
""")

# Users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    username TEXT UNIQUE NOT NULL,

    email TEXT UNIQUE NOT NULL,

    password TEXT NOT NULL,

is_admin INTEGER DEFAULT 0

)
""")

# Add user_id to history table if it does not already exist
try:
    cursor.execute("ALTER TABLE history ADD COLUMN user_id INTEGER")
except sqlite3.OperationalError:
    pass

connection.commit()
connection.close()


# ===========================
# Export PDF
# ===========================
@app.route("/export/pdf")
def export_pdf():

    connection = sqlite3.connect("truthlens.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, prediction, confidence, created_at
        FROM history
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    connection.close()

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer)

    data = [["ID", "Prediction", "Confidence", "Date"]]

    for row in rows:
        data.append([
            str(row[0]),
            row[1],
            f"{row[2]}%",
            row[3]
        ])

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.darkblue),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),1,colors.grey),
        ("BACKGROUND",(0,1),(-1,-1),colors.beige),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("BOTTOMPADDING",(0,0),(-1,0),10),
    ]))

    doc.build([table])

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="TruthLens_Report.pdf",
        mimetype="application/pdf"
    )


# ===========================
# Export Excel
# ===========================
@app.route("/export/excel")
def export_excel():

    connection = sqlite3.connect("truthlens.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, prediction, confidence, created_at
        FROM history
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    connection.close()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "TruthLens History"

    sheet.append([
        "ID",
        "Prediction",
        "Confidence",
        "Date"
    ])

    for row in rows:
        sheet.append([
            row[0],
            row[1],
            row[2],
            row[3]
        ])

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="TruthLens_Report.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ===========================
# Delete Record
# ===========================
@app.route("/delete/<int:record_id>")
def delete(record_id):

    connection = sqlite3.connect("truthlens.db")
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM history WHERE id=?",
        (record_id,)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("history"))
# ===========================
# Dashboard
# ===========================

@app.route("/dashboard")
def dashboard():

    # Only logged-in users can access dashboard
    if not session.get("user_id"):
        return redirect(url_for("login"))

    connection = sqlite3.connect("truthlens.db")
    cursor = connection.cursor()

    user_id = session.get("user_id")

    # Total analyses for current user
    cursor.execute("""
        SELECT COUNT(*)
        FROM history
        WHERE user_id = ?
    """, (user_id,))

    total = cursor.fetchone()[0]

    # Real news count
    cursor.execute("""
        SELECT COUNT(*)
        FROM history
        WHERE user_id = ?
        AND prediction LIKE '%Real%'
    """, (user_id,))

    real = cursor.fetchone()[0]

    # Fake news count
    cursor.execute("""
        SELECT COUNT(*)
        FROM history
        WHERE user_id = ?
        AND prediction LIKE '%Fake%'
    """, (user_id,))

    fake = cursor.fetchone()[0]

    # Average confidence
    cursor.execute("""
        SELECT AVG(confidence)
        FROM history
        WHERE user_id = ?
    """, (user_id,))

    average = cursor.fetchone()[0] or 0
    average = round(average, 2)

    # Calculate percentages
    if total > 0:
        real_percentage = round((real / total) * 100, 2)
        fake_percentage = round((fake / total) * 100, 2)
    else:
        real_percentage = 0
        fake_percentage = 0

    # Verification status
    if fake_percentage >= 50:
        verification_status = "High misinformation detected"
    else:
        verification_status = "Mostly reliable results"

    # Daily trend
    # Your current history table has no created_at column,
    # so use an empty list until a date column is added.
    daily_data = []

    connection.close()

    return render_template(
        "dashboard.html",
        total=total,
        real=real,
        fake=fake,
        average=average,
        real_percentage=real_percentage,
        fake_percentage=fake_percentage,
        verification_status=verification_status,
        daily_data=daily_data
    )

# ===========================
# Latest News
# ===========================

@app.route("/latest")
def latest():

    feed = feedparser.parse("https://feeds.bbci.co.uk/news/rss.xml")

    news_list = []

    for entry in feed.entries[:10]:
        news_list.append({
            "title": entry.title,
            "link": entry.link
        })

    return render_template(
        "latest.html",
        news_list=news_list
    )

# ===========================
# Analyze Latest News
# ===========================
@app.route("/analyze_latest", methods=["POST"])
def analyze_latest():

    url = request.form.get("url", "").strip()

    try:
        article = Article(url)
        article.download()
        article.parse()

        news = article.title + " " + article.text
        title = article.title

        source, credibility = check_source(url)

    except Exception:
        return render_template(
            "index.html",
            prediction="Unable to read article.",
            confidence=0,
            explanation=[
                "The article could not be downloaded."
            ]
        )

       # AI Prediction
    prediction = model.predict([news])[0]

    # Confidence
    decision = model.decision_function([news])[0]

    confidence = round(
        50 + (49 * abs(decision) / (abs(decision) + 1)),
        2
    )

    # Summary
    summary = generate_summary(news)

    # Keywords
    keywords = extract_keywords(news)

    # Named Entities
    entities = extract_entities(news)

    # Highlight suspicious words
    highlighted_news = highlight_suspicious_words(news)

    # Evidence Check
    evidence_status, evidence_articles = check_evidence(
        title if title else news[:100]
    )

    # Sentiment
    sentiment_score = TextBlob(news).sentiment.polarity

    if sentiment_score > 0.05:
        sentiment = "Positive"
    elif sentiment_score < -0.05:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    sentiment_score = round(sentiment_score, 3)

    # Trust Score
    trust_score, trust_assessment = calculate_trust_score(
        prediction,
        confidence,
        credibility,
        sentiment_score,
        keywords,
        entities
    )

    # AI Explanation
    ai_explanation = generate_ai_explanation(
        prediction,
        confidence,
        credibility,
        sentiment_score,
        trust_score,
        keywords,
        entities
    )

    # Result
    if prediction == 1:

        result = "Real News"

        explanation = [
            "Writing style appears professional.",
            "Language is mostly neutral.",
            "No strong clickbait patterns detected.",
            "Article structure resembles reliable news."
        ]

    else:

        result = "Fake News"

        explanation = [
            "Possible sensational language detected.",
            "Writing pattern differs from reliable news.",
            "AI found characteristics often seen in misinformation.",
            "Verify using trusted news sources."
        ]

       # Save to Database
    connection = sqlite3.connect("truthlens.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO history(
            news,
            prediction,
            confidence,
            user_id
        )
        VALUES (?, ?, ?, ?)
    """, (
        news[:500],
        result,
        confidence,
        session.get("user_id")
    ))

    connection.commit()
    connection.close()

    return render_template(
        "index.html",
        prediction=result,
        confidence=confidence,
        explanation=explanation,
        source=source,
        credibility=credibility,
        title=title,
        sentiment=sentiment,
        sentiment_score=sentiment_score,
        summary=summary,
        keywords=keywords,
        entities=entities,
        highlighted_news=highlighted_news,
        trust_score=trust_score,
        trust_assessment=trust_assessment,
        evidence_status=evidence_status,
        evidence_articles=evidence_articles,
        ai_explanation=ai_explanation,
    )

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        connection = sqlite3.connect("truthlens.db")
        cursor = connection.cursor()

        try:
            cursor.execute("""
                INSERT INTO users(username, email, password)
                VALUES (?, ?, ?)
            """, (username, email, password))

            connection.commit()

        except sqlite3.IntegrityError:

            connection.close()

            return "Username or email already exists."

        connection.close()

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = sqlite3.connect("truthlens.db")
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id, username, password FROM users WHERE email=?",
            (email,)
        )

        user = cursor.fetchone()

        connection.close()

        if user and check_password_hash(user[2], password):

            session["user_id"] = user[0]
            session["username"] = user[1]

            return redirect("/")

        return "Invalid email or password."

    return render_template("login.html")

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

# ===========================
# Prediction
# ===========================

@app.route("/predict", methods=["POST"])
def predict():

    # Only logged-in users can analyze news
    if not session.get("user_id"):
        return redirect(url_for("login"))

    news = request.form.get("news", "").strip()
    url = request.form.get("url", "").strip()

    source = "Unknown"
    credibility = "Unknown"
    title = ""

    # Read article from URL
    if url:
        try:
            article = Article(url)
            article.download()
            article.parse()

            news = article.title + " " + article.text
            title = article.title

            source, credibility = check_source(url)

        except Exception:
            return render_template(
                "index.html",
                prediction="Unable to read the article from the URL.",
                confidence=0,
                explanation=[
                    "The article could not be downloaded. Please try another URL or paste the article text."
                ]
            )

    # Validate input
    if not news:
        return render_template(
            "index.html",
            prediction="Please enter news text or a URL.",
            confidence=0,
            explanation=[
                "Please provide news text or a valid article URL."
            ]
        )

        # AI Prediction
    prediction = model.predict([news])[0]

    # Confidence
    decision = model.decision_function([news])[0]

    confidence = round(
        50 + (49 * abs(decision) / (abs(decision) + 1)),
        2
    )

    # AI Article Summary
    summary = generate_summary(news)
    keywords = extract_keywords(news)
    entities = extract_entities(news)

    # Highlight suspicious words
    highlighted_news = highlight_suspicious_words(news)

    # Evidence Check
    evidence_status, evidence_articles = check_evidence(
        title if title else news[:100]
    )

    # Sentiment Analysis
    sentiment_score = TextBlob(news).sentiment.polarity

    if sentiment_score > 0.05:
        sentiment = "Positive"
    elif sentiment_score < -0.05:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    sentiment_score = round(sentiment_score, 3)

    # Trust Score
    trust_score, trust_assessment = calculate_trust_score(
        prediction,
        confidence,
        credibility,
        sentiment_score,
        keywords,
        entities
    )

    # AI Explainability
    ai_explanation = generate_ai_explanation(
        prediction,
        confidence,
        credibility,
        sentiment_score,
        trust_score,
        keywords,
        entities
    )

    # AI Explanation
    if prediction == 1:

        result = "Real News"

        explanation = [
            "Writing style appears professional.",
            "Language is mostly neutral.",
            "No strong clickbait patterns detected.",
            "Article structure resembles reliable news."
        ]

    else:

        result = "Fake News"

        explanation = [
            "Possible sensational language detected.",
            "Writing pattern differs from many reliable articles.",
            "AI found characteristics often seen in misinformation.",
            "Verify this information using trusted news sources."
        ]

    # Save to Database
    connection = sqlite3.connect("truthlens.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO history(
            news,
            prediction,
            confidence,
            user_id
        )
        VALUES (?, ?, ?, ?)
    """, (
        news[:500],
        result,
        confidence,
        session.get("user_id")
    ))

    connection.commit()
    connection.close()

    # Save report data for PDF download
    session["report"] = {
        "prediction": result,
        "confidence": confidence,
        "trust_score": trust_score,
        "sentiment": sentiment,
        "summary": summary,
        "explanation": explanation
    }

    # Dashboard statistics for current user
    connection = sqlite3.connect("truthlens.db")
    cursor = connection.cursor()

    user_id = session.get("user_id")

    cursor.execute("""
        SELECT COUNT(*)
        FROM history
        WHERE user_id = ?
    """, (user_id,))

    total_articles = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM history
        WHERE user_id = ?
        AND prediction LIKE '%Real%'
    """, (user_id,))

    real_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM history
        WHERE user_id = ?
        AND prediction LIKE '%Fake%'
    """, (user_id,))

    fake_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT AVG(confidence)
        FROM history
        WHERE user_id = ?
    """, (user_id,))

    average_confidence = cursor.fetchone()[0] or 0

    connection.close()

    average_confidence = round(average_confidence, 2)

    # Display results
    return render_template(
        "index.html",
        prediction=result,
        confidence=confidence,
        explanation=explanation,
        source=source,
        credibility=credibility,
        title=title,
        sentiment=sentiment,
        sentiment_score=sentiment_score,
        summary=summary,
        keywords=keywords,
        entities=entities,
        highlighted_news=highlighted_news,
        trust_score=trust_score,
        trust_assessment=trust_assessment,
        evidence_status=evidence_status,
        evidence_articles=evidence_articles,
        ai_explanation=ai_explanation,
        total_articles=total_articles,
        real_count=real_count,
        fake_count=fake_count,
        average_confidence=average_confidence
    )

# ===========================
# Custom 404 Error Page
# ===========================
@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

# ===========================
# Custom 500 Error Page
# ===========================
@app.errorhandler(500)
def internal_server_error(error):
    return render_template("500.html"), 500

# ===========================
# Run App
# ===========================
if __name__ == "__main__":
    app.run(debug=True)