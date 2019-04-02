import os
import math
import json
import time
import requests
import lxml.html
from datetime import datetime

class CraigsAPI:
    def __init__(self, path_to_categories):
        self.num_results_pp = 120
        self.domain = 'https://toronto.craigslist.org/'
        self.login_url = 'https://accounts.craigslist.org/login'
        self.our_ads_url = 'https://accounts.craigslist.org/login/home'
        self.base_headers = {
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'Referer': 'https://www.google.com',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        self.ok_codes = [200, 301]
        self.category_dict = _get_categories_from_file(path_to_categories)

    def _get_categories_from_web(self, file_path=False):
        response = requests.get(self.domain, headers=headers)
        soup = BeautifulSoup(response.content)

        categories = soup.find('div', {'id': 'center'}).findChildren('div')
        links = []
        for category in categories:
            category_links = category.find_all('a')
            links += category_links

        link_dict = {link.text: link['href'] for link in links}

        if file_path:
            with open(file_path, 'w+') as outfile:
                json.dump(link_dict, outfile, indent=4)
                print('Generated Category File.')

        return link_dict

    def _get_categories_from_file(file_path):
        try:
            with open(file_path, 'r') as readfile:
                return json.load(readfile)
        except Exception as e:
            return _get_categories_from_web(file_path)

    def login(self, username, password):
        self._username = username
        self._password = password
        _ = _refresh_session(username, password)
        pass

    def _refresh_session(self, username, password):
        login_data = = {
              'step': 'confirmation',
              'rt': 'L',
              'rp': '/login/home',
              't': str(get_epoch_time()),
              'p': '0',
              'inputEmailHandle': username,
              'inputPassword': password
            }

        login_headers = self.base_headers.copy()
        login_headers['Origin'] = 'https://accounts.craigslist.org'
        login_headers['Referer'] = 'https://accounts.craigslist.org/login?rt=L&rp=%2Flogin%2Fhome'

        session = requests.session()
        response = session.post(self.login_url, headers=login_headers, data=login_data)
        if response.status_code in self.ok_codes:
            self.session = session
            print('Sucessful Login.')
        else:
            print('Failed to login.')

    def get_epoch_time(self):
        return round((datetime.now() - datetime(1970, 1, 1)).total_seconds())

    def get_our_postings(self):
        headers = headers.copy()
        response = self.session.get(self.our_ads_url, headers=headers)
        if response:
            content = lxml.html.fromstring(response.text)
            postings = content.xpath('//section[@class="body"][0]//table[0]/li/text()')
            return postings
        else:
            return None

    def post_our_ad(self):
        pass

    def get_ads(self, category, query=False, num_results, timer=1):
        num_pages = math.ceil(num_results / self.num_results_pp)

        if query:
            urls = [self.domain + self.category_dict[category] + '?s=%s&query=%s&sort=rel' % (int(counter)*120, \
                                                              query.replace(' ', '+')) \
                                                                for counter in range(num_pages)]
        else:
            urls = [self.domain + self.category_dict[category] + '?s=%s' % (int(counter)*120) for counter in range(num_pages)]

        ad_dict = {}
        for url in urls:
            response = requests.get(url, headers=headers)
            time.sleep(timer)
            page_dict = _parse_page_content(response)
            if len(page_dict) == 0:
                return ad_dict
            else:
                ad_dict.update(page_dict)
        return ad_dict

    def _parse_page_content(response):
        try:
            content = lxml.html.fromstring(response.text)

            page_links = content.xpath('//div[@class="content"]/ul[@class="rows"]//li/p/a/@href')
            page_infos = content.xpath('//div[@class="content"]/ul[@class="rows"]//li/p/a/text()')
            post_dates = content.xpath('//div[@class="content"]/ul[@class="rows"]//li/p/time/@datetime')

            # Optional Attributes
            prices = content.xpath('//div[@class="content"]/ul[@class="rows"]//li/span[@class="result-price"]')
            locations = [location.strip() if 'pic' not in location else '' \
             for location in content.xpath('//div[@class="content"]/ul[@class="rows"]//li/p/span[@class="result-meta"]/span[1]/text()[1]')]

            # Ensure Equal Lengths for Dictionary Generation
            assert len(page_links) == len(page_infos) == len(post_dates)

            dict_length = len(page_links)

            # Validation for Adding Attributes
            if len(prices) != dict_length:
                prices = [None] * dict_length

            if len(locations) != dict_length:
                locations = [None] * dict_length

            page_dict = {page_links[counter]: {'info': page_infos[counter], 'date': post_dates[counter], \
                                               'price': prices[counter], 'location': locations[counter]} \
                                                 for counter in range(dict_length)}
        except Exception as e:
            print('Error')
            return {}
