from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///league.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# league model
class League(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    teams = db.relationship('Team', backref='league',lazy=True)
    matches = db.relationship('Match', backref='league', lazy=True, cascade="all, delete-orphan")

# team model
class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False)
    played = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    draws = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    goals_for = db.Column(db.Integer, default=0)
    goals_against = db.Column(db.Integer, default=0)
    goal_difference = db.Column(db.Integer, default=0)

# match model
class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False)
    team_a_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    team_b_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    team_a_score = db.Column(db.Integer, default=0)
    team_b_score = db.Column(db.Integer, default=0)
    played = db.Column(db.Boolean, default=False)

    # relationships to get teams
    team_a = db.relationship('Team', foreign_keys=[team_a_id])
    team_b = db.relationship('Team', foreign_keys=[team_b_id])

def generate_fixtures(league_id):
    teams = Team.query.filter_by(league_id=league_id).all()
    fixtures = []
    
    # fixtures only generate when exactly 20 teams are in the league
    if len(teams) != 20:
        return
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            fixtures.append((teams[i].id, teams[j].id)) #home match
            fixtures.append((teams[j].id, teams[i].id)) #away match

    random.shuffle(fixtures) # shuffling to randomize match order

    for match in fixtures:
        new_match = Match(team_a_id=match[0], team_b_id=match[1], league_id=league_id)
        db.session.add(new_match)

    db.session.commit()

@app.route('/')
def home():
    league_id = request.args.get("league_id")
    leagues = League.query.all()
    selected_league = League.query.get(int(league_id)) if league_id else None
    return render_template('index.html', leagues=leagues, selected_league=selected_league, league_id=league_id)

@app.route('/league/<int:league_id>')
def view_league(league_id):
    league = League.query.get(league_id)
    teams = Team.query.filter_by(league_id=league_id).order_by(Team.points.desc(), Team.goal_difference.desc()).all()
    matches = Match.query.filter_by(league_id=league_id).all()
    return render_template('league.html', league=league, teams=teams, matches=matches)

@app.route('/create_league', methods=['POST'])
def create_league():
    league_name = request.form['league_name']
    if league_name:
        new_league = League(name=league_name)
        db.session.add(new_league)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/delete_league/<int:league_id>', methods=['POST'])
def delete_league(league_id):
    league = League.query.get(league_id)
    if league:
        db.session.delete(league)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/add_team/<int:league_id>', methods=['POST'])
def add_team(league_id):
    league = League.query.get(league_id)
    if league and len(league.teams) < 20:
        team_name = request.form['team_name']
        new_team = Team(name=team_name, league_id=league_id)
        db.session.add(new_team)
        db.session.commit()

        league = League.query.get(league_id)
        if len(league.teams) == 20:
            generate_fixtures(league_id)
    return redirect(url_for('home', league_id=league_id))

@app.route('/update_match/<int:match_id>', methods=['POST'])
def update_match(match_id):
    match = Match.query.get(match_id)
    if match and not match.played:
        team_a_score = int(request.form['team_a_score'])
        team_b_score = int(request.form['team_b_score'])

        match.team_a_score = team_a_score
        match.team_b_score = team_b_score
        match.played = True

        team_a = Team.query.get(match.team_a_id)
        team_b = Team.query.get(match.team_b_id)

        team_a.played += 1
        team_b.played += 1

        team_a.goals_for += team_a_score
        team_a.goals_against += team_b_score
        team_b.goals_for += team_b_score
        team_b.goals_against += team_a_score

        team_a.goal_difference = team_a.goals_for - team_a.goals_against
        team_b.goal_difference = team_b.goals_for - team_b.goals_against

        if team_a_score > team_b_score:
            team_a.wins += 1
            team_b.losses += 1
            team_a.points += 3
        elif team_a_score < team_b_score:
            team_b.wins += 1
            team_a.losses += 1
            team_b.points += 3
        else:
            team_a.draws += 1
            team_b.draws += 1
            team_a.points += 1
            team_b.points += 1

        db.session.commit()
    return redirect(url_for('view_league', league_id=match.league_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)