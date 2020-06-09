from aifc import Error
from flask import render_template
from flask import Flask as _Flask
from datetime import date
from flask.json import JSONEncoder as _JSONEncoder
from flask_sqlalchemy import SQLAlchemy
import traceback
import datetime
import os


# 继承_JSONEncoder重写default，每当发送有不能序列化的类型时，在这里就可以参考源码进行添加即可。
class JSONEncoder(_JSONEncoder):
    def default(self, o):
        if hasattr(o, 'keys') and hasattr(o, '__getitem__'):
            return dict(o)
        if isinstance(o, date):
            return o.strftime('%Y-%m-%d')
        raise Error()


# 重写flask，把新的JSONEncoder赋值给flask对象，这样新的才能生效
class Flask(_Flask):
    json_encoder = JSONEncoder


app = Flask(__name__)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:000000@127.0.0.1/oceans?charset=utf8'
app.config["SECRET_KEY"] = 'f00cd2a8351943b4a52573fcbb3a4c97'
app.config['JSON_AS_ASCII'] = False
app.config["FC_DIR"] = os.path.join(os.path.abspath(os.path.dirname(__file__)), "static/uploads/users/")
app.config["COMPANY_DIR"] = os.path.join(os.path.abspath(os.path.dirname(__file__)), "static/uploads/company/")
app.debug = True
db = SQLAlchemy(app)

from app.home import home as home_blueprint


app.register_blueprint(home_blueprint)


# 生产环境上打开此类配置
# 全局异常处理
# @app.errorhandler(Exception)
# def flask_global_exception_handler(e):
#     try:
#         file = './app/log/'+datetime.datetime.now().strftime("%Y-%m-%d")+'_log.txt'
#         with open(file, 'a') as f:
#             f.writelines(['\n\n\n\n'+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" 出现异常"+'\n\n'])
#         print(e)
#         traceback.print_exc(file=open(file, 'a'))
#         return render_template("home/404.html")
#     except BaseException as ex:
#         print(ex)
#         traceback.print_exc()
#         return render_template("home/404.html")
