from typing import List

from app import app, db
from flask_apscheduler import APScheduler
from app import home
import time


class SchedulerConfig(object):
    JOBS = [
        {
            'id': 'company_news_collect',  # 任务id
            'func': '__main__:company_news_collect',  # 任务执行程序,企业新闻收集
            'args': None,  # 执行程序参数
            'trigger': 'interval',  # 任务执行类型，定时器
            'seconds': 604800  # 任务执行时间，单位秒
            # 'seconds': 10  # 任务执行时间，单位秒
        }
    ]


# 定义任务执行程序,企业新闻收集
def company_news_collect():
    result = db.session.execute(
        "SELECT id,abbr,keyword,update_time FROM company"
    ).fetchall()
    db.session.commit()
    companies = [dict(zip(item.keys(), item)) for item in result]
    for company in companies:
        overviews: List[home.views.Overview] = []
        overview_list = []
        if len(company['keyword'].split(',')) > 1:
            for key in company['keyword'].split():
                overview_list.extend(home.analysis.NewsByBaidu.analysis_html(
                    company['abbr'], key, company['id'], str(company['update_time'].date())))
        else:
            overview_list = home.analysis.NewsByBaidu.analysis_html(
                company['abbr'], company['keyword'], company['id'], str(company['update_time'].date()))
        for overview in overview_list:
            overviews.append(home.views.Overview(
                id=overview['id'], title=overview['title'], profile=overview['profile'],
                keyword=overview['keyword'], url=overview['url'], date=overview['date'],
                status=overview['status'], source=overview['source'], company_id=overview['company_id']))
        db.session.add_all(overviews)
        db.session.commit()
        print('企业: '+company['abbr']+' 相关新闻检索完成')
        time.sleep(10)
    print('overviews: ok!')


# 为实例化的flask引入定时任务配置
app.config.from_object(SchedulerConfig())


if __name__ == "__main__":
    scheduler = APScheduler()  # 实例化APScheduler
    scheduler.init_app(app)  # 把任务列表载入实例flask
    scheduler.start()
    app.run(use_reloader=False, host='127.0.0.1')
