import re

def remove_script_tags(file):
	pattern = re.compile(r'<script[\s\S]+?/script>')
	subst = ""
	return re.sub(pattern, subst, file)

def clean_html(page):
	page = remove_script_tags(page)
	return page.replace("</sc'+'ript>", "").replace('</bo"+"dy>', '').replace('</ht"+"ml>', '')

def current_year():
	return 2021