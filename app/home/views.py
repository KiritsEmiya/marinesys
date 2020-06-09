import os
import datetime
import traceback
import uuid
from functools import wraps
from . import analysis
import requests
from typing import List
import json

from sqlalchemy import and_
from sqlalchemy import or_

import time
from pyquery import PyQuery

from app import db, app
from app.models import User, Userlog, Category, Company, News, Overview, Operations, Image, Newscol, SecondhandShip, \
    Newbuilding, ShipDemolition, TimeCharter, ShipType, Contacts
from . import home
from flask import render_template, redirect, url_for, session, request, flash, jsonify
from werkzeug.security import generate_password_hash
from .forms import RegistForm, LoginForm, UserDetailForm, PwdForm

import jieba
import jieba.analyse
import math


# 修改文件名称
def change_filename(filename):
    fileinfo = os.path.splitext(filename)
    filename = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + str(uuid.uuid4().hex) + fileinfo[-1]
    return filename


# json转数据库model
def model_format(model=None, data={}):
    for key in data.keys():
        if key in model.keys():
            if type(data[key]) == int:
                setattr(model, key, data[key])
            if type(data[key]) == str:
                setattr(model, key, data[key].strip())
    return model


# 得到Post提交的对象
def model_for_post():
    data = eval(str(request.data, encoding="utf-8").replace('null', '\"\"'))
    view_model = {}
    # 判断属性值是否为空
    for key in data:
        if type(data[key]) == int:
            view_model[key] = data[key]
        if type(data[key]) == str and data[key].strip() != '':
            view_model[key] = data[key].strip()
        if type(data[key]) == list and len(data[key]) != 0:
            for i, item in enumerate(data[key]):
                if i == 0:
                    view_model[key] = str(item)
                else:
                    view_model[key] += ',' + str(item)
    return view_model


# 登录装饰器
def user_login_req(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("home.login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


# 新闻相似度检查
class CheckNewsSimilarity(object):

    jieba.analyse.set_stop_words('./app/home/stop_words.txt')

    @classmethod
    def get_similarity(cls, doc, source):
        vectors = CheckNewsSimilarity.tf_idf(res1=CheckNewsSimilarity.cut_word(article=doc),
                                             res2=CheckNewsSimilarity.cut_word(article=source))
        # 相似度
        similarity = CheckNewsSimilarity.run(vector1=vectors[0], vector2=vectors[1])
        # 使用arccos计算弧度
        # rad = math.acos(similarity)
        return round(round(similarity, 2)*100)

    @classmethod
    def cut_word(cls, article):
        # 这里使用了TF-IDF算法，所以分词结果会有些不同->https://github.com/fxsjy/jieba#3-关键词提取
        res = jieba.analyse.extract_tags(
            sentence=article, topK=100, withWeight=True)
        # print(res)
        return res

    @classmethod
    def tf_idf(cls, res1=None, res2=None):
        # 向量，可以使用list表示
        vector_1 = []
        vector_2 = []
        # 词频，可以使用dict表示
        tf_1 = {i[0]: i[1] for i in res1}
        tf_2 = {i[0]: i[1] for i in res2}
        res = set(list(tf_1.keys()) + list(tf_2.keys()))

        # 填充词频向量
        for word in res:
            if word in tf_1:
                vector_1.append(tf_1[word])
            else:
                vector_1.append(0)
            if word in tf_2:
                vector_2.append(tf_2[word])
            else:
                vector_2.append(0)
        # print(vector_1)
        # print(vector_2)
        return vector_1, vector_2

    @classmethod
    def numerator(cls, vector1, vector2):
        # 分子
        return sum(a * b for a, b in zip(vector1, vector2))

    @classmethod
    def denominator(cls, vector):
        # 分母
        return math.sqrt(sum(a * b for a, b in zip(vector, vector)))

    @classmethod
    def run(cls, vector1, vector2):
        return CheckNewsSimilarity.numerator(
            vector1, vector2) / (CheckNewsSimilarity.denominator(vector1) * CheckNewsSimilarity.denominator(vector2))


# 用户登录
@home.route("/login/", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        data = form.data
        user = User.query.filter_by(name=data["name"]).first()
        if user:
            if not user.check_pwd(data["pwd"]):
                flash("密码错误！", "err")
                return redirect(url_for("home.login"))
        else:
            flash("账号不存在！", "err")
            return redirect(url_for("home.login"))
        session["user"] = user.name
        session["user_id"] = user.id
        userlog = Userlog(
            user_id=user.id,
            ip=request.remote_addr
        )
        db.session.add(userlog)
        db.session.commit()
        next_url = request.args.get("next", "")
        if next_url != "" and next_url is not None:
            return redirect(next_url)
        return redirect(url_for("home.index"))
    return render_template("home/login.html", form=form)


# 初始化实时新闻列表
@home.route("/default_hourly_news/", methods=["GET", "POST"])
def default_hourly_news():
    if request.method == 'POST':
        para = eval(str(request.data, encoding="utf-8").replace('null', '\"\"'))
        abbr = Company.query.filter_by(id=para['id']).first().abbr
        print(para)
        print(abbr)
        hourly_news_list = []
        for keyword in para['keyword'].split(','):
            hourly_news_list.extend(analysis.NewsByBaidu.analysis_html(abbr, keyword, para['id']))
        # 添加谷歌新闻源，
        # for keyword in para['keyword']:
        #     hourly_news_list.extend(analysis.NewsByGoogle.analysis_html(abbr, keyword, para['id']))
        # print(len(hourly_news_list))
    return jsonify(hourly_news_list)


# 按分类搜索新闻
@home.route("/news_by_category/", methods=["GET", "POST"])
def news_by_category():
    if request.method == 'POST':
        para = eval(str(request.data, encoding="utf-8").replace('null', '\"\"'))
        category_id = para['category_id']
    news_list = News.query.filter(News.category == category_id).all()
    return jsonify(news_list)


# 谷歌系统新闻搜索
@home.route("/news_by_google/")
def news_by_google():
    key = request.args.get("key", "")
    print('google: '+key)
    company_id = request.args.get("id", 0)
    abbr = Company.query.filter_by(id=company_id).first().abbr
    if company_id is None:
        company_id = 0
    '''
    overviews: List[Overview] = []
    for overview in analysis.NewsByGoogle.analysis_html('cosco'):
        overviews.append(Overview(id=overview['id'], title=overview['title'], profile=overview['profile'],
                                  keyword=overview['keyword'], url=overview['url'], date=overview['date'],
                                  status=overview['status'], source=overview['source'],))
    print(overviews[0])
    db.session.add_all(overviews)
    db.session.commit()
    '''
    return jsonify(analysis.NewsByGoogle.analysis_html(abbr, key, company_id))


# 百度新闻搜索
@home.route("/news_by_baidu/")
def news_by_baidu():
    key = request.args.get("key", "")
    print('baidu: '+key)
    company_id = request.args.get("id", 0)
    abbr = Company.query.filter_by(id=company_id).first().abbr
    if company_id is None:
        company_id = 0
    return jsonify(analysis.NewsByBaidu.analysis_html(abbr, key, company_id))


# 系统新闻搜索
@home.route("/news_by_system/")
def news_by_system():
    key = request.args.get("key", "")
    print('system: '+key)
    news: List[News] = News.query.filter(
        News.keyword.ilike('%' + key + '%')
    ).order_by(
        News.date.desc()
    ).all()
    return jsonify(news)


# 新闻概览分页列表
@home.route("/overview_by_system/paging", methods=["GET", "POST"])
@user_login_req
def overview_paging():
    view_model = model_for_post()
    page_index = view_model['page_index']
    page_size = view_model['page_size']
    result = db.session.query(
        Overview, Company.name
    ).filter(
        Company.id == Overview.company_id
    ).order_by(
        Overview.id.asc()
    ).limit(
        page_size
    ).offset(
        (page_index - 1) * page_size
    )
    overviews = []
    for item, name in result:
        temp = item.to_dict()
        temp['company'] = name
        overviews.append(temp)
    return jsonify(overviews)


# 新闻概览列表
@home.route("/overview_by_system/")
@user_login_req
def overview_by_system():
    overview_count = Overview.query.count()
    total_page = int((overview_count + 30 - 1) / 30)
    result = db.session.query(
        Overview, Company.name
    ).filter(
        Company.id == Overview.company_id
    ).order_by(
        Overview.id.asc()
    ).limit(30)
    overviews = []
    for item, name in result:
        temp = item.to_dict()
        temp['company'] = name
        overviews.append(temp)
    return jsonify({'total_page': total_page, 'overviews': overviews})


# 退出登录
@home.route("/logout/")
@user_login_req
def logout():
    session.pop("user", None)
    session.pop("user_id", None)
    return redirect(url_for("home.login"))


# 用户注册
@home.route("/register/", methods=["GET", "POST"])
def register():
    form = RegistForm()
    if form.validate_on_submit():
        data = form.data
        user = User(
            name=data["name"],
            email=data["email"],
            phone=data["phone"],
            pwd=generate_password_hash(data["pwd"]),
            uuid=uuid.uuid4().hex
        )
        db.session.add(user)
        db.session.commit()
        flash("注册成功！请登录", "ok")
        return redirect(url_for("home.login"))
    else:
        return render_template("home/register.html", form=form)


# 删除新闻图片
@home.route("/news/image/delete/")
@user_login_req
def news_image_delete():
    img_name = request.args.get("img_name", "")
    if 'static' in img_name:
        if os.path.exists('./app/static'+img_name.split('static')[1]):
            os.remove('./app/static'+img_name.split('static')[1])
            return jsonify('删除图片成功!')
        else:
            return jsonify('图片不存在!')
    else:
        return jsonify('非本地图片!')


# 删除企业图片
@home.route("/company/image/delete/", methods=["GET", "POST"])
@user_login_req
def company_image_delete():
    if request.method == 'POST':
        image_list = eval(str(request.data, encoding="utf-8").replace('null', '\"\"'))
        opt_image_list = []
        for item in image_list:
            if item['news_id'] == '':
                print('news_id为空,满足删除条件')
                opt_image_list.append(item)
                # 从文件目录删除
                if 'static' in item['url']:
                    if os.path.exists('./app/static'+item['url'].split('static')[1]):
                        os.remove('./app/static'+item['url'].split('static')[1])
            # 从数据库删除
                db.session.delete(Image.query.filter_by(id=item['id']).first())
                db.session.commit()
    if len(image_list) == len(opt_image_list):
        return jsonify({'status': 'ok', 'info': '图片删除成功!'})
    if len(image_list) > len(opt_image_list) > 0:
        return jsonify({'status': 'part', 'info': '部分图片关联新闻，无法删除!'})
    if len(opt_image_list) == 0:
        return jsonify({'status': 'error', 'info': '所选图片关联新闻，无法删除!'})


# 重复企业图片合并
@home.route("/company/image/merge/", methods=["GET", "POST"])
@user_login_req
def company_image_merge():
    try:
        if request.method == 'POST':
            image_list = eval(str(request.data, encoding="utf-8").replace('null', '\"\"'))
            news_image_opt_list = []
            source_image = image_list[0]        # 替换后的源图片
            source_image_url = '../../../static'+source_image['url'].split('static')[1]        # 替换后的源图片url
            for item in image_list:
                if item['news_id'] != '':
                    news_image_opt_list.append(item)
                if 'static' in item['url'] and source_image['id'] != item['id']:
                    if os.path.exists('./app/static' + item['url'].split('static')[1]):
                        os.remove('./app/static' + item['url'].split('static')[1])      # 删除删除本地图片资源
                    db.session.delete(Image.query.filter_by(id=item['id']).first())     # 删除图片表数据
                    db.session.commit()
            if len(news_image_opt_list) != 0:
                news_list = News.query.filter(News.company_id == item['company_id']).order_by(News.date.desc()).all()
                if len(news_list) != 0:
                    for news in news_list:
                        for image in news_image_opt_list:
                            if image['url'] in news.content:
                                print(image['url'])
                                db.session.query(News).filter(News.id == news.id).update({
                                    'content': news.content.replace(image['url'], source_image_url)})
                                db.session.commit()
                db.session.query(Image).filter(Image.id == Image.id).update({
                    'news_id': news_image_opt_list[0]['news_id']})
                db.session.commit()
        return jsonify({'status': 'ok', 'info': '图片合并成功!'})
    except BaseException as ex:
        print(ex)
        traceback.print_exc()
        return jsonify({'status': 'error', 'info': '遇到未知错误，无法删除!'})


# 获取企业所有图片
@home.route("/company/image/list")
@user_login_req
def company_image_list():
    company_id = request.args.get("company_id", 0)
    image_list = Image.query.filter_by(company_id=company_id).order_by(Image.time.desc()).all()
    return jsonify(image_list)


# 获取分类下所有图片
@home.route("/category/image/list")
@user_login_req
def category_image_list():
    category_id = request.args.get("category_id", 0)
    image_list = Image.query.filter_by(category_id=category_id).order_by(Image.time.desc()).all()
    return jsonify(image_list)


# 获取与该关键词有关的所有图片
@home.route("/keyword/image/list", methods=["GET", "POST"])
@user_login_req
def keyword_image_list():
    if request.method == 'POST':
        para = eval(str(request.data, encoding="utf-8").replace('null', '\"\"'))
        image_list = Image.query.filter(
            Image.keyword.ilike('%' + para['keyword'] + '%')
        ).filter(
            Image.company_id == para['company_id']
        ).order_by(Image.time.desc()).all()
        return jsonify(image_list)
    keyword = request.args.get("keyword", "").lower()
    image_list = Image.query.filter(Image.keyword.ilike('%' + keyword + '%')).order_by(Image.time.desc()).all()
    return jsonify(image_list)


# 上传新闻图片 type 1: 新增新闻页面、定时新闻页面  2: 编辑新闻页面  3: 企业新闻添加
@home.route("/news/image/<int:type>/", methods=["GET", "POST"])
@user_login_req
def news_image(type=None):
    if request.method == 'POST':
        image = request.files['imageData']
        print(image.filename)
        news_image_dir = "./app/static/uploads/news/"+time.strftime('%Y-%m', time.localtime(time.time()))+"/"
        if not os.path.exists(news_image_dir):
            os.makedirs(news_image_dir)
        logo = change_filename(str(image.filename))
        image.save(news_image_dir+logo)
        if int(type) == 1:
            return jsonify({'img': news_image_dir.replace('./app/', '../../../')+logo})
        if int(type) == 2:
            return jsonify({'img': news_image_dir.replace('./app/', '../../../../')+logo})
        if int(type) == 3:
            return jsonify({'img': news_image_dir.replace('./app/', '../../../../../')+logo})
        else:
            return jsonify('error')


# 上传企业LOGO
@home.route("/company_logo", methods=["GET", "POST"])
@user_login_req
def company_logo():
    if request.method == 'POST':
        image = request.files['file']
        # print(image.filename)
        if not os.path.exists(app.config["COMPANY_DIR"]):
            os.makedirs(app.config["COMPANY_DIR"])
            os.chmod(app.config["COMPANY_DIR"], "rw")
        logo = change_filename(str(image.filename))
        image.save(app.config["COMPANY_DIR"] + logo)
        # print('../../static/uploads/company/' + logo)
        return jsonify({'img': '../../static/uploads/company/' + logo})


# 用户中心
@home.route("/user/", methods=["GET", "POST"])
@user_login_req
def user():
    form = UserDetailForm()
    user = User.query.get(int(session["user_id"]))
    # 关闭验证
    form.face.validators.clear()
    form.info.validators.clear()
    if request.method == "GET":
        form.name.data = user.name
        form.email.data = user.email
        form.phone.data = user.phone
        form.info.data = user.info
    if form.validate_on_submit():
        data = form.data
        if form.face.data.filename != "":
            # file_face = secure_filename(form.face.data.filename)
            file_face = form.face.data.filename
            if not os.path.exists(app.config["FC_DIR"]):
                os.makedirs(app.config["FC_DIR"])
                os.chmod(app.config["FC_DIR"])
            user.face = change_filename(file_face)
            form.face.data.save(app.config["FC_DIR"] + user.face)
        name_count = User.query.filter_by(name=data["name"]).count()
        if data["name"] != user.name and name_count == 1:
            flash("昵称已经存在!", "err")
            return redirect(url_for("home.user"))
        email_count = User.query.filter_by(email=data["email"]).count()
        if data["email"] != user.email and email_count == 1:
            flash("邮箱已经存在!", "err")
            return redirect(url_for("home.user"))
        phone_count = User.query.filter_by(phone=data["phone"]).count()
        if data["phone"] != user.phone and phone_count == 1:
            flash("手机已经存在!", "err")
            return redirect(url_for("home.user"))
        user.name = data["name"]
        user.email = data["email"]
        user.phone = data["phone"]
        user.info = data["info"]
        db.session.add(user)
        db.session.commit()
        flash("修改成功!", "ok")
        return redirect(url_for("home.user"))
    return render_template("home/user.html", form=form, user=user)


# 修改密码
@home.route("/pwd/", methods=["GET", "POST"])
@user_login_req
def pwd():
    form = PwdForm()
    if form.validate_on_submit():
        data = form.data
        user = User.query.filter_by(name=session["user"]).first()
        if not user.check_pwd(data["old_pwd"]):
            flash("旧密码错误！", "err")
            return redirect(url_for('home.pwd'))
        user.pwd = generate_password_hash(data["new_pwd"])
        db.session.add(user)
        db.session.commit()
        flash("修改密码成功，请重新登录！", "ok")
        return redirect(url_for('home.logout'))
    return render_template("home/pwd.html", form=form)


# 用户操作记录
@home.route("/operations/<int:page>/")
@user_login_req
def operations(page=None):
    if page is None:
        page = 1
    page_data = Operations.query.join(
        User
    ).filter(
        User.id == session["user_id"]
    ).order_by(
        Operations.addtime.desc()
    ).paginate(page=page, per_page=7)
    return render_template("home/operations.html", page_data=page_data)


# 添加用户操作记录
@home.route("/operations/add/", methods=["GET", "POST"])
@user_login_req
def operations_add():
    judge = lambda x, y: str(x[y]).strip() if y in x.keys() and str(x[y]).strip() != '' else None
    if request.method == 'POST':
        data = eval(str(request.data, encoding="utf-8").replace('null', '\"\"'))
        operation = Operations(
            user_id=int(session["user_id"]),
            action=judge(data, 'action'),
            content=judge(data, 'content'),
            annotation=judge(data, 'annotation')
        )
        db.session.add(operation)
        db.session.commit()
    return jsonify("ok")


# 用户登录日志
@home.route("/loginlog/<int:page>/", methods=["GET"])
@user_login_req
def loginlog(page=None):
    if page is None:
        page = 1
    page_data = Userlog.query.filter_by(
        user_id=int(session["user_id"])
    ).order_by(
        Userlog.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template("home/loginlog.html", page_data=page_data)


# 用户收藏列表
@home.route("/collect/<int:page>/", methods=["GET", "POST"])
@user_login_req
def collect(page=None):
    if page is None:
        page = 1
    page_data = Newscol.query.join(
        News
    ).join(
        User
    ).filter(
        News.id == Newscol.news_id,
        User.id == session["user_id"]
    ).order_by(
        Newscol.addtime.desc()
    ).paginate(page=page, per_page=5)
    return render_template("home/collect.html", page_data=page_data)


# 添加新闻收藏
@home.route("/collect/add/", methods=["GET"])
@user_login_req
def collect_add():
    user_id = int(session["user_id"])
    news_id = request.args.get("id", 0)
    news_col_count = Newscol.query.filter_by(
        user_id=user_id,
        news_id=news_id
    ).count()
    # 已收藏
    if news_col_count == 1:
        return jsonify({'status': 'repeat', 'info': '已收藏该新闻,请勿重复收藏!'})
    # 未收藏进行收藏
    if news_col_count == 0:
        news_col = Newscol(
            user_id=user_id,
            news_id=news_id
        )
        db.session.add(news_col)
        db.session.commit()
        return jsonify({'status': 'ok', 'info': '新闻收藏成功!'})


# 取消新闻收藏
@home.route("/collect/delete/", methods=["GET"])
@user_login_req
def collect_delete():
    collect_id = request.args.get("id", 0)
    print(collect_id)
    news_col = Newscol.query.filter_by(id=collect_id).first()
    if news_col:
        db.session.delete(news_col)  # 删除新闻收藏表数据
        db.session.commit()
    page_data = Newscol.query.join(
        News
    ).join(
        User
    ).filter(
        News.id == Newscol.news_id,
        User.id == session["user_id"]
    ).order_by(
        Newscol.addtime.desc()
    ).paginate(page=1, per_page=5)
    # flash("取消收藏成功！", "ok")
    return render_template("home/collect.html", page_data=page_data)


# 首页
@home.route("/")
def index():
    categories = Category.query.all()
    category = []
    for a in range(0, 6):
        category.append(categories[a])
    return render_template("home/index.html", categories=categories, category=category)


# 新闻概览详情
@home.route("/overview/detail/<int:id>/")
@user_login_req
def overview_get_detail(id=None):
    overview = Overview.query.filter_by(id=id).first()
    company_name = Company.query.filter_by(id=overview.company_id).first().name
    print('overview')
    return jsonify({'overview': overview, 'companyName': company_name})


# 关联新闻列表
@home.route("/news/similar/list/")
@user_login_req
def news_similar_list():
    key = request.args.get("key", "")
    print(key)
    result = db.session.execute(
        "SELECT id,title,date FROM news WHERE keyword LIKE '%" + key + "%' ORDER BY date DESC"
    ).fetchall()
    db.session.commit()
    news_list_all = [dict(zip(item.keys(), item)) for item in result]
    print('关联新闻长度:'+str(len(news_list_all)))
    return jsonify('ok')


# 企业定时新闻页面
@home.route("/news/timed/view/")
@user_login_req
def news_timed_view():
    return render_template("home/news_timed_view.html")


# 修改新闻页面
@home.route("/news/edit/view/")
@user_login_req
def news_edit_view():
    id = request.args.get("id", "")
    news = News.query.filter_by(id=id).first()
    company_name = Company.query.filter_by(id=news.company_id).first().name
    return render_template("home/news_edit_view.html", id=id, company_name=company_name)


# 新闻图片下载替换
@user_login_req
def news_image_download(content):
    if content is None:
        return None
    else:
        doc = PyQuery(content)
        for item in doc('img').items():
            if '/static/uploads/news/' in item.attr('src'):
                content = content.replace(item.attr('src'), '../../../static'+item.attr('src').split('static')[1])
                continue
            else:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " +
                                  "Chrome/54.0.2840.99 Safari/537.36"}
                # params 接收一个字典或者字符串的查询参数，字典类型自动转换为url编码，不需要urlencode()
                response = requests.get(item.attr('src'), headers=headers, stream=True)
                if response.status_code == 200:
                    news_image_dir = "./app/static/uploads/news/" + \
                                     time.strftime('%Y-%m', time.localtime(time.time())) + "/"
                    if not os.path.exists(news_image_dir):
                        os.makedirs(news_image_dir)
                    logo = change_filename(item.attr('src'))
                    with open(news_image_dir+logo, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024):  # 历遍请求下载回来的图片
                            if chunk:  # 如果chunk不等于0
                                f.write(chunk)
                                f.flush()  # 刷新缓冲区
                    content = content.replace(item.attr('src'), news_image_dir.replace('./app/', '../../../')+logo)
                    print('已下载至本地并替换')
        return content


# 新闻关联图片
@user_login_req
def news_relate_image(news):
    if news.content is None:
        return None
    else:
        doc = PyQuery(news.content)
        news_inner_image_list: List[Image] = []
        for item in doc('img').items():
            news_inner_image_list.append(Image(id=None, url=item.attr('src'), keyword=news.keyword,
                                               company_id=news.company_id, news_id=news.id,
                                               category_id=news.category))
        if len(news_inner_image_list) > 0:
            db.session.add_all(news_inner_image_list)
            db.session.commit()
            print('此新闻有'+str(len(news_inner_image_list))+'张图片, 已保存'+str(len(news_inner_image_list))+'张图片')
        else:
            print('此新闻无图片')
            return None


# 上传企业相关图片
@user_login_req
@home.route("/upload/company/image/", methods=["GET", "POST"])
def upload_company_image():
    if request.method == 'POST':
        image = request.files['file']
        # print(image.filename)     # 原图片名称
        news_image_dir = "./app/static/uploads/news/"+time.strftime('%Y-%m', time.localtime(time.time()))+"/"
        if not os.path.exists(news_image_dir):
            os.makedirs(news_image_dir)
        logo = change_filename(str(image.filename))
        image.save(news_image_dir+logo)
        return jsonify({'img': news_image_dir.replace('./app/', '../../../') + logo})


# 添加企业图片到数据库
@user_login_req
@home.route("/add/company/image/", methods=["GET", "POST"])
def add_company_image():
    if request.method == 'POST':
        judge = lambda x, y: str(x[y]).strip() if y in x.keys() and str(x[y]).strip() != '' else None
        data = eval(str(request.data, encoding="utf-8").replace('null', '\"\"'))
        print(data)
        image = Image(id=None, url=judge(data, 'url'), keyword=judge(data, 'keyword'),
                      company_id=judge(data, 'company_id'), news_id=judge(data, 'news_id'),
                      category_id=judge(data, 'category_id'))
        db.session.add(image)
        db.session.commit()
        print('上传关键词为"'+data['keyword'][0]+'"的图片成功')
        return jsonify({'status': 'ok', 'info': '图片上传成功!'})


# 修改企业图片到数据库
@user_login_req
@home.route("/edit/company/image/", methods=["GET", "POST"])
def edit_company_image():
    if request.method == 'POST':
        judge = lambda x, y: str(x[y]).strip() if y in x.keys() and str(x[y]).strip() != '' else None
        data = eval(str(request.data, encoding="utf-8").replace('null', '\"\"'))
        # print(data)
        # print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))

        # 关键词数组转化成字符串
        keyword = None
        if judge(data, 'keyword') is not None and len(eval(judge(data, 'keyword'))) != 0:
            for i, key in enumerate(eval(judge(data, 'keyword'))):
                if i == 0:
                    keyword = key
                else:
                    keyword += ',' + key
        db.session.query(Image).filter(Image.id == int(judge(data, 'id'))).update({
            'keyword': keyword, 'url': judge(data, 'url'), 'category_id': judge(data, 'category_id'),
            'time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))})
        db.session.commit()
        print('修改id为'+str(data['id'])+'的图片成功')
        return jsonify({'status': 'ok', 'info': '图片修改成功!'})


# 新增新闻
@home.route("/news/add/", methods=["GET", "POST"])
@user_login_req
def news_add():
    try:
        judge = lambda x, y: str(x[y]).strip() if y in x.keys() and str(x[y]).strip() != '' else None
        if request.method == 'POST':
            data = eval(str(request.data, encoding="utf-8").replace('null', '\"\"'))
            print(type(judge(data, 'category')))
            if judge(data, 'title') is None or judge(data, 'profile') is None or \
                    judge(data, 'date') is None or judge(data, 'content') is None or \
                    judge(data, 'effect') is None or judge(data, 'category') is None or \
                    judge(data, 'company') is None or judge(data, 'keyword') is None:
                return jsonify("error")
            if int(judge(data, 'company')) == 0:
                return jsonify({'status': 'no'})

            doc = PyQuery(judge(data, 'content')).text().replace('\n', '')
            all_news = News.query.filter(
                News.keyword.ilike('%' + judge(data, 'keyword')[0] + '%')
            ).order_by(
                News.date.desc()
            ).all()
            similar_news_list = []
            for item in all_news:
                if judge(data, 'id') is not None and int(judge(data, 'id')) == item.id:
                    # print('存在id:'+str(item.id))
                    continue
                res = CheckNewsSimilarity.get_similarity(doc, PyQuery(item.content).text().replace('\n', ''))
                # 新闻相似度

                # print('相似id:'+str(item.id))
                # if res > 70:
                if res > 200:
                    similar_news_list.append({'id': item.id, 'title': item.title,
                                              'date': item.date, 'similar': str(res)+'%'})

            # 关键词数组转化成字符串
            keyword = None
            if judge(data, 'keyword') is not None and len(eval(judge(data, 'keyword'))) != 0:
                for i, key in enumerate(eval(judge(data, 'keyword'))):
                    if i == 0:
                        keyword = key
                    else:
                        keyword += ',' + key
            # 添加新闻
            if judge(data, 'id') is None:
                if len(similar_news_list) > 0:
                    return jsonify({'status': 'repeat', 'similar_news_list': similar_news_list})
                news = News(title=judge(data, 'title'), profile=judge(data, 'profile'),
                            date=judge(data, 'date'), effect=judge(data, 'effect'),
                            category=judge(data, 'category'), company_id=judge(data, 'company'),
                            content=news_image_download(judge(data, 'content')), keyword=keyword)
                db.session.add(news)
                db.session.commit()
                print('添加新闻"'+data['title']+'"成功')
                news_relate_image(news)
            # 修改新闻
            else:
                if len(similar_news_list) > 0:
                    return jsonify({'status': 'repeat', 'similar_news_list': similar_news_list})
                db.session.query(News).filter(News.id == int(judge(data, 'id'))).update({
                    'title': judge(data, 'title'), 'profile': judge(data, 'profile'),
                    'date': judge(data, 'date'), 'effect': judge(data, 'effect'),
                    'category': judge(data, 'category'), 'company_id': judge(data, 'company'),
                    'content': news_image_download(judge(data, 'content')), 'keyword': keyword})
                db.session.commit()
                print('修改新闻"'+data['title']+'"成功')
            return jsonify({'status': 'ok'})
    except BaseException as ex:
        print(ex)
        traceback.print_exc()
        return jsonify({'status': 'error'})


# 删除新闻
@home.route("/news/delete/<int:id>/", methods=["GET", "POST"])
@user_login_req
def news_delete(id=None):
    if id is None:
        return jsonify({'status': 'error', 'info': '此新闻不存在!'})
    try:
        news = News.query.filter_by(id=id).first()
        if news:
            doc = PyQuery(news.content)
            for item in doc('img').items():
                image_url = item.attr('src').split('static')[1]

                image = Image.query.filter(Image.url.ilike('%' + image_url + '%')).first()
                if image:
                    db.session.delete(image)     # 删除图片表数据
                    db.session.commit()
                if os.path.exists('./app/static' + image_url):
                    os.remove('./app/static' + image_url)      # 删除删除本地图片资源
            db.session.delete(News.query.filter_by(id=id).first())  # 删除新闻表数据
            db.session.commit()
            return jsonify({'status': 'ok', 'info': '成功删除此新闻!'})
        else:
            return jsonify({'status': 'none', 'info': '此新闻不存在!'})
    except BaseException as ex:
        print(ex)
        traceback.print_exc()
        return jsonify({'status': 'error', 'info': '出现未知错误,请刷新重试!'})


# 新闻详情
@home.route("/news/details/view/")
def news_details_view():
    id = request.args.get("id", 1)
    print(id)
    return render_template("home/news_details_view.html", id=id)


# 获取新闻内容
@home.route("/news/details/<int:id>/")
def news_details(id=None):
    if id is None:
        id = 1
    news_detail = News.query.filter_by(id=id).first()
    return jsonify(news_detail)


# 查询所有新闻 id、日期、标题
@home.route("/news/get/all/", methods=["GET", "POST"])
def news_get_all():
    news_count = News.query.count()
    total_page = int((news_count + 30 - 1) / 30)
    result = db.session.query(News).order_by(News.id.asc()).limit(30)
    news_list_all = [item.to_dict() for item in result]
    print('获取所有新闻,共'+str(news_count)+'条,'+'共'+str(total_page)+'页')
    return jsonify({'total_page': total_page, 'news_list_all': news_list_all})


# 分页查询新闻
@home.route("/news/list/paging", methods=["GET", "POST"])
def news_list_paging():
    view_model = model_for_post()
    page_index = view_model['page_index']
    page_size = view_model['page_size']
    result = db.session.query(News).order_by(
        News.id.asc()
    ).limit(
        page_size
    ).offset(
        (page_index - 1) * page_size
    )
    news_list_all = [item.to_dict() for item in result]
    print(len(news_list_all))
    return jsonify(news_list_all)


# 通过标题模糊查找新闻,返回 id、日期、标题
@home.route("/get_news_by_title", methods=["GET", "POST"])
@user_login_req
def get_news_by_title():
    view_model = model_for_post()
    key = ''
    news_category_id = ''
    news_date = ''
    print(view_model)
    if 'key' in view_model.keys():
        key = str(view_model['key'])
    if 'news_category_id' in view_model.keys():
        news_category_id = str(view_model['news_category_id'])
        print(news_category_id)
    if 'news_date' in view_model.keys():
        news_date = str(view_model['news_date'])
        if news_date != '':
            news_date = str(datetime.date.today() - datetime.timedelta(days=int(news_date)))
            print('查找日期是: '+news_date+' 以后的数据')
    result = News.query.filter(
        or_(
            News.title.ilike('%' + key + '%'),
            News.profile.ilike('%' + key + '%'),
            News.keyword.ilike('%' + key + '%')
        )
    ).filter(
        News.category.ilike('%' + news_category_id + '%')
    ).filter(
        News.date >= news_date
    ).order_by(
        News.date.desc()
    ).all()
    print(len(result))
    return jsonify(result)


# 通过企业id查找新闻,返回 id、日期、标题
@home.route("/select/news/by_company_id")
@user_login_req
def get_news_by_company_id():
    company_id = request.args.get("company_id", "")
    result = db.session.execute(
        "SELECT id,title,date FROM news WHERE company_id = :company_id ORDER BY date DESC", {'company_id': company_id}
    ).fetchall()
    db.session.commit()
    news_list_all = [dict(zip(item.keys(), item)) for item in result]
    return jsonify(news_list_all)


# 新闻状态修改
@home.route("/news/status/change/<int:id>/", methods=["GET", "POST"])
@user_login_req
def news_status_change(id=None):
    db.session.query(Overview).filter(Overview.id == id).update({'status': 1})
    db.session.commit()
    return jsonify("ok")

'''
# 查找所有企业
@home.route("/get_all_companies/")
@user_login_req
def get_all_companies():
    all = Company.query.order_by(Company.id.desc()).all()
    companies = [all[0], all[1], all[567], all[4], all[6], all[8], all[9],
                 all[34], all[45], all[67], all[41], all[61], all[81], all[91],
                 all[12], all[45], all[989], all[755], all[345], all[678], all[len(all)-1]]
    print("查找所有企业")
    return jsonify(companies)
'''

# 查找所有企业,返回id及名称
@home.route("/get_all_companies/")
@user_login_req
def get_all_companies():
    company_count = Company.query.count()
    total_page = int((company_count + 30 - 1) / 30)
    result = db.session.query(Company).order_by(Company.id.asc()).limit(30)
    companies = [item.to_dict() for item in result]
    print('查找所有企业,共'+str(company_count)+'家,'+'共'+str(total_page)+'页')
    return jsonify({'total_page': total_page, 'companies': companies})


# 分页查询企业数据
@home.route("/company/list/paging", methods=["GET", "POST"])
@user_login_req
def company_list_paging():
    view_model = model_for_post()
    page_index = view_model['page_index']
    page_size = view_model['page_size']
    result = db.session.query(Company).order_by(
        Company.id.asc()
    ).limit(
        page_size
    ).offset(
        (page_index - 1) * page_size
    )
    companies = [item.to_dict() for item in result]
    print(len(companies))
    return jsonify(companies)


# 通过名称模糊查找企业,返回id及名称
@home.route("/get_companies_by_name", methods=["GET", "POST"])
@user_login_req
def get_companies_by_name():
    view_model = model_for_post()
    key = ''
    company_category_id = ''
    company_add_time = ''
    if 'key' in view_model.keys():
        key = str(view_model['key'])
    if 'company_category_id' in view_model.keys():
        company_category_id = str(view_model['company_category_id'])
    if 'company_add_time' in view_model.keys():
        company_add_time = str(view_model['company_add_time'])
        if company_add_time != '':
            company_add_time = str(datetime.date.today() - datetime.timedelta(days=int(company_add_time)))
            print('查找日期是: '+company_add_time+' 以后的数据')
    result = Company.query.filter(
        or_(
            Company.name.ilike('%' + key + '%'),
            Company.chs_name.ilike('%' + key + '%'),
            Company.profile.ilike('%' + key + '%'),
            Company.abbr.ilike('%' + key + '%'),
            Company.keyword.ilike('%' + key + '%')
        )
    ).filter(
        Company.category_id.ilike('%' + company_category_id + '%')
    ).filter(
        Company.add_time >= company_add_time
    ).order_by(
        Company.add_time.desc()
    ).all()
    return jsonify(result)


# 查找所有企业,返回id及名称
@home.route("/all_companies_name/")
@user_login_req
def all_companies_name():
    result = db.session.execute(
        "SELECT id,name,found_time FROM company"
    ).fetchall()
    db.session.commit()
    companies = [dict(zip(item.keys(), item)) for item in result]
    print('查找所有的企业,共'+str(len(companies))+'家')
    return jsonify(companies)


# 企业详情
@home.route("/company/details/<int:id>/")
def company_details(id=None):
    if id is None:
        id = 1
    details = Company.query.filter_by(id=id).first()
    return jsonify(details)


# 企业新闻更新页面
@home.route("/company_news_update/view/<int:id>/")
@user_login_req
def company_news_update_view(id=None):
    print('企业新闻更新页面,企业ID: '+str(id))
    details = Company.query.filter_by(id=id).first()
    company = {'id': id, 'name': details.name, 'keyword': details.keyword}
    return render_template("home/company_news_update.html", company=company)


# 新增/编辑企业
@home.route("/company/add/", methods=["GET", "POST"])
@user_login_req
def company_add():
    try:
        judge = lambda x, y: str(x[y]).strip() if y in x.keys() and str(x[y]).strip() != '' else None
        if request.method == 'POST':
            data = eval(str(request.data, encoding="utf-8").replace('null', '\"\"'))
            if judge(data, 'name') is None:
                return jsonify({'status': 'err', 'op': 'add', 'info': '请输入企业名称!'})
            # 添加企业
            category_id = None
            keyword = None
            if judge(data, 'keyword') is not None and len(eval(judge(data, 'keyword'))) != 0:
                for i, key in enumerate(eval(judge(data, 'keyword'))):
                    if i == 0:
                        keyword = key
                    else:
                        keyword += ',' + key
            if judge(data, 'category_id') is not None and len(eval(judge(data, 'category_id'))) != 0:
                for i, item in enumerate(eval(judge(data, 'category_id'))):
                    if i == 0:
                        category_id = str(item)
                    else:
                        category_id += ',' + str(item)
            if judge(data, 'id') is None:
                company = Company(id=None, name=judge(data, 'name'), logo=judge(data, 'logo'),
                                  chs_name=judge(data, 'chs_name'), abbr=judge(data, 'abbr'),
                                  website=judge(data, 'website'), profile=judge(data, 'profile'),
                                  email=judge(data, 'email'), category_id=category_id, address=judge(data, 'address'),
                                  keyword=keyword, found_time=judge(data, 'found_time'),
                                  add_time=datetime.datetime.now().strftime('%Y-%m-%d'),
                                  telephone=judge(data, 'telephone'), facsimile=judge(data, 'facsimile'))
                db.session.add(company)
                db.session.commit()
                print('成功添加企业"'+company.name+'"至数据库')
                # print(data)
                return jsonify({'status': 'ok', 'op': 'add',  'company': company, 'info': '新增二手船数据成功!'})
            # 修改企业
            else:
                db.session.query(Company).filter(Company.id == int(judge(data, 'id'))).update({
                    'name': judge(data, 'name'), 'chs_name': judge(data, 'chs_name'),
                    'abbr': judge(data, 'abbr'), 'logo': judge(data, 'logo'),
                    'website': judge(data, 'website'), 'profile': judge(data, 'profile'),
                    'email': judge(data, 'email'), 'address': judge(data, 'address'),
                    'telephone': judge(data, 'telephone'), 'keyword': keyword,
                    'facsimile': judge(data, 'facsimile'), 'category_id': category_id,
                    'update_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'found_time': judge(data, 'found_time'), 'add_time': judge(data, 'add_time')})
                db.session.commit()
                print('成功修改企业"'+data['name']+'"至数据库')
                # print(data)
                return jsonify({'status': 'ok', 'op': 'edit', 'info': '修改二手船数据成功!'})
    except BaseException as ex:
        print(ex)
        traceback.print_exc()
        return jsonify("error")


# 删除企业
@home.route("/company/delete/<int:id>/", methods=["GET", "POST"])
@user_login_req
def company_delete(id=None):
    model = Company.query.filter_by(id=id).first()
    if model:
        # 删除企业下通讯录(逻辑删除)
        db.session.query(Contacts).filter(Contacts.current_company == model.id).update({Contacts.current_company: ''})
        # 删除企业
        db.session.delete(model)
        db.session.commit()
        return jsonify('ok')
    return jsonify('err')


'''
# 批量更新
@home.route("/update_companies", methods=["GET", "POST"])
def update_company():
    db.session.query(Company).filter(Company.add_time == None).update({Company.add_time: "2020-03-02"})
    db.session.commit()
    return jsonify("ok")
    

@home.route("/update_companies/")
def update_companies():

    for v in range(4, 38):
        print(v)

        db.session.execute(
            "UPDATE company SET category_id=REPLACE(category_id, '"+str(v)+"', '1000"+str(v)+"') WHERE category_id = '"+str(v)+"'"
        )
        db.session.commit()
        time.sleep(1)
    return jsonify('ok')


# 批量新增  
@home.route("/add_companies", methods=["GET", "POST"])
def update_company():
 secondhand_ships: List[SecondhandShip] = []
 for i in range(101):
     secondhand_ships.append(SecondhandShip(id=None, name='育明', size='超大型', dwt='10W', type='巴拿马', built='2012-12-03',
                                            main_engine='MAN', special_survey='2019-12-12', dry_docking='2019-10-10',
                                            price=10000, buyers=1203, buyers_abbr='cosco', sellers=1,
                                            sellers_abbr='DELOITTE', date='2020-02-02', imo='1773637',
                                            comments='secondhandShip', tips='test',
                                            yard=None, gear=None, hull=None))
 db.session.add_all(secondhand_ships)
 db.session.commit()
 return jsonify("ok")
 
 
@home.route("/add_companies", methods=["GET", "POST"])
def update_company():
 news_list: List[News] = []
 data = News.query.filter_by(id=6).first().to_dict()
 for i in range(101):
     news = News()
     data['id'] = None
     model = model_format(news, data)
     news_list.append(model)
 db.session.add_all(news_list)
 db.session.commit()
 return jsonify("ok")
'''

# 船舶类型
@home.route("/ship/type/list")
@user_login_req
def ship_type_list():
    result = ShipType.query.all()
    return jsonify(result)


# 二手船模块
# 查询所有二手船数据
@home.route("/secondhandShip/list")
@user_login_req
def secondhand_ship_list():
    ships_count = SecondhandShip.query.count()
    total_page = int((ships_count + 30 - 1) / 30)
    # result = db.session.query(SecondhandShip).order_by(SecondhandShip.date.desc()).limit(30)
    result = db.session.query(SecondhandShip).order_by(SecondhandShip.id.asc()).limit(30)
    secondhand_ships = [item.to_dict() for item in result]
    print('查找所有二手船数据,共'+str(ships_count)+'条,'+'共'+str(total_page)+'页')
    return jsonify({'total_page': total_page, 'secondhand_ships': secondhand_ships})


# 分页查询二手船数据
@home.route("/secondhandShip/list/paging", methods=["GET", "POST"])
@user_login_req
def secondhand_ship_paging():
    view_model = model_for_post()
    page_index = view_model['page_index']
    page_size = view_model['page_size']
    result = db.session.query(SecondhandShip).order_by(
        SecondhandShip.id.asc()
    ).limit(
        page_size
    ).offset(
        (page_index - 1) * page_size
    )
    secondhand_ships = [item.to_dict() for item in result]
    print(len(secondhand_ships))
    return jsonify(secondhand_ships)


# 查询单个二手船数据
@home.route("/secondhandShip/single", methods=["GET", "POST"])
@user_login_req
def secondhand_ship_single():
    if request.method == 'POST':
        view_model = model_for_post()
        ship_id = int(view_model['id'])
        secondhand_ship = SecondhandShip.query.filter_by(id=ship_id).first()
        if secondhand_ship:
            return jsonify({'status': 'ok', 'result': secondhand_ship})
        else:
            return jsonify({'status': 'err', 'result': '暂无数据!'})


# 条件查询二手船数据
@home.route("/secondhandShip/name", methods=["GET", "POST"])
@user_login_req
def secondhand_ship_name():
    if request.method == 'POST':
        view_model = model_for_post()
        key = ''
        ship_type = ''
        ship_date = ''
        if 'key' in view_model.keys():
            key = str(view_model['key'])
        if 'ship_type' in view_model.keys():
            ship_type = view_model['ship_type']
        if 'ship_date' in view_model.keys():
            ship_date = str(view_model['ship_date'])
            if ship_date != '':
                ship_date = str(datetime.date.today() - datetime.timedelta(days=int(ship_date)))
                print('查找日期是: ' + ship_date + ' 以后的数据')
        result = SecondhandShip.query.filter(
            or_(
                SecondhandShip.name.ilike('%' + key + '%'),
                SecondhandShip.yard.ilike('%' + key + '%'),
                SecondhandShip.buyers_abbr.ilike('%' + key + '%'),
                SecondhandShip.sellers_abbr.ilike('%' + key + '%')
            )
        ).filter(
            SecondhandShip.type.ilike('%' + ship_type + '%')
        ).filter(
            SecondhandShip.date >= ship_date
        ).order_by(
            SecondhandShip.date.desc()
        ).all()
        return jsonify({'status': 'ok', 'result': result})


# 根据企业id查询二手船数据
@home.route("/secondhandShip/buyers", methods=["GET", "POST"])
@user_login_req
def secondhand_ship_company():
    if request.method == 'POST':
        view_model = model_for_post()
        buyers = int(view_model['buyers'])
        secondhand_ship = SecondhandShip.query.filter_by(buyers=buyers).all()
        if len(secondhand_ship) == 0:
            return jsonify({'status': 'err', 'result': '暂无数据!'})
        else:
            return jsonify({'status': 'ok', 'result': secondhand_ship})


# 新增或修改二手船数据
@home.route("/secondhandShip/add", methods=["GET", "POST"])
@user_login_req
def secondhand_ship_add():
    if request.method == 'POST':
        view_model = model_for_post()
        if view_model:
            secondhand_ship = SecondhandShip()
            model = model_format(secondhand_ship, view_model)
            if model.id:
                db.session.query(SecondhandShip).filter(SecondhandShip.id == model.id).update({
                    'size': model.size, 'name': model.name, 'type': model.type, 'dwt': model.dwt, 'built': model.built,
                    'yard': model.yard, 'main_engine': model.main_engine, 'special_survey': model.special_survey,
                    'dry_docking': model.dry_docking, 'gear': model.gear, 'hull': model.hull, 'price': model.price,
                    'buyers': model.buyers, 'buyers_abbr': model.buyers_abbr, 'sellers': model.sellers,
                    'sellers_abbr': model.sellers_abbr, 'date': model.date, 'comments': model.comments,
                    'imo': model.imo, 'add_time': model.add_time, 'tips': model.tips})
                db.session.commit()
                return jsonify({'status': 'ok', 'op': 'edit', 'info': '修改二手船数据成功!'})
            else:
                db.session.add(model)
                db.session.commit()
                return jsonify({'status': 'ok', 'op': 'add', 'info': '新增二手船数据成功!'})
        return jsonify({'status': 'err', 'info': '所填信息不可为空!'})


# 删除二手船数据
@home.route("/secondhandShip/delete", methods=["GET", "POST"])
@user_login_req
def secondhand_ship_delete():
    view_model = model_for_post()
    ship_id = int(view_model['id'])
    model = SecondhandShip.query.filter_by(id=ship_id).first()
    if model:
        db.session.delete(model)
        db.session.commit()
        return jsonify({'status': 'ok', 'info': '删除成功'})
    return jsonify({'status': 'err', 'info': '暂无数据'})


# 新造船模块
# 查询所有新造船数据
@home.route("/newBuilding/list")
@user_login_req
def new_building_list():
    ships_count = Newbuilding.query.count()
    total_page = int((ships_count + 30 - 1) / 30)
    result = db.session.query(Newbuilding).order_by(Newbuilding.id.asc()).limit(30)
    new_buildings = [item.to_dict() for item in result]
    print('查找所有新造船数据,共'+str(ships_count)+'条,'+'共'+str(total_page)+'页')
    return jsonify({'total_page': total_page, 'new_buildings': new_buildings})


# 分页查询新造船数据
@home.route("/newBuilding/list/paging", methods=["GET", "POST"])
@user_login_req
def new_building_paging():
    view_model = model_for_post()
    page_index = view_model['page_index']
    page_size = view_model['page_size']
    result = db.session.query(Newbuilding).order_by(
        Newbuilding.id.asc()
    ).limit(
        page_size
    ).offset(
        (page_index - 1) * page_size
    )
    new_buildings = [item.to_dict() for item in result]
    print(len(new_buildings))
    return jsonify(new_buildings)


# 查询单个新造船数据
@home.route("/newBuilding/single", methods=["GET", "POST"])
@user_login_req
def new_building_single():
    if request.method == 'POST':
        view_model = model_for_post()
        ship_id = int(view_model['id'])
        new_building = Newbuilding.query.filter_by(id=ship_id).first()
        if new_building:
            return jsonify({'status': 'ok', 'result': new_building})
        else:
            return jsonify({'status': 'err', 'result': '暂无数据!'})


# 条件查询新造船数据
@home.route("/newBuilding/type", methods=["GET", "POST"])
@user_login_req
def new_building_owner():
    if request.method == 'POST':
        view_model = model_for_post()
        key = ''
        ship_type = ''
        ship_date = ''
        if 'key' in view_model.keys():
            key = str(view_model['key'])
        if 'ship_type' in view_model.keys():
            ship_type = view_model['ship_type']
        if 'ship_date' in view_model.keys():
            ship_date = str(view_model['ship_date'])
            if ship_date != '':
                ship_date = str(datetime.date.today() - datetime.timedelta(days=int(ship_date)))
                print('查找日期是: ' + ship_date + ' 以后的数据')
        result = Newbuilding.query.filter(
            or_(
                Newbuilding.yard.ilike('%' + key + '%'),
                Newbuilding.owner_abbr.ilike('%' + key + '%')
            )
        ).filter(
            Newbuilding.type.ilike('%' + ship_type + '%')
        ).filter(
            Newbuilding.date >= ship_date
        ).order_by(
            Newbuilding.date.desc()
        ).all()
        return jsonify({'status': 'ok', 'result': result})


# 根据企业id查询新造船数据
@home.route("/newBuilding/owner", methods=["GET", "POST"])
@user_login_req
def new_building_company():
    if request.method == 'POST':
        view_model = model_for_post()
        owner = int(view_model['owner'])
        new_building = Newbuilding.query.filter_by(owner=owner).all()
        if len(new_building) == 0:
            return jsonify({'status': 'err', 'result': '暂无数据!'})
        else:
            return jsonify({'status': 'ok', 'result': new_building})


# 新增或修改新造船数据
@home.route("/newBuilding/add", methods=["GET", "POST"])
@user_login_req
def new_building_add():
    if request.method == 'POST':
        view_model = model_for_post()
        if view_model:
            new_building = Newbuilding()
            model = model_format(new_building, view_model)
            if model.id:
                db.session.query(Newbuilding).filter(Newbuilding.id == model.id).update({
                    'size': model.size, 'dwt': model.dwt, 'type': model.type, 'units': model.units,
                    'built': model.built, 'yard': model.yard, 'price': model.price,
                    'owner': model.owner, 'owner_abbr': model.owner_abbr, 'country': model.country,
                    'date': model.date, 'comments': model.comments, 'add_time': model.add_time, 'tips': model.tips})
                db.session.commit()
                return jsonify({'status': 'ok', 'op': 'edit', 'info': '修改新造船数据成功!'})
            else:
                db.session.add(model)
                db.session.commit()
                return jsonify({'status': 'ok', 'op': 'add', 'info': '新增新造船数据成功!'})
        return jsonify({'status': 'err', 'info': '所填信息不可为空!'})


# 删除新造船数据
@home.route("/newBuilding/delete", methods=["GET", "POST"])
@user_login_req
def new_building_delete():
    view_model = model_for_post()
    ship_id = int(view_model['id'])
    model = Newbuilding.query.filter_by(id=ship_id).first()
    if model:
        db.session.delete(model)
        db.session.commit()
        return jsonify({'status': 'ok', 'info': '删除成功'})
    return jsonify({'status': 'err', 'info': '暂无数据'})


# 拆船模块
# 查询所有拆船数据
@home.route("/shipDemolition/list")
@user_login_req
def ship_demolition_list():
    ships_count = ShipDemolition.query.count()
    total_page = int((ships_count + 30 - 1) / 30)
    result = db.session.query(ShipDemolition).order_by(ShipDemolition.id.asc()).limit(30)
    ships_demolition = [item.to_dict() for item in result]
    print('查找所有拆船数据,共'+str(ships_count)+'条,'+'共'+str(total_page)+'页')
    return jsonify({'total_page': total_page, 'ships_demolition': ships_demolition})


# 分页查询拆船数据
@home.route("/shipDemolition/list/paging", methods=["GET", "POST"])
@user_login_req
def ship_demolition_paging():
    view_model = model_for_post()
    page_index = view_model['page_index']
    page_size = view_model['page_size']
    result = db.session.query(ShipDemolition).order_by(
        ShipDemolition.id.asc()
    ).limit(
        page_size
    ).offset(
        (page_index - 1) * page_size
    )
    ships_demolition = [item.to_dict() for item in result]
    print(len(ships_demolition))
    return jsonify(ships_demolition)


# 查询单个拆船数据
@home.route("/shipDemolition/single", methods=["GET", "POST"])
@user_login_req
def ship_demolition_single():
    if request.method == 'POST':
        view_model = model_for_post()
        ship_id = int(view_model['id'])
        ship_demolition = ShipDemolition.query.filter_by(id=ship_id).first()
        if ship_demolition:
            return jsonify({'status': 'ok', 'result': ship_demolition})
        else:
            return jsonify({'status': 'err', 'result': '暂无数据!'})


# 条件查询拆船数据
@home.route("/shipDemolition/name", methods=["GET", "POST"])
@user_login_req
def ship_demolition_name():
    if request.method == 'POST':
        view_model = model_for_post()
        key = ''
        ship_type = ''
        ship_date = ''
        if 'key' in view_model.keys():
            key = str(view_model['key'])
        if 'ship_type' in view_model.keys():
            ship_type = view_model['ship_type']
        if 'ship_date' in view_model.keys():
            ship_date = str(view_model['ship_date'])
            if ship_date != '':
                ship_date = str(datetime.date.today() - datetime.timedelta(days=int(ship_date)))
                print('查找日期是: ' + ship_date + ' 以后的数据')
        result = ShipDemolition.query.filter(
            or_(
                ShipDemolition.name.ilike('%' + key + '%'),
                ShipDemolition.owner_abbr.ilike('%' + key + '%')
            )
        ).filter(
            ShipDemolition.type.ilike('%' + ship_type + '%')
        ).filter(
            ShipDemolition.date >= ship_date
        ).order_by(
            ShipDemolition.date.desc()
        ).all()
        return jsonify({'status': 'ok', 'result': result})


# 根据企业id查询拆船数据
@home.route("/shipDemolition/owner", methods=["GET", "POST"])
@user_login_req
def ship_demolition_company():
    if request.method == 'POST':
        view_model = model_for_post()
        owner = int(view_model['owner'])
        ship_demolition = ShipDemolition.query.filter_by(owner=owner).all()
        if len(ship_demolition) == 0:
            return jsonify({'status': 'err', 'result': '暂无数据!'})
        else:
            return jsonify({'status': 'ok', 'result': ship_demolition})


# 新增或修改拆船数据
@home.route("/shipDemolition/add", methods=["GET", "POST"])
@user_login_req
def ship_demolition_add():
    if request.method == 'POST':
        view_model = model_for_post()
        if view_model:
            ship_demolition = ShipDemolition()
            model = model_format(ship_demolition, view_model)
            if model.id:
                db.session.query(ShipDemolition).filter(ShipDemolition.id == model.id).update({
                    'name': model.name, 'size': model.size, 'type': model.type, 'built': model.built,
                    'ldt': model.ldt, 'dwt': model.dwt, 'price': model.price,
                    'owner': model.owner, 'owner_abbr': model.owner_abbr, 'region': model.region,
                    'date': model.date, 'comments': model.comments, 'add_time': model.add_time, 'tips': model.tips})
                db.session.commit()
                return jsonify({'status': 'ok', 'op': 'edit', 'info': '修改拆船数据成功!'})
            else:
                db.session.add(model)
                db.session.commit()
                return jsonify({'status': 'ok', 'op': 'add', 'info': '新增拆船数据成功!'})
        return jsonify({'status': 'err', 'info': '所填信息不可为空!'})


# 删除拆船数据
@home.route("/shipDemolition/delete", methods=["GET", "POST"])
@user_login_req
def ship_demolition_delete():
    view_model = model_for_post()
    ship_id = int(view_model['id'])
    model = ShipDemolition.query.filter_by(id=ship_id).first()
    if model:
        db.session.delete(model)
        db.session.commit()
        return jsonify({'status': 'ok', 'info': '删除成功'})
    return jsonify({'status': 'err', 'info': '暂无数据'})


# 期租模块
# 查询所有期租数据
@home.route("/timeCharter/list")
@user_login_req
def time_charter_list():
    ships_count = TimeCharter.query.count()
    total_page = int((ships_count + 30 - 1) / 30)
    result = db.session.query(TimeCharter).order_by(TimeCharter.id.asc()).limit(30)
    time_charters = [item.to_dict() for item in result]
    print('查找所有期租数据,共'+str(ships_count)+'条,'+'共'+str(total_page)+'页')
    return jsonify({'total_page': total_page, 'time_charters': time_charters})


# 分页查询期租数据
@home.route("/timeCharter/list/paging", methods=["GET", "POST"])
@user_login_req
def time_charter_paging():
    view_model = model_for_post()
    page_index = view_model['page_index']
    page_size = view_model['page_size']
    result = db.session.query(TimeCharter).order_by(
        TimeCharter.id.asc()
    ).limit(
        page_size
    ).offset(
        (page_index - 1) * page_size
    )
    time_charters = [item.to_dict() for item in result]
    print(len(time_charters))
    return jsonify(time_charters)


# 查询单个期租数据
@home.route("/timeCharter/single", methods=["GET", "POST"])
@user_login_req
def time_charter_single():
    if request.method == 'POST':
        view_model = model_for_post()
        ship_id = int(view_model['id'])
        time_charter = TimeCharter.query.filter_by(id=ship_id).first()
        if time_charter:
            return jsonify({'status': 'ok', 'result': time_charter})
        else:
            return jsonify({'status': 'err', 'result': '暂无数据!'})


# 条件查询期租数据
@home.route("/timeCharter/name", methods=["GET", "POST"])
@user_login_req
def time_charter_name():
    if request.method == 'POST':
        view_model = model_for_post()
        print(view_model)
        key = ''
        ship_type = ''
        ship_date = ''
        if 'key' in view_model.keys():
            key = str(view_model['key'])
        if 'ship_type' in view_model.keys():
            ship_type = view_model['ship_type']
        if 'ship_date' in view_model.keys():
            ship_date = str(view_model['ship_date'])
            if ship_date != '':
                ship_date = str(datetime.date.today() - datetime.timedelta(days=int(ship_date)))
                print('查找日期是: ' + ship_date + ' 以后的数据')
        result = TimeCharter.query.filter(
            or_(
                TimeCharter.name.ilike('%' + key + '%'),
                TimeCharter.yard.ilike('%' + key + '%'),
                TimeCharter.owner_abbr.ilike('%' + key + '%'),
                TimeCharter.charterer_abbr.ilike('%' + key + '%')
            )
        ).filter(
            TimeCharter.type.ilike('%' + ship_type + '%')
        ).filter(
            TimeCharter.date >= ship_date
        ).order_by(
            TimeCharter.date.desc()
        ).all()
        print(len(result))
        return jsonify({'status': 'ok', 'result': result})

# 根据企业id查询期租数据
@home.route("/timeCharter/owner", methods=["GET", "POST"])
@user_login_req
def time_charter_company():
    if request.method == 'POST':
        view_model = model_for_post()
        owner = int(view_model['owner'])
        time_charter = TimeCharter.query.filter_by(owner=owner).all()
        if len(time_charter) == 0:
            return jsonify({'status': 'err', 'result': '暂无数据!'})
        else:
            return jsonify({'status': 'ok', 'result': time_charter})


# 新增期租数据
@home.route("/timeCharter/add", methods=["GET", "POST"])
@user_login_req
def time_charter_add():
    if request.method == 'POST':
        view_model = model_for_post()
        if view_model:
            time_charter = TimeCharter()
            model = model_format(time_charter, view_model)
            if model.id:
                db.session.query(TimeCharter).filter(TimeCharter.id == model.id).update({
                    'size': model.size, 'name': model.name, 'type': model.type, 'dwt': model.dwt,
                    'built': model.built, 'yard': model.yard, 'dely': model.dely, 'date': model.date,
                    'via': model.via, 'cargo': model.cargo, 'redly': model.redly, 'rate': model.rate,
                    'owner': model.owner, 'owner_abbr': model.owner_abbr, 'charterer': model.charterer,
                    'charterer_abbr': model.charterer_abbr, 'period': model.period, 'imo': model.imo,
                    'add_time': model.add_time, 'tips': model.tips})
                db.session.commit()
                return jsonify({'status': 'ok', 'op': 'edit', 'info': '修改期租数据成功!'})
            else:
                db.session.add(model)
                db.session.commit()
                return jsonify({'status': 'ok', 'op': 'add', 'info': '新增期租数据成功!'})
        return jsonify({'status': 'err', 'info': '所填信息不可为空'})


# 删除期租数据
@home.route("/timeCharter/delete", methods=["GET", "POST"])
@user_login_req
def time_charter_delete():
    view_model = model_for_post()
    ship_id = int(view_model['id'])
    model = TimeCharter.query.filter_by(id=ship_id).first()
    if model:
        db.session.delete(model)
        db.session.commit()
        return jsonify({'status': 'ok', 'info': '删除成功'})
    return jsonify({'status': 'err', 'info': '暂无数据'})


# 通讯录模块
# 查询所有通讯录数据
@home.route("/contacts/list")
@user_login_req
def get_contacts_list():
    result = db.session.query(
        Contacts.id, Contacts.name, Contacts.telephone, Contacts.add_time, Company.name.label("current_company")
    ).outerjoin(
        Company, Contacts.current_company == Company.id
    ).order_by(
        Contacts.id.desc()
    ).limit(30)
    contacts_list = [dict(zip(item.keys(), item)) for item in result]
    contacts_count = Contacts.query.count()
    total_page = int((contacts_count + 30 - 1) / 30)
    print('查找所有联系人数据,共'+str(contacts_count)+'条,'+'共'+str(total_page)+'页')
    return jsonify({'total_page': total_page, 'contacts_list': contacts_list})


# 分页查询通讯录数据
@home.route("/contacts/list/paging", methods=["GET", "POST"])
@user_login_req
def contacts_paging():
    view_model = model_for_post()
    page_index = view_model['page_index']
    page_size = view_model['page_size']
    result = db.session.query(
        Contacts.id, Contacts.name, Contacts.telephone, Contacts.add_time, Company.name.label("current_company")
    ).outerjoin(
        Company, Contacts.current_company == Company.id
    ).order_by(
        Contacts.id.desc()
    ).limit(
        page_size
    ).offset(
        (page_index - 1) * page_size
    )
    contacts_list = [dict(zip(item.keys(), item)) for item in result]
    return jsonify(contacts_list)


# 查询单个通讯录数据
@home.route("/contacts/single", methods=["GET", "POST"])
@user_login_req
def contacts_single():
    if request.method == 'POST':
        view_model = model_for_post()
        contacts_id = int(view_model['id'])
        contacts = Contacts.query.filter_by(id=contacts_id).first()
        if contacts:
            return jsonify({'status': 'ok', 'result': contacts})
        else:
            return jsonify({'status': 'err', 'info': '暂无数据!'})


# 条件查询通讯录数据
@home.route("/contacts/name", methods=["GET", "POST"])
@user_login_req
def contacts_name():
    if request.method == 'POST':
        view_model = model_for_post()
        key = ''
        current_company = ''
        contacts_date = ''
        if 'key' in view_model.keys():
            key = str(view_model['key'])
        if 'current_company' in view_model.keys():
            current_company = str(view_model['current_company'])
        if 'contacts_date' in view_model.keys():
            contacts_date = str(view_model['contacts_date'])
            if contacts_date != '':
                contacts_date = str(datetime.date.today() - datetime.timedelta(days=int(contacts_date)))
                print('查找日期是: ' + contacts_date + ' 以后的数据')

        result = db.session.query(
            Contacts.id, Contacts.name, Contacts.add_time, Company.name.label('current_company'),
            Company.id.label('company_id')
        ).outerjoin(
            Company, Contacts.current_company == Company.id
        ).filter(
            or_(
                Contacts.name.ilike('%' + key + '%'),
                Contacts.chs_name.ilike('%' + key + '%'),
                Contacts.profile.ilike('%' + key + '%')
            )
        ).filter(
            Contacts.current_company.ilike('%' + current_company + '%')
        ).filter(
            Contacts.add_time >= contacts_date
        ).order_by(
            Contacts.id.desc()
        ).all()
        contacts_list = [dict(zip(item.keys(), item)) for item in result]
        print(contacts_list)
        print(len(contacts_list))
        return jsonify({'status': 'ok', 'result': contacts_list})


# 根据企业id查询通讯录数据
@home.route("/contacts/company_id", methods=["GET", "POST"])
@user_login_req
def contacts_company():
    if request.method == 'POST':
        view_model = model_for_post()
        company_id = int(view_model['company_id'])
        company_contacts_list = Contacts.query.filter_by(current_company=company_id).all()
        if len(company_contacts_list) == 0:
            return jsonify({'status': 'err', 'result': []})
        else:
            return jsonify({'status': 'ok', 'result': company_contacts_list})


# 新增或修改通讯录数据
@home.route("/contacts/add", methods=["GET", "POST"])
@user_login_req
def contacts_add():
    if request.method == 'POST':
        view_model = model_for_post()
        print(type(view_model))
        print(view_model)
        if view_model:
            contacts = Contacts()
            model = model_format(contacts, view_model)
            if model.id:
                db.session.query(Contacts).filter(Contacts.id == model.id).update({
                    'name': model.name, 'chs_name': model.chs_name, 'position': model.position,
                    'profile': model.profile, 'sex': model.sex,
                    'telephone': model.telephone, 'email': model.email,
                    'history_company': model.history_company, 'current_company': model.current_company,
                    'address': model.address, 'add_time': model.add_time})
                db.session.commit()
                return jsonify({'status': 'ok', 'op': 'edit', 'info': '修改通讯录数据成功!'})
            else:
                db.session.add(model)
                db.session.commit()
                print(model.id)
                print(model.name)
                return jsonify({'status': 'ok', 'op': 'add', 'info': '新增通讯录数据成功!', 'data': model})
        return jsonify({'status': 'err', 'info': '系统错误,请稍后再试!'})


# 通讯录数据绑定企业
@home.route("/contacts/bing/company", methods=["GET", "POST"])
@user_login_req
def contacts_bing_company():
    if request.method == 'POST':
        data = eval(str(request.data, encoding="utf-8").replace('null', '\"\"'))
        if len(data['contacts_list']) != 0 and data['company_id'] != 0 and data['company_id'] is not None:
            for item in data['contacts_list']:
                db.session.query(Contacts).filter(Contacts.id == item['id']).update({
                    Contacts.current_company: data['company_id']})
                db.session.commit()
            return jsonify({'status': 'ok', 'op': 'edit', 'info': '通讯录数据绑定企业成功!'})
        return jsonify({'status': 'err', 'info': '通讯录数据绑定企业失败!'})


# 删除通讯录数据
@home.route("/contacts/delete", methods=["GET", "POST"])
@user_login_req
def contacts_delete():
    # type=1 逻辑删除   type=0 物理删除
    view_model = model_for_post()
    print(view_model)
    contacts_id = str(view_model['contacts_id'])
    company_id = str(view_model['company_id'])
    op_type = int(view_model['type'])
    model = Contacts.query.filter(Contacts.id == contacts_id).first()
    if model and op_type == 1:
        db.session.query(Contacts).filter(
            and_(
                Contacts.id == contacts_id,
                Contacts.current_company == company_id
            )
        ).update(
            {Contacts.current_company: ''}
        )
        db.session.commit()
        return jsonify({'status': 'ok', 'info': '删除成功'})
    if model and op_type == 0:
        db.session.delete(model)
        db.session.commit()
        return jsonify({'status': 'ok', 'info': '删除成功'})
    return jsonify({'status': 'err', 'info': '删除失败'})


# 所属行业
@home.route("/category/<int:id>/")
def category(id=None):
    if id is None:
        id = 1
    category = Category.query.filter_by(id=id).all()
    return jsonify(category[0])


# 所有行业
@home.route("/categories/")
def categories():
    categories_list = Category.query.all()
    return jsonify(categories_list)


# 系统管理
@home.route("/system/")
@user_login_req
def system():
    return render_template("home/system.html")


# 企业搜索
@home.route("/search")
def search():
    key = request.args.get("key", "").upper()

    little_company_list = []
    all_company_list = []
    all_company = Company.query.filter(
        or_(
            Company.name.ilike('%' + key + '%'),
            Company.chs_name.ilike('%' + key + '%'),
            Company.abbr.ilike('%' + key + '%')
        )
    ).all()
    for company in all_company:
        category_list = company.category_id.split(',')
        category_name = Category.query.filter(Category.id == category_list[0]).first().name
        all_company_list.append({'id': company.id, 'name': company.name, 'category': category_name})

    company_count = len(all_company_list)

    if company_count > 4:
        for a in range(0, 4):
            little_company_list.append(all_company_list[a])
    else:
        little_company_list = all_company_list

    return render_template("home/search.html",
                           company_count=company_count,
                           key=key,
                           all_company_list=all_company_list,
                           little_company_list=little_company_list)


# 分类搜索图片企业新闻
@home.route("/search_by_category")
def search_by_category():

    key = request.args.get("key", "").upper()
    category_id = str(request.args.get("category", ""))

    little_company_list = []
    all_company_list = []
    all_company = Company.query.filter(Company.category_id.ilike('%' + category_id + '%')).all()
    for company in all_company:
        category_list = company.category_id.split(',')
        category_name = Category.query.filter(Category.id == category_list[0]).first().name
        all_company_list.append({'id': company.id, 'name': company.name, 'category': category_name})

    company_count = len(all_company_list)

    if company_count > 4:
        for a in range(0, 4):
            little_company_list.append(all_company_list[a])
    else:
        little_company_list = all_company_list

    return render_template("home/search_by_category.html",
                           company_count=company_count,
                           key=key,
                           category_id=category_id,
                           all_company_list=all_company_list,
                           little_company_list=little_company_list)
