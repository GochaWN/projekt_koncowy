from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import os
from flask_migrate import Migrate
import kaggle
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project2.db"
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Salary(db.Model):
    ID = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(50))
    state = db.Column(db.String(50), name='state')
    metro = db.Column(db.String(50))
    mean_salary_adjusted = db.Column(db.Float)


with app.app_context():
    db.create_all()

local_directory = os.environ.get('LOCAL_DIRECTORY', os.getcwd())
zip_file_path = os.path.join(local_directory, 'developer_salaries.zip')
csv_file_path = os.path.join(local_directory, 'SofwareDeveloperIncomeExpensesperUSACity.csv')

kaggle_config_dir = os.environ.get('KAGGLE_CONFIG_DIR', '.kaggle')
os.environ['KAGGLE_CONFIG_DIR'] = kaggle_config_dir

os.environ['KAGGLE_USERNAME'] = os.environ.get('KAGGLE_USERNAME')
os.environ['KAGGLE_KEY'] = os.environ.get('KAGGLE_KEY')


dataset_name = 'thedevastator/u-s-software-developer-salaries'

kaggle.api.authenticate()
try:
    kaggle.api.dataset_download_files(dataset_name, path=local_directory, unzip=True)
except Exception as e:
    print(f"Kaggle API Error: {e}")
    exit()
extracted_files = os.listdir(local_directory)



if os.path.exists(csv_file_path):
    size = os.path.getsize(csv_file_path)

    df = pd.read_csv('SofwareDeveloperIncomeExpensesperUSACity.csv')

    df.columns.values[0] = 'ID'
    df.columns.values[2] = 'mean_salary_adjusted'
    df.to_csv('SofwareDeveloperIncomeExpensesperUSACity.csv', index=False)


    df = pd.read_csv(csv_file_path)

    df[['City', 'State']] = df['City'].str.split(', ', n=1, expand=True)
    df.to_csv('SofwareDeveloperIncomeExpensesperUSACity.csv', index=False)

    state_mapping = {'TX': 'Texas', 'CA': 'California', 'NY': 'New York', 'FL': 'Florida', 'IL': 'Illinois'}
    df['State'] = df['State'].map(state_mapping)


    df.to_csv('SofwareDeveloperIncomeExpensesperUSACity.csv', index=False)


with app.app_context():
    df.to_sql('salary', db.engine, if_exists='replace', index=False)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/results', methods=['POST'])
def results():

    selected_state = request.form.get('state')

    print("Selected State:", selected_state)



    state_data = Salary.query.filter_by(state=selected_state).all()




    if not state_data:
        return render_template('error.html', message="No data for this state.")

    # 1. Średnie roczne zarobki dla programistów w wybranym stanie.
    average_salary = db.session.query(db.func.avg(Salary.mean_salary_adjusted)).filter_by(state=selected_state).scalar()

    # 2. Trzy miasta w danym stanie, w których programiści zarabiają najwięcej.
    top_cities = db.session.query(Salary.city).filter_by(state=selected_state).order_by(Salary.mean_salary_adjusted.desc()).limit(3).all()
    top_cities = [city[0] for city in top_cities]

    # 3. O ile procent powyżej średniej wynoszą zarobki w tych miastach w porównaniu do średnich zarobków w danym stanie.
    city_percentages = [
        (city, ((Salary.query.filter_by(state=selected_state,
                                        city=city).first().mean_salary_adjusted / average_salary) - 1) * 100)
        for city in top_cities
    ]

    # 4. Rekomendacja w którym mieście w danym stanie zarobki dla programistów są najwyższe.
    recommended_city = max(city_percentages, key=lambda x: x[1])[0]
    recommended_city_data = db.session.query(Salary).filter_by(state=selected_state, city=recommended_city).first()
    recommended_city_salary = recommended_city_data.mean_salary_adjusted if recommended_city_data else 0

    return render_template('results.html', state=selected_state, average_salary=average_salary,
                           top_cities=top_cities, city_percentages=city_percentages, recommended_city=recommended_city, recommended_city_salary=recommended_city_salary)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

