import requests
import time as Time
import datetime
from pyquery import PyQuery as pq
from urllib.parse import quote


# 百度搜索新闻源
class NewsByBaidu(object):

    # 解析网址
    @classmethod
    def search_news(cls, abbr, key):
        search_key = abbr + " " + key
        # print(search_key)
        # kw = {'rtt': 1, 'bsst': 1, 'cl': 2, 'tn': 'news', 'word': key}
        kw = {'rtt': 1, 'bsst': 1, 'cl': 2, 'tn': 'news', 'word': search_key}

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " +
                                 "Chrome/54.0.2840.99 Safari/537.36"}

        # params 接收一个字典或者字符串的查询参数，字典类型自动转换为url编码，不需要urlencode()
        response = requests.get("https://www.baidu.com/s?", params=kw, headers=headers)

        return response.text

    # pyquery 解析
    @classmethod
    def analysis_html(cls, abbr, key, company_id, date=None):
        if date is None:
            date = str(datetime.date.today() - datetime.timedelta(days=180))  # 新闻搜索时间默认为六个月之前
        # print(date)
        doc = pq(NewsByBaidu.search_news(abbr, key))
        pages = NewsByBaidu.analysis_page(doc)
        if pages == 0:
            # print('pages 小于'+'10')
            # print(pages)
            news = NewsByBaidu.analysis_news(doc, key, company_id, date)
            print('来自百度的'+str(len(news))+'条与"' + key + '"相关的新闻')
            # print(news)
        else:
            news = NewsByBaidu.analysis_news(doc, key, company_id, date)
            for page in pages:
                # print(page)
                for item in NewsByBaidu.analysis_news(pq(requests.get(page).text), key, company_id, date):
                    # if 1 == 1:
                    if date < item['date']:
                        news.append({'id': item['id'], 'title': item['title'], 'profile': item['profile'],
                                     'keyword': item['keyword'], 'url': item['url'], 'status': item['status'],
                                     'date': item['date'], 'company_id': item['company_id'], 'source': item['source']})
            # print(len(news))
            # print(news)
            # print(len(pages))
            # print(pages)
            print('来自百度的'+str(len(news))+'条与"' + key + '"相关的新闻')
        return news
        # print(soup.find_all(attrs={'class': 'result'}))

    # 新闻解析
    @classmethod
    def analysis_news(cls, doc, key, company_id, date):
        news = []
        items = doc('.result').items()
        for item in items:
            # print(item)
            href = item('a').attr('href').strip()
            title = item('h3').text().strip()
            if '前' in item.find('p').text().strip().split(' ')[1]:
                time = Time.strftime('%Y-%m-%d', Time.localtime(Time.time()))
            else:
                time = item.find('p').text().strip().split(' ')[1]
            item.find('p').remove()
            item.find('span').remove()
            item.find('h3').remove()
            profile = item.text().strip()
            # source 1为百度 0为谷歌
            news_date = time.replace('年', '-').replace('月', '-').replace('日', '')
            if date < news_date:
                news.append({'id': None, 'title': title, 'profile': profile, 'url': href, 'keyword': key, 'status': 0,
                             'date': news_date, 'source': 1, 'company_id': int(company_id)})
        # print(news)
        return news

    # a标签解析
    @classmethod
    def analysis_page(cls, doc):
        pages = []
        items = doc.find('#page')
        if items.find('a').size() < 1:
            return 0
        items.find('.n').remove()
        a_list = items.find('a')
        for a in a_list:
            pages.append('http://www.baidu.com' + pq(a).attr('href').strip())
        return pages


# 谷歌搜索新闻源
class NewsByGoogle(object):

    # 解析网址
    @classmethod
    def search_news(cls, abbr, key):
        print(abbr)
        search_key = abbr + " " + key
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " +
                                 "Chrome/54.0.2840.99 Safari/537.36"}
        # params 接收一个字典或者字符串的查询参数，字典类型自动转换为url编码，不需要urlencode()
        response = requests.get("http://www.google.com.sg/search?q=" + search_key + "&tbm=nws&tbs=qdr:y", headers=headers)
        return response.text

    # pyquery 解析
    @classmethod
    def analysis_html(cls, abbr, key, company_id, date=None):
        if date is None:
            date = str(datetime.date.today() - datetime.timedelta(days=180))
        # print(date)
        doc = pq(NewsByGoogle.search_news(abbr, key))
        pages = NewsByGoogle.analysis_page(doc)
        # print('pages: '+str(len(pages)))
        if pages == 0:
            print('pages:'+str(pages))
            news = NewsByGoogle.analysis_news(doc, key, company_id, date)
            # print('None')
            # print(len(news))
        else:
            news = NewsByGoogle.analysis_news(doc, key, company_id, date)
            for page in pages:
                for item in NewsByGoogle.analysis_news(pq(search_news(page)), key, company_id, date):
                    if date < item['date']:
                        news.append({'id': item['id'], 'title': item['title'], 'profile': item['profile'],
                                     'keyword': item['keyword'], 'url': item['url'], 'status': item['status'],
                                     'date': item['date'], 'company_id': item['company_id'], 'source': item['source']})
        print('来自谷歌的' + str(len(news)) + '条与"' + key + '"相关的新闻')
        # print(news)
        return news

    # 新闻解析
    @classmethod
    def analysis_news(cls, doc, key, company_id, date):
        news = []
        items = doc('.g').items()
        for item in items:
            # print(item)
            href = item('h3').find('a').attr('href').strip()
            title = item('h3').text().strip()
            meta_time = item.find('.slp').text().strip().split('-')
            if 'ago' in meta_time[len(meta_time) - 1]:
                time = Time.strftime('%Y-%m-%d', Time.localtime(Time.time()))
            else:
                time = meta_time[len(meta_time) - 1]
                time = NewsByGoogle.format_date(time.replace(',', '').split(' '))
            profile = item.find('.st').text().strip()
            # source 1为百度 0为谷歌
            # status 1为已读 0为未读
            news_date = time.replace('年', '-').replace('月', '-').replace('日', '')
            if date < news_date:
                news.append({'id': None, 'title': title, 'profile': profile, 'url': href, 'keyword': key, 'status': 0,
                             'date': news_date, 'source': 0, 'company_id': int(company_id)})
        # print(news)
        return news

    # # a标签解析
    # @classmethod
    # def analysis_page(cls, doc):
    #     pages = []
    #     items = doc.find('#navcnt')
    #     if items.find('a').size() < 1:
    #         return 0
    #     items.find('.pn').remove()
    #     a_list = items.find('a')
    #     for a in a_list:
    #         pages.append('https://www.google.com.sg' + pq(a).attr('href').strip())
    #     return pages
    #
    # a标签解析

    @classmethod
    def analysis_page(cls, doc):
        pages = []
        items = doc.find('#foot')
        if items.find('a').size() < 1:
            return 0
        items.find('.pnnext').remove()
        a_list = items.find('a')
        for a in a_list:
            pages.append('https://www.google.com.hk' + pq(a).attr('href').strip())
            # print('https://www.google.com.hk' + pq(a).attr('href').strip())
        return pages

    # 日期转换
    @classmethod
    def format_date(cls, time):
        day = ''
        if len(time[1]) < 2:
            day += '0' + time[1]
        else:
            day = time[1]
        date = ''
        date += time[2] + '-'
        if 'Jan' == time[0]:
            date += '01' + '-' + day
        if 'Feb' == time[0]:
            date += '02' + '-' + day
        if 'Mar' == time[0]:
            date += '03' + '-' + day
        if 'Apr' == time[0]:
            date += '04' + '-' + day
        if 'May' == time[0]:
            date += '05' + '-' + day
        if 'Jun' == time[0]:
            date += '06' + '-' + day
        if 'Jul' == time[0]:
            date += '07' + '-' + day
        if 'Aug' == time[0]:
            date += '08' + '-' + day
        if 'Sept' == time[0]:
            date += '09' + '-' + day
        if 'Oct' == time[0]:
            date += '10' + '-' + day
        if 'Nov' == time[0]:
            date += '11' + '-' + day
        if 'Dec' == time[0]:
            date += '12' + '-' + day
        return date


# 得到新闻结果页html
def search_news(page):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " +
                             "Chrome/54.0.2840.99 Safari/537.36"}
    # params 接收一个字典或者字符串的查询参数，字典类型自动转换为url编码，不需要urlencode()
    response = requests.get(page, headers=headers)
    return response.text


# NewsByBaidu.analysis_html("cosco", 597)
# NewsByGoogle.analysis_html("cosco", 597, '2019-12-03')


# 谷歌搜索新闻源
class NewsByGoogleWithSplash(object):

    @classmethod
    def search_news(cls, key):
        print(key)
        lua = '''
        function main(splash, args)
            local treat = require("treat")
            local response = splash:http_get("https://www.google.com.sg/search?q=cosco&tbm=nws&tbs=qdr:y")
                return {
                    html=treat.as_string(response.body),
                    url=response.url,
                    status=response.status
                }
        end
        '''
        url = 'http://localhost:8050/execute?lua_source=' + quote(lua)
        response = requests.get(url)
        print(response.text)

    # PyQuery 解析
    @classmethod
    def analysis_html(cls, key):
        doc = pq(NewsByGoogle.search_news(key))
        pages = NewsByGoogle.analysis_page(doc)
        print(len(pages))
        if pages == 0:
            # print(pages)
            news = NewsByGoogle.analysis_news(doc, key)
            print('None')
            print(len(news))
            print(news)
        else:
            news = NewsByGoogle.analysis_news(doc, key)
            for page in pages:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " +
                                  "Chrome/54.0.2840.99 Safari/537.36"}
                print(page)
                print(pq(requests.get(page, headers).text))
                for item in NewsByGoogle.analysis_news(pq(requests.get(page, headers).text), key):
                    i = 0
                    i += 1
                    print(i)
                    news.append({'title': item['title'], 'content': item['content'], 'keyword': item['keyword'],
                                 'url': item['url'], 'time': item['time'], 'source': item['source']})
            print('Next')
            print(len(news))
            print(news)
            # print(len(pages))
            # print(pages)
        return news
        # print(soup.find_all(attrs={'class': 'result'}))

    # 新闻解析
    @classmethod
    def analysis_news(cls, doc, key):
        news = []
        items = doc('.g').items()
        for item in items:
            # print(item)
            href = item('h3').find('a').attr('href').strip()
            title = item('h3').text().strip()
            if 'ago' in item.find('.slp').text().strip().split('-')[1]:
                time = Time.strftime('%Y-%m-%d', Time.localtime(Time.time()))
                print(time)
            else:
                time = item.find('.slp').text().strip().split('-')[1]
                time = NewsByGoogle.format_date(time.replace(',', '').split(' '))
                print(time)
            content = item.find('.st').text().strip()
            # source 1为百度 0为谷歌
            news.append({'title': title, 'content': content, 'url': href, 'keyword': key,
                         'time': time.replace('年', '-').replace('月', '-').replace('日', ''), 'source': 0})
        # print(news)
        return news

    # a标签解析
    @classmethod
    def analysis_page(cls, doc):
        pages = []
        items = doc.find('#navcnt')
        if items.find('a').size() < 1:
            print(0)
            return 0
        items.find('.pn').remove()
        a_list = items.find('a')
        for a in a_list:
            pages.append('https://www.google.com.sg' + pq(a).attr('href').strip())
        print(pages)
        return pages

    # 日期转换
    @classmethod
    def format_date(cls, time):
        day = ''
        if len(time[1]) < 2:
            day += '0' + time[1]
        else:
            day = time[1]
        date = ''
        date += time[2] + '-'
        if 'Jan' == time[0]:
            date += '01' + '-' + day
        if 'Feb' == time[0]:
            date += '02' + '-' + day
        if 'Mar' == time[0]:
            date += '03' + '-' + day
        if 'Apr' == time[0]:
            date += '04' + '-' + day
        if 'May' == time[0]:
            date += '05' + '-' + day
        if 'Jun' == time[0]:
            date += '06' + '-' + day
        if 'Jul' == time[0]:
            date += '07' + '-' + day
        if 'Aug' == time[0]:
            date += '08' + '-' + day
        if 'Sept' == time[0]:
            date += '09' + '-' + day
        if 'Oct' == time[0]:
            date += '10' + '-' + day
        if 'Nov' == time[0]:
            date += '11' + '-' + day
        if 'Dec' == time[0]:
            date += '12' + '-' + day
        return date
