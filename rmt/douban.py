import re
import sys
import requests
import urllib.parse

class Douban():
	# 电影查询api以及头文件
	def __init__(self,tmdb_name):
		self.headers = {
			'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36',
			'Host' : 'movie.douban.com',
		}
		self.search_url = 'https://movie.douban.com/j/subject_suggest?q={}'
		self.name = tmdb_name
    # 名称检查
	def name_check(self):
		en_re = re.compile(r'[A-Za-z]', re.S)
		res = re.findall(en_re, self.name)
		if res == []:
			return False
		else:
			return True
	# 外部调用
	def run(self):
		name = self.name
		# requests获取搜索结果
		try:
			res = requests.get(self.search_url.format(urllib.parse.quote(name)), headers=self.headers)
			results = res.json()
		except:
			pass
		if len(results) == 0:
			return name
		else:
			#使用第一个搜索结果
			douban_name = results[0].get('title')
			season_re = re.compile('第*\S*季')
			season_name = re.findall(season_re, douban_name)
			if season_name == []:
				return douban_name
			else:
				douban_name = douban_name.replace(season_name[0],"")
				douban_name = douban_name.rstrip()
				return douban_name
