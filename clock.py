from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Mail, Message

# Configure application
app = Flask(__name__)

# Configure CS50 Library to use SQLite database
db = SQL(os.getenv("postgres://ddbkgaxnissqhx:25074932dc176fee4fc964ef20d681f522b3bac67b747fdbc5839bd5a27f39ff@ec2-34-203-182-172.compute-1.amazonaws.com:5432/d272qc35s71bfm"))

#-----------------------------------
# Email part

# Configure mail server parameters
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'IDtoIT.CS@gmail.com'
app.config['MAIL_PASSWORD'] = 'harvardcs50'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

# Create an instance of the Mail class
mail = Mail(app)

# set configuration values
class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config())

# initialize scheduler
scheduler = APScheduler(BackgroundScheduler(timezone='Asia/Taipei'))
# if you don't wanna use a config, you can set options here:
scheduler.api_enabled = True
#scheduler.init_app(app)


db.app = app
db.init_app(app)

if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
    @scheduler.task('cron', id='notify', hour=23, minute=56, second=0)
    def notify():
        with db.app.app_context():
        	targets = db.execute("SELECT * FROM users WHERE JULIANDAY(date('now'))=(JULIANDAY(date_f)+7)")
        	if len(targets) == 0:
        		return
        	else:
        		for target in targets:
        		    if target["email"] != "NULL":
            			msg = Message('Diabetes Management System Automatic notification! ', sender = 'IDtoIT.CS@gmail.com', recipients = [target["email"]])
            			msg.body = "Hello {0} – It's time for your regualr diabetes mellitus check-up. Please schedule an appointment before {1}. See you then!".format(target["name"], target["date_f"])
            			mail.send(msg)
    scheduler.start()

#--------Email Part end---------#
