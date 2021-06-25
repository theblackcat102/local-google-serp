from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import urllib
from bs4 import BeautifulSoup as bs
from lxml import etree
from selenium.common.exceptions import TimeoutException as SE_TimeoutExepction
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException

from datetime import datetime,timezone

from .os_detect import OS as Os
SEARCH_PREFIX = '/search'
SEARCH_PREFIX_LEN = len(SEARCH_PREFIX)

DOMAIN = 'https://www.google.com'

RELATED_SEARCH_BOX = '/html/body/div[7]/div[1]/div[10]/div[1]/div/div[4]/div/div[1]/div/div'


def get_chrome_options_args(is_headless):
    chrome_options = Options()
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--lang=en-SG")
    chrome_options.add_experimental_option('prefs', {'intl.accept_languages': 'en,en_US'})

    if is_headless:
        chrome_options.add_argument("--headless")
    if (Os().wsl or Os().windows) and is_headless:
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-zygote")
        chrome_options.add_argument("--single-process")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    return chrome_options

def extract_quesionts(soup):
    related_questions = []
    for accordian_expanded in soup.findAll('g-accordion-expander'):
        
        question = accordian_expanded.find('div',{'role': 'button'}).text.strip()
        display_link = accordian_expanded.find('cite').text.strip()
        link = accordian_expanded.find('a') # we assume the link should rank first
        title = link.text.strip()
        link = link.get('href')
        snippet = accordian_expanded.find('div', {'data-attrid':"wa:/description"})
        if snippet:
            snippet = snippet.text                                    
        alt_search_link = None
        alt_search_query = None
        
        question = {
            'title': title,
            'displayed_link': display_link,
            'link': link, 
            'snippet': snippet
        }
        for a in accordian_expanded.findAll('a'):
            if SEARCH_PREFIX == a.get('href')[:SEARCH_PREFIX_LEN]:
                alt_search_link = a.get('href')
                alt_search_query = a.text.strip()
        
                question['question'] = alt_search_query
                question['question_link'] = alt_search_link
        
        related_questions.append(question)
    return related_questions

def extract_knowledge_graph(elem, dom):
    outputs = {}
    knowledge_graph = {}
    if elem.find('div', {'class': 'kp-wholepage'}):
        expandable_contents = []
        kp_wholepage_elem = elem.find('div', {'class': 'kp-wholepage'})        
        if kp_wholepage_elem.find('g-expandable-content'):
            for content in kp_wholepage_elem.findAll('g-expandable-content'):
                expandable_contents.append(content.text.strip())
        if len(expandable_contents) > 0:
            if 'knowledge_graph' not in outputs:
                outputs['knowledge_graph'] = {}
            outputs['knowledge_graph']['expanded_content'] = expandable_contents
        knowledge_graph = elem

        kg_title_xpath = '//*[contains(@class, "kp-wholepage")]/div[2]/div[2]/div/div/div/div[2]/h2/span'
        if len(dom.xpath(kg_title_xpath)):
            e = dom.xpath(kg_title_xpath)[0]
            kg_title = ''.join(e.itertext()).strip()
            outputs['title'] = kg_title

        data_attributes = elem.findAll('div', {'data-attrid': True})
        for attribute in data_attributes:
            attrid = attribute.get('data-attrid')
            if attrid is not None and attrid in ['description', 'subtitle']:
                continue
            spans = attribute.findAll('span')
            if len(spans) > 1:
                name, value = spans[0], spans[1]
                if value.find('span'):
                    outputs[name.text.strip()] = value.text.strip()
                elif len(value.findAll('a')) > 0:
                    name = name.text.strip()
                    outputs[name] = []
                    for a in value.findAll('a'):
                        link  = a.get('href')
                        outputs[name].append({
                            'value': a.text.strip(),
                            'link': DOMAIN+link if '/' == link[0] else link
                        })
                else:
                    outputs[name.text.strip()] = value.text.strip()

        kg_summary = '//*[@id="kp-wp-tab-overview"]/div[1]/div/div/div/div/div/div/div/div/span[1]'
        if len(dom.xpath(kg_summary)):
            e = dom.xpath(kg_summary)[0]
            kg_summary_text = ''.join(e.itertext()).strip()
            outputs['description'] = kg_summary_text
        # source
        source_xpath = '//*[@id="kp-wp-tab-overview"]/div[1]/div/div/div/div/div/div/div/div/span[2]/a'
        if len(dom.xpath(source_xpath)):
            e = dom.xpath(source_xpath)[0]
            source_link = e.get('href')
            data_source = ''.join(e.itertext()).strip()
            outputs['source'] = {
                "name": data_source,
                'link': source_link
            }

        people_also_search_for = []
        for t in knowledge_graph.findAll('div', {'data-reltype': 'sideways'}):
            data = {}
            if t.find('img'):
                data['image'] = t.find('img').get('src')
            if t.find('a'):
                data['link'] = t.find('a').get('href')
            data['name'] = t.text
            if len(data) > 1:
                people_also_search_for.append(data)
        
        if len(people_also_search_for) > 0:
            outputs['people_also_search_for'] = people_also_search_for
    return outputs

def extract_display_stats(full_dom):
    time_stats = '//*[@id="result-stats"]/nobr'
    e = full_dom.xpath(time_stats)
    if len(e) > 0:
        time_to_finish = ''.join(e[0].itertext()).strip()
        full_stats_xpath = '//*[@id="result-stats"]'
        e = full_dom.xpath(full_stats_xpath)
        full_stats_text = ''.join(e[0].itertext()).strip()
        total_result_text = full_stats_text.replace(time_to_finish, '')
        total_results = total_result_text.split(' ')[1]
        total = int(total_results.replace(',',''))
        
        time_to_finish_text = time_to_finish.replace('(','').split(' ')[0]
        time_taken_displayed = float(time_to_finish_text)
        return {
            'total_results': total,
            'time_taken_displayed': time_taken_displayed
        }
    return {}


chrome_options = get_chrome_options_args(True)
options = {
    'connection_timeout': None  # Never timeout, otherwise it floods errors
}

# to be implement : inline_videos, inline_images
def extract(url):
    has_question = False

    driver = webdriver.Chrome(
        executable_path='./chromedriver', seleniumwire_options=options,
        chrome_options=chrome_options
    )
    wait = WebDriverWait(driver, 30)
    driver.get(url)

    created_t = datetime.now(timezone.utc)

    body = driver.find_element_by_xpath("//body").text
    kg_expander = '/html/body/div[7]/div/div[9]/div[1]/div/div[2]/div[2]/div/div/div[1]/div/div/div[2]/div[4]/div/div/div/div[1]/div/div/div/div/div/div[2]/g-expandable-container/div/div[1]/div[1]/g-expandable-content[1]/span/div/g-text-expander/a'
    try:    
        if driver.find_element_by_xpath(kg_expander):
            button = driver.find_element_by_xpath(kg_expander)
            text = button.get_attribute('jsaction')
            if text:
                button.click()
    except (NoSuchElementException, ElementClickInterceptedException):
        pass

    full_dom = etree.HTML(driver.page_source)
    question_xpath = '/html/body/div[7]/div/div[9]/div[1]/div/div[2]/div[2]/div/div/div[2]/div/div/div/div[1]/div/div/g-accordion-expander/div[1]'
    for idx, e in enumerate(full_dom.xpath(question_xpath)):
        try:
            question_path = '/html/body/div[7]/div/div[9]/div[1]/div/div[2]/div[2]/div/div/div[2]/div/div/div/div[1]/div/div[{}]/g-accordion-expander/div[1]'.format(idx+1)
            button = driver.find_element_by_xpath(question_path)
            text = button.get_attribute('jsaction')
            if text:
                has_question = True
                button.click()
        except ElementClickInterceptedException:
            continue

    raw_html = driver.page_source
    soup = bs(raw_html,features="lxml")

    outputs = {}
    if has_question:
        outputs['question'] = extract_quesionts(soup)


    related_searches = []
    related_box = soup.find('div', {'data-abe':True})
    if related_box:
        for a in related_box.findAll('a'):
            if SEARCH_PREFIX == a.get('href')[:SEARCH_PREFIX_LEN]:
                query = a.text.strip()
                link = DOMAIN+ a.get('href')
                related_searches.append({
                    'query': query,
                    'link': link
                })
        if len(related_searches) > 0:
            outputs['related_searches'] = related_searches

    search_information = extract_display_stats(full_dom)    
    if len(search_information) > 0:
        outputs['search_information'] = search_information

    results= list(soup.findAll('div', {'class': 'g'}))
    organic_results = []
    for r in results:
        dom = etree.HTML(str(r))
        if r.find('div', {'class': 'kp-wholepage'}):
            knowledge_graph = extract_knowledge_graph(soup, full_dom)
            if len(knowledge_graph) > 0:
                outputs['knowledge_graph'] = knowledge_graph
        elif len(dom.xpath('//div/div[2]/div/div')) > 0 and len(dom.xpath('//div/div[1]/a/h3')) > 0:
            title = dom.xpath('//div/div[1]/a/h3')[0].text
            link = r.find('a').get('href')
            displayed_link = r.find('cite').text
            snippet = ''.join(dom.xpath('//div/div[2]/div/div')[0].itertext())
            title = title.replace(displayed_link, '')

            organic_results.append({
                'title': title,
                'snippet': snippet,
                'displayed_link': displayed_link,
                'link': link
            })
    if len(organic_results) > 0:
        outputs['organic_results'] = organic_results
    
    processed_t = datetime.now(timezone.utc)

    outputs['search_metadata'] = {
        "status": "Success",
        "total_time_taken": (processed_t - created_t).total_seconds(),
        "created_at": created_t.strftime('%Y-%m-%dT%H:%M:%S +UTC'),
        "processed_at": processed_t.strftime('%Y-%m-%dT%H:%M:%S +UTC'),
        "google_url": url,
    }

    return outputs


if __name__ == '__main__':
    from tqdm import tqdm
    keywords = [
        # 'Herman Miller與羅技電競椅', 
        'Palantir公司創辦人', 
        # 'Jeff Bezos的兄弟是誰', 'Jeff Bezos去太空', '亞馬遜第二任CEO', '亞馬遜森林環保', 
        # '亞馬遜森林的生態被破壞', '亞馬遜森林比例2017年', '巴西 2012年GDP成長率', '台灣2015年GDP成長率'
        # 'TikTok與字節跳動的2020', '2018關鍵字解析', '馬來西亞大學教授性騷擾', '性騷擾防制法', '金正恩妹妹', '北韓飢荒', '法國IKEA監視員工',
        # 'LGBT同志法案', 'C羅運動生涯', '大谷翔平老婆', '王柏融年薪', '台灣AZ 死亡案例', 
        # 'porsche 986 boxster 自排', 'posrche二手推薦',  '保時捷二手自排', '三洋機車二手','yamaha 機車二手', 'gogoro 機車價格', '120 cc 機車價格',
        # '街車', 'KTM Duke', '小綿羊', 'yamaha 鬼火', '台灣機車銷量','機車駕照','機車駕照體檢',

    ]
    for keyword in keywords:
        
        encode_query = urllib.parse.urlencode({'q': keyword})
        url = 'https://www.google.com/search?{}&oq=1111%E4%BA%BA%E5%8A%9B%E9%8A%80%E8%A1%8C&aqs=chrome.0.69i59j0l8.940j0j9&sourceid=chrome&ie=UTF-8'.format(encode_query)
        outputs = extract(url)
        print(keyword, list(outputs.keys()))

        print(outputs)

