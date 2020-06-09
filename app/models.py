from datetime import datetime
from app import db


# 用户
class User(db.Model):
    __tablename__ = "user"  # 表名
    __table_args__ = {"useexisting": True}  # 更新表结构时加上此参数才会生效
    id = db.Column(db.Integer, primary_key=True)  # 编号
    name = db.Column(db.String(100), unique=True)  # 昵称
    pwd = db.Column(db.String(100))  # 密码
    email = db.Column(db.String(100), unique=True)  # 邮箱
    phone = db.Column(db.String(11), unique=True)  # 手机号码
    info = db.Column(db.Text)  # 个性简介
    face = db.Column(db.String(255), unique=True)  # 头像
    addtime = db.Column(db.DateTime, index=True, default=datetime.now)  # 注册时间
    uuid = db.Column(db.String(255), unique=True)  # 唯一标志符
    userlogs = db.relationship('Userlog', backref='user')  # 会员日志外键关联
    # comments = db.relationship('Comment', backref='user')  # 会员评论外键关联
    operations = db.relationship('Operations', backref='user')  # 会员评论外键关联
    newscols = db.relationship('Newscol', backref='user')  # 用户收藏外键关联

    def __repr__(self):
        return '<User %r>' % self.name

    # 定义返回方法
    def check_pwd(self, pwd):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.pwd, pwd)


# 用户登录日志
class Userlog(db.Model):
    __tablename__ = "userlog"  # 表名
    __table_args__ = {"useexisting": True}  # 更新表结构时加上此参数才会生效
    id = db.Column(db.Integer, primary_key=True)  # 编号
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 所属会员
    ip = db.Column(db.String(100))  # 登录IP
    addtime = db.Column(db.DateTime, index=True, default=datetime.now)  # 登陆时间

    def __repr__(self):
        return '<User %r>' % self.id


# 企业详情
class Company(db.Model):
    __tablename__ = "company"  # 表名
    __table_args__ = {"useexisting": True}  # 更新表结构时加上此参数才会生效
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="")
    chs_name = db.Column(db.String(100), default="")       # 企业中文名
    abbr = db.Column(db.String(100), default="")       # 企业别名
    logo = db.Column(db.String(200))
    profile = db.Column(db.String(300), default="")
    address = db.Column(db.String(100))
    telephone = db.Column(db.String(200))
    facsimile = db.Column(db.String(100))
    email = db.Column(db.String(100))
    website = db.Column(db.String(100))
    # members = db.Column(db.String(300))
    keyword = db.Column(db.String(100), default="")
    add_time = db.Column(db.String(20))  # 数据添加时间
    update_time = db.Column(db.DateTime, index=True, default=datetime.now)  # 更新时间
    found_time = db.Column(db.String(20))  # 企业成立时间
    category_id = db.Column(db.String(30), default="")

    # 返回对象中的每个属性
    def keys(self):
        # return ['id','nickname']也可以指定序列化指定的字段
        return ['id', 'name', 'chs_name', 'abbr', 'logo', 'profile', 'address', 'telephone', 'keyword', 'facsimile',
                'email', 'website', 'add_time', 'update_time', 'found_time', 'category_id']

    # 通过对象的每个属性获取对应的值
    def __getitem__(self, item):
        return getattr(self, item)

    # 转换成Json对象
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# 船舶类型
class ShipType(db.Model):
    __tablename__ = "ship_type"  # 表名
    __table_args__ = {"useexisting": True}  # 更新表结构时加上此参数才会生效
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(30))  # 船名

    # 返回对象中的每个属性
    def keys(self):
        # return ['id','nickname']也可以指定序列化指定的字段
        return ['id', 'type']

    # 通过对象的每个属性获取对应的值
    def __getitem__(self, item):
        return getattr(self, item)

    # 转换成Json对象
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# 二手船买卖
class SecondhandShip(db.Model):
    __tablename__ = "secondhand_ship"  # 表名
    __table_args__ = {"useexisting": True}  # 更新表结构时加上此参数才会生效
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="")  # 船名
    size = db.Column(db.String(200))  # 尺寸
    dwt = db.Column(db.String(200))  # 载重吨
    type = db.Column(db.String(300), default="")  # 船舶类型
    built = db.Column(db.String(100))  # 建造年代
    yard = db.Column(db.String(200), default="")  # 造船厂
    main_engine = db.Column(db.String(100))  # 主机型号
    special_survey = db.Column(db.String(100))      # 特别检查时间
    dry_docking = db.Column(db.String(100))     # 船坞检查时间
    gear = db.Column(db.String(100))  # 船舶起重机负荷
    hull = db.Column(db.String(100))  # 船壳
    price = db.Column(db.String(50))  # 价格
    buyers = db.Column(db.Integer)  # 关联买方企业id
    buyers_abbr = db.Column(db.String(100), default="")  # 买方企业简写
    sellers = db.Column(db.Integer)  # 关联卖方企业id
    sellers_abbr = db.Column(db.String(100), default="")  # 卖方企业简写
    comments = db.Column(db.String(100))  # 交易备注
    date = db.Column(db.String(100), default="")  # 交船时间
    imo = db.Column(db.Integer)  # 国际海事组织船舶编号
    add_time = db.Column(db.String(20), default=datetime.now().strftime('%Y-%m-%d'))  # 数据添加时间
    tips = db.Column(db.String(100))  # 操作备注

    # 返回对象中的每个属性
    def keys(self):
        # return ['id','nickname']也可以指定序列化指定的字段
        return ['id', 'name', 'size', 'dwt', 'built', 'yard', 'type', 'main_engine', 'special_survey',
                'dry_docking', 'gear', 'hull', 'price', 'buyers', 'buyers_abbr', 'sellers', 'sellers_abbr',
                'date', 'comments', 'imo', 'add_time', 'tips']

    # 通过对象的每个属性获取对应的值
    def __getitem__(self, item):
        return getattr(self, item)

    # 转换成Json对象
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# 新造船
class Newbuilding(db.Model):
    __tablename__ = "newbuilding"  # 表名
    __table_args__ = {"useexisting": True}  # 更新表结构时加上此参数才会生效
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(300), default="")   # 船舶类型
    dwt = db.Column(db.String(200))   # 载重吨
    units = db.Column(db.String(200))   # 项目数量
    size = db.Column(db.String(200))   # 尺寸
    built = db.Column(db.String(100))   # 建造年代
    yard = db.Column(db.String(200), default="")   # 造船厂
    price = db.Column(db.String(300))   # 价格
    owner = db.Column(db.Integer)   # 关联船东企业id
    owner_abbr = db.Column(db.String(100), default="")   # 船东企业简称
    country = db.Column(db.String(100))   # 船东国籍
    date = db.Column(db.String(100), default="")   # 交船时间
    comments = db.Column(db.String(100))  # 交易备注
    # company_id = db.Column(db.Integer)  # 关联企业id
    add_time = db.Column(db.String(20), default=datetime.now().strftime('%Y-%m-%d'))  # 数据添加时间
    tips = db.Column(db.String(100))  # 操作备注

    # 返回对象中的每个属性
    def keys(self):
        # return ['id','nickname']也可以指定序列化指定的字段
        return ['id', 'type', 'dwt', 'dwt', 'units', 'size', 'built', 'yard', 'price', 'owner',
                'owner_abbr', 'country', 'date', 'comments', 'add_time', 'tips']

    # 通过对象的每个属性获取对应的值
    def __getitem__(self, item):
        return getattr(self, item)

    # 转换成Json对象
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# 拆船
class ShipDemolition(db.Model):
    __tablename__ = "ship_demolition"  # 表名
    __table_args__ = {"useexisting": True}  # 更新表结构时加上此参数才会生效
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), default="")  # 船名
    size = db.Column(db.String(200))  # 尺寸
    type = db.Column(db.String(300), default="")  # 船舶类型
    built = db.Column(db.String(200))  # 建造年代
    dwt = db.Column(db.String(200))  # 载重吨
    ldt = db.Column(db.String(100))  # 轻吨
    price = db.Column(db.String(300))  # 价格
    owner = db.Column(db.Integer)  # 船东企业id
    owner_abbr = db.Column(db.String(100), default="")  # 船东企业简称
    region = db.Column(db.String(100))  # 拆船地点
    date = db.Column(db.String(100), default="")  # 交船时间
    comments = db.Column(db.String(100))  # 交易备注
    # company_id = db.Column(db.Integer)  # 关联企业id
    add_time = db.Column(db.String(20), default=datetime.now().strftime('%Y-%m-%d'))  # 数据添加时间
    tips = db.Column(db.String(100))  # 操作备注

    # 返回对象中的每个属性
    def keys(self):
        # return ['id','nickname']也可以指定序列化指定的字段
        return ['id', 'name', 'size', 'type', 'built', 'dwt', 'ldt', 'price', 'owner', 'owner_abbr',
                'region', 'date', 'comments', 'add_time', 'tips']

    # 通过对象的每个属性获取对应的值
    def __getitem__(self, item):
        return getattr(self, item)

    # 转换成Json对象
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# 期租
class TimeCharter(db.Model):
    __tablename__ = "time_charter"  # 表名
    __table_args__ = {"useexisting": True}  # 更新表结构时加上此参数才会生效
    id = db.Column(db.Integer, primary_key=True)
    size = db.Column(db.String(100))  # 尺寸
    name = db.Column(db.String(100), default="")  # 船名
    type = db.Column(db.String(100), default="")  # 船舶类型
    dwt = db.Column(db.String(200))  # 载重吨
    built = db.Column(db.String(100))  # 建造年代
    yard = db.Column(db.String(200), default="")  # 造船厂
    dely = db.Column(db.String(200))  # 交船地点
    date = db.Column(db.String(100), default="")  # 交船时间
    via = db.Column(db.String(100))  # 装货地点
    cargo = db.Column(db.String(100))  # 货物
    redly = db.Column(db.String(100))  # 还船地点
    rate = db.Column(db.String(100))  # 租金
    owner = db.Column(db.Integer)  # 关联船东企业id
    owner_abbr = db.Column(db.String(100), default="")  # 船东企业简称
    charterer = db.Column(db.Integer)  # 关联租家企业id
    charterer_abbr = db.Column(db.String(100), default="")  # 租家企业简称
    period = db.Column(db.String(100))  # 租期
    # company_id = db.Column(db.Integer)  # 关联企业id
    imo = db.Column(db.Integer)  # 国际海事组织船舶编号
    add_time = db.Column(db.String(20), default=datetime.now().strftime('%Y-%m-%d'))  # 数据添加时间
    tips = db.Column(db.String(100))  # 操作备注

    # 返回对象中的每个属性
    def keys(self):
        # return ['id','nickname']也可以指定序列化指定的字段
        return ['id', 'size', 'name', 'type', 'dwt', 'built', 'yard', 'dely', 'date', 'via', 'cargo', 'redly',
                'rate', 'owner', 'owner_abbr', 'charterer', 'charterer_abbr', 'period', 'imo', 'add_time', 'tips']

    # 通过对象的每个属性获取对应的值
    def __getitem__(self, item):
        return getattr(self, item)

    # 转换成Json对象
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# 企业类别
class Category(db.Model):
    __tablename__ = "category"  # 表名
    __table_args__ = {"useexisting": True}  # 更新表结构时加上此参数才会生效
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    priority = db.Column(db.Integer)

    # 返回对象中的每个属性
    def keys(self):
        # return ['id','nickname']也可以指定序列化指定的字段
        return ['id', 'name', 'priority']

    # 通过对象的每个属性获取对应的值
    def __getitem__(self, item):
        return getattr(self, item)

    # 转换成Json对象
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# 企业图库
class Image(db.Model):
    __tablename__ = "image"  # 表名
    __table_args__ = {"useexisting": True}  # 更新表结构时加上此参数才会生效
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(200))
    keyword = db.Column(db.String(100))
    time = db.Column(db.DateTime, index=True, default=datetime.now)  # 添加时间
    company_id = db.Column(db.Integer)
    news_id = db.Column(db.Integer)
    category_id = db.Column(db.Integer)

    # 返回对象中的每个属性
    def keys(self):
        # return ['id','nickname']也可以指定序列化指定的字段
        return ['id', 'url', 'keyword', 'time', 'company_id', 'news_id', 'category_id']

    # 通过对象的每个属性获取对应的值
    def __getitem__(self, item):
        return getattr(self, item)

    # 转换成Json对象
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# 企业新闻
class News(db.Model):
    __tablename__ = "news"  # 表名
    __table_args__ = {"useexisting": True}  # 更新表结构时加上此参数才会生效
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), default="")
    profile = db.Column(db.String(400), default="")
    content = db.Column(db.Text)
    date = db.Column(db.String(20), default="")
    # date = db.Column(db.Date, index=True)
    keyword = db.Column(db.String(300), default="")
    effect = db.Column(db.Integer)
    category = db.Column(db.String(20))
    company_id = db.Column(db.Integer)
    newscols = db.relationship("Newscol", backref='news')  # 新闻收藏

    # 返回对象中的每个属性
    def keys(self):
        # return ['id','nickname']也可以指定序列化指定的字段
        return ['id', 'title', 'profile', 'content', 'date', 'keyword', 'effect', 'category', 'company_id']

    # 通过对象的每个属性获取对应的值
    def __getitem__(self, item):
        return getattr(self, item)

    # 转换成Json对象
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# 通讯录
class Contacts(db.Model):
    __tablename__ = "contacts"  # 表名
    __table_args__ = {"useexisting": True}  # 更新表结构时加上此参数才会生效
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="")        # 姓名
    chs_name = db.Column(db.String(100), default="")    # 中文名
    position = db.Column(db.String(100), default="")    # 职位
    profile = db.Column(db.String(100), default="")                 # 个人简介
    # country = db.Column(db.String(20), default="")      # 国籍
    sex = db.Column(db.String(1))                         # 性别
    telephone = db.Column(db.String(20), default="")    # 联系方式
    email = db.Column(db.String(50), default="")        # 邮箱
    history_company = db.Column(db.String(50), default="")          # 历史任职企业
    current_company = db.Column(db.String(10), default="")          # 当前任职企业
    address = db.Column(db.String(50))                  # 地址
    add_time = db.Column(db.String(10), default=datetime.now().strftime('%Y-%m-%d'))  # 数据添加时间

    # 返回对象中的每个属性
    def keys(self):
        # return ['id','nickname']也可以指定序列化指定的字段
        return ['id', 'name', 'chs_name', 'position', 'profile', 'sex', 'telephone', 'email',
                'history_company', 'current_company', 'address', 'add_time']

    # 通过对象的每个属性获取对应的值
    def __getitem__(self, item):
        return getattr(self, item)

    # 转换成Json对象
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# 新闻概览
class Overview(db.Model):
    __tablename__ = "overview"  # 表名
    __table_args__ = {"useexisting": True}  # 更新表结构时加上此参数才会生效
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    profile = db.Column(db.String(400))
    keyword = db.Column(db.String(300))
    url = db.Column(db.String(300))
    date = db.Column(db.Date, index=True)
    company_id = db.Column(db.Integer)
    status = db.Column(db.Integer)
    source = db.Column(db.Integer)

    # 返回对象中的每个属性
    def keys(self):
        # return ['id','nickname']也可以指定序列化指定的字段
        return ['id', 'title', 'profile', 'keyword', 'url', 'date', 'company_id', 'status', 'source']

    # 通过对象的每个属性获取对应的值
    def __getitem__(self, item):
        return getattr(self, item)

    # 转换成Json对象
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# 新闻收藏
class Newscol(db.Model):
    __tablename__ = "newscol"
    __table_args__ = {"useexisting": True}
    id = db.Column(db.Integer, primary_key=True)  # 编号
    # news_id = db.Column(db.Integer)  # 所属新闻
    # user_id = db.Column(db.Integer)  # 所属用户
    news_id = db.Column(db.Integer, db.ForeignKey('news.id'))  # 所属新闻
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 所属会员
    addtime = db.Column(db.DateTime, index=True, default=datetime.now)  # 添加时间

    def __repr__(self):
        return "<Moviecol %r>" % self.id


# 用户操作记录
class Operations(db.Model):
    __tablename__ = "Operations"
    __table_args__ = {"useexisting": True}
    id = db.Column(db.Integer, primary_key=True)  # 编号
    action = db.Column(db.String(10))  # 操作行为
    content = db.Column(db.String(100))  # 操作内容
    annotation = db.Column(db.String(300))  # 操作备注
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 所属用户
    addtime = db.Column(db.DateTime, index=True, default=datetime.now)  # 操作时间

    def __repr__(self):
        return "<Operations %r>" % self.id


# 电影标签
# class Tag(db.Model):
#     __tablename__ = "tag"  # 表名
#     __table_args__ = {"useexisting": True}
#     id = db.Column(db.Integer, primary_key=True)  # 编号
#     name = db.Column(db.String(100), unique=True)  # 标题
#     addtime = db.Column(db.DateTime, index=True, default=datetime.now)  # 添加时间
#     movies = db.relationship("Movie", backref='tag')  # 所属电影
#
#     def __repr__(self):
#         return "<Tag %r>" % self.name


# # 电影
# class Movie(db.Model):
#     __tablename__ = "movie"  # 表名
#     __table_args__ = {"useexisting": True}
#     id = db.Column(db.Integer, primary_key=True)  # 编号
#     title = db.Column(db.String(255), unique=True)  # 标题
#     url = db.Column(db.String(255), unique=True)  # 地址
#     info = db.Column(db.Text)  # 简介
#     logo = db.Column(db.String(255), unique=True)  # 封面
#     star = db.Column(db.SmallInteger)  # 星级
#     playnum = db.Column(db.BigInteger)  # 播放量
#     commentnum = db.Column(db.BigInteger)  # 评论量
#     #  （设置外键第一步）
#     tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'))  # 所属标签
#     area = db.Column(db.String(255))  # 上映地区
#     release_time = db.Column(db.Date)  # 上映时间
#     length = db.Column(db.String(100))  # 电影时间长度
#     addtime = db.Column(db.DateTime, index=True, default=datetime.now)  # 上传时间
#     comments = db.relationship("Comment", backref='movie')  # 关联评论
#     moviecols = db.relationship("Moviecol", backref='movie')  # 电影收藏
#
#     def __repr__(self):
#         return "<Movie %r>" % self.title


# 上映预告
# class Preview(db.Model):
#     __tablename__ = "preview"
#     __table_args__ = {"useexisting": True}
#     id = db.Column(db.Integer, primary_key=True)  # 编号
#     title = db.Column(db.String(255), unique=True)  # 标题
#     logo = db.Column(db.String(255), unique=True)  # 封面
#     addtime = db.Column(db.DateTime, index=True, default=datetime.now)  # 添加时间
#
#     def __repr__(self):
#         return "<Preview %r>" % self.title


# 评论
# class Comment(db.Model):
#     __tablename__ = "comment"
#     __table_args__ = {"useexisting": True}
#     id = db.Column(db.Integer, primary_key=True)  # 编号
#     content = db.Column(db.Text)  # 内容
#     movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'))  # 所属电影
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 所属会员
#     addtime = db.Column(db.DateTime, index=True, default=datetime.now)  # 评论时间
#
#     def __repr__(self):
#         return "<Comment %r>" % self.id


# 电影收藏
# class Moviecol(db.Model):
#     __tablename__ = "moviecol"
#     __table_args__ = {"useexisting": True}
#     id = db.Column(db.Integer, primary_key=True)  # 编号
#     movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'))  # 所属电影
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 所属会员
#     addtime = db.Column(db.DateTime, index=True, default=datetime.now)  # 添加时间
#
#     def __repr__(self):
#         return "<Moviecol %r>" % self.id


# 权限
# class Auth(db.Model):
#     __tablename__ = "auth"
#     __table_args__ = {"useexisting": True}
#     id = db.Column(db.Integer, primary_key=True)  # 编号
#     name = db.Column(db.String(100), unique=True)  # 名称
#     url = db.Column(db.String(255), unique=True)  # 权限地址
#     addtime = db.Column(db.DateTime, index=True, default=datetime.now)  # 添加时间
#
#     def __repr__(self):
#         return "<Auth %r>" % self.name


# 角色
# class Role(db.Model):
#     __tablename__ = "role"
#     __table_args__ = {"useexisting": True}
#     id = db.Column(db.Integer, primary_key=True)  # 编号
#     name = db.Column(db.String(100), unique=True)  # 名称
#     auths = db.Column(db.String(600))  # 角色权限列表
#     addtime = db.Column(db.DateTime, index=True, default=datetime.now)  # 添加时间
#     admins = db.relationship("Admin", backref='role')  # 管理员外键关联
#
#     def __repr__(self):
#         return "<Role %r>" % self.name


# 管理员
# class Admin(db.Model):
#     __tablename__ = "admin"
#     __table_args__ = {"useexisting": True}
#     id = db.Column(db.Integer, primary_key=True)  # 编号
#     name = db.Column(db.String(100), unique=True)  # 账号
#     pwd = db.Column(db.String(100))  # 密码
#     is_super = db.Column(db.SmallInteger)  # 是否为超级管理员，0为超级管理员
#     role_id = db.Column(db.Integer, db.ForeignKey('role.id'))  # 所属角色
#     addtime = db.Column(db.DateTime, index=True, default=datetime.now)  # 添加时间
#     adminlogs = db.relationship("Adminlog", backref='admin')  # 操作日志外键关联
#     oplogs = db.relationship("Oplog", backref='admin')  # 操作日志外键关联
#
#     def __repr__(self):
#         return "<Admin %r>" % self.name
#
#     def check_pwd(self, pwd):
#         from werkzeug.security import check_password_hash
#         return check_password_hash(self.pwd, pwd)


# 管理员登录日志
# class Adminlog(db.Model):
#     __tablename__ = "adminlog"
#     __table_args__ = {"useexisting": True}
#     id = db.Column(db.Integer, primary_key=True)  # 编号
#     admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'))  # 所属管理员
#     ip = db.Column(db.String(100))  # 登录IP
#     addtime = db.Column(db.DateTime, index=True, default=datetime.now)  # 登陆时间
#
#     def __repr__(self):
#         return "<Adminlog %r>" % self.id


# 操作日志
# class Oplog(db.Model):
#     __tablename__ = "oplog"
#     __table_args__ = {"useexisting": True}
#     id = db.Column(db.Integer, primary_key=True)  # 编号
#     admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'))  # 所属管理员
#     ip = db.Column(db.String(100))  # 登陆IP
#     reason = db.Column(db.String(600))  # 操作原因
#     addtime = db.Column(db.DateTime, index=True, default=datetime.now)  # 登陆时间
#
#     def __repr__(self):
#         return "<Oplog %r>" % self.id


# db.create_all()
# if __name__ == "__main__":
#     db.create_all()
#     role = Role(
#         name = "超级管理员",
#         auths = ""
#     )
#     db.session.add(role)
#     db.session.commit()
#
#
#     from werkzeug.security import generate_password_hash  # 密码哈希加密
#
#     admin = Admin(
#         name = "admin1",
#         pwd = generate_password_hash("eminjan521"),
#         is_super = 0,
#         role_id = 1
#     )
#     db.session.add(admin)
#     db.session.commit()
