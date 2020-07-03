
import requests
import re
import random
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from lxml.html import fromstring
from itertools import cycle
import traceback
import pymongo
import argparse
import json

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
ua=UserAgent()

mongoclient = pymongo.MongoClient("mongodb+srv://Mycle:Piterpiter@cluster0-dqqoe.mongodb.net/test?retryWrites=true&w=majority")
db = mongoclient["amazon_data"]

def get_proxies():
    with open('proxy.txt') as f:
        proxylist = f.read().splitlines()
    return proxylist

proxies = get_proxies()
proxy_pool = cycle(proxies)

def get_converted_price(price):
    converted_price = float(re.sub(r"[^\d.]", "", price.split('-')[0]))
    return converted_price

def extract_url(url):
    if url.find("www.amazon.com") != -1:
        index = url.find("/dp/")
        print(index,'gp')
        if index != -1:
            index2 = index + 14
            url = "https://www.amazon.com" + url[index:index2]
        else:
            index = url.find("/gp/")
            print(index,'gp')
            if index != -1:
                index2 = index + 22
                url = "https://www.amazon.com" + url[index:index2]
            else:
                url = None
    else:
        url = None
    return url

def get_product_details(url):
    details = {
        'breadcrumb': '',
    }
    
    headers = {'User-Agent': ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
            'Accept-Encoding': 'none',
            'Accept-Language': 'en-US,en;q=0.8',
            'Connection': 'keep-alive'
            }
    _url = extract_url(url)
    if _url is None:
        details = None
    else:
        # try:
        response = requests.get(_url, headers=headers)
        soup = BeautifulSoup(response.content, "html5lib")
        try:
            breadcrumbs = soup.find('ul', attrs = {'class':'a-unordered-list a-horizontal a-size-small'}).findAll('li')
            sub_breadcrumb = ''
            for breadcrumb in breadcrumbs:
                sub_breadcrumb += breadcrumb.get_text().strip() + ' '
            details["breadcrumb"] = sub_breadcrumb[:-1]
        except:
            details["breadcrumb"] = ''
                
        product_urls = []
        radio_titles = []
        prefix_url = _url.split('/dp/')[0]
        try:
            selected_radio = soup.find('ul', attrs = {'class':'a-unordered-list a-nostyle a-button-list a-declarative a-button-toggle-group a-horizontal a-spacing-top-micro swatches swatchesSquare imageSwatches'}).find('li', attrs = {'class':'swatchSelect'})
            radio_titles.append(selected_radio.get('title').replace('Click to select ', ''))
            product_urls.append(_url)
            
            radiogroups = soup.find('ul', attrs = {'class':'a-unordered-list a-nostyle a-button-list a-declarative a-button-toggle-group a-horizontal a-spacing-top-micro swatches swatchesSquare imageSwatches'}).findAll('li', attrs = {'class':'swatchAvailable'})
            for radio in radiogroups:
                product_urls.append(prefix_url + radio.get('data-dp-url'))
                radio_titles.append(radio.get('title').replace('Click to select ', ''))
        except:
            pass
        
        if len(product_urls) == 0:
            product_urls.append(_url)
            radio_titles.append('general')
        
        # for product_url, radio_title in product_urls, radio_titles:
        for i in range(len(product_urls)):
            product_url = product_urls[i]
            radio_title = radio_titles[i]
            radio_title_dict = {}
            
            price = None
            title = None
            feature_bullets = []
            product_detail = {}
            plain_text = ''
            
            try:
                response = requests.get(product_url, headers=headers)
                soup = BeautifulSoup(response.content, "html5lib")
        
                plain_text = response.text
                # price
                try:
                    price = soup.find(id="priceblock_dealprice") or soup.find(id='priceblock_saleprice')
                    radio_title_dict['price'] = price.get_text().strip()
                except:
                    radio_title_dict['price'] = None
                # title
                try:
                    title = soup.find(id="productTitle")
                    radio_title_dict['productTitle'] = title.get_text().strip()
                except:
                    radio_title_dict['productTitle'] = None
                # by info
                try:
                    by_info = soup.find(id="bylineInfo")
                    radio_title_dict['byInfo'] = by_info.get_text().strip()
                except:
                    radio_title_dict['byInfo'] = None
                # star
                try:
                    star = soup.find(id="acrPopover").find('span', attrs = {'class':'a-icon-alt'})
                    radio_title_dict['star'] = star.get_text().strip().split(' ')[0]
                except:
                    radio_title_dict['star'] = None
                # customer review
                try:
                    customer_review = soup.find(id="acrCustomerReviewText")
                    radio_title_dict['customerReview'] = customer_review.get_text().strip().split(' ')[0].replace(',', '')
                except:
                    radio_title_dict['customerReview'] = None
                # answered question
                try:
                    answered_question = soup.find(id="askATFLink")
                    radio_title_dict['answeredQuestion'] = answered_question.get_text().strip().split(' ')[0]
                except:
                    radio_title_dict['answeredQuestion'] = None
                # price saving
                try:
                    price_saving = soup.find(id="regularprice_savings").find('td', attrs = {'class':'a-span12 a-color-price a-size-base priceBlockSavingsString'})
                    radio_title_dict['priceSaving'] = price_saving.get_text().strip()
                except:
                    radio_title_dict['priceSaving'] = None
                # discard
                try:
                    discard = soup.find('div', attrs = {'class':'a-section maple-banner__text'})
                    radio_title_dict['discard'] = discard.get_text().strip()
                except:
                    radio_title_dict['discard'] = None
                # shipping message
                try:
                    shipping_messages = soup.find(id="price-shipping-message")
                    radio_title_dict['shippingMessage'] = shipping_messages.get_text().strip().replace('\n', '')
                except:
                    radio_title_dict['shippingMessage'] = None
                # size
                try:
                    size = soup.find(id="variation_size_name").find('span', attrs = {'class':'selection'})
                    radio_title_dict['size'] = size.get_text().strip()
                except:
                    pass
                # color
                try:
                    color = soup.find(id="variation_color_name").find('span', attrs = {'class':'selection'})
                    radio_title_dict['color'] = color.get_text().strip()
                except:
                    pass
                # product description
                try:
                    product_description = soup.find(id="productDescription").find('p')
                    radio_title_dict['productDescription'] = product_description.get_text().strip()
                except:
                    radio_title_dict['productDescription'] = None
                
                if not radio_title_dict['productDescription']:
                    try:
                        product_description = soup.find('div', attrs = {'class':'celwidget aplus-module 3p-module-b'})
                        radio_title_dict['productDescription'] = product_description.get_text().strip()
                    except:
                        radio_title_dict['productDescription'] = None
                    
                # product detail
                product_detail_dict = {}
                try:
                    product_details = soup.find(id="detail-bullets").find('ul').findAll('li')
                    for product_sub_detail in product_details:
                        sub_detail = product_sub_detail.get_text().strip()
                        try:
                            p_key = sub_detail.split(':')[0].strip()
                            if p_key != 'Customer Reviews':
                                p_value = sub_detail.split(':')[1].strip().replace('\n', '').replace(".zg_hrsr { margin", '')
                                product_detail_dict[p_key] = p_value
                        except Exception as e:
                            continue     
                    radio_title_dict['productDetail'] = product_detail_dict
                except:
                    radio_title_dict['productDetail'] = {}
                    
                if not bool(radio_title_dict['productDetail']):
                    try:
                        product_details = soup.find(id="productDetails_detailBullets_sections1").findAll('tr')
                        for product_sub_detail in product_details:
                            try:
                                p_key = product_sub_detail.find('th').get_text().strip()
                                if p_key != 'Customer Reviews':
                                    p_value = product_sub_detail.find('th').find_next_sibling("td").get_text().strip()
                                    product_detail_dict[p_key] = p_value
                            except Exception as e:
                                continue
                        radio_title_dict['productDetail'] = product_detail_dict
                    except:
                        radio_title_dict['productDetail'] = {}
                # small image urls
                try:
                    small_img_urls = soup.find(id="altImages").findAll('img')
                except:
                    small_img_urls = []
                try:
                    feature_bullets = soup.find('ul', attrs = {'class':'a-unordered-list a-vertical a-spacing-mini'}).findAll('span', attrs = {'class':'a-list-item'})
                except:
                    feature_bullets = []
                
                if radio_title_dict['price'] is None:
                    radio_title_dict['price'] = soup.find(id='color_name_0_price').get_text().strip()
                    # details["deal"] = False    
                if price is None:
                    radio_title_dict['price'] = soup.find(id="priceblock_ourprice").get_text().strip()
                    # details["deal"] = False
            except Exception as e:
                if price is None or title is None:
                    for i in range(1):
                        proxy = random.choice(proxies)
                        try:
                            response = requests.get(product_url, headers=headers, proxies={"http": proxy, "https": proxy}, timeout=15)
                            soup = BeautifulSoup(response.content, "html5lib")
        
                            plain_text = response.text
                            # price
                            try:
                                price = soup.find(id="priceblock_dealprice") or soup.find(id='priceblock_saleprice')
                                radio_title_dict['price'] = price.get_text().strip()
                            except:
                                radio_title_dict['price'] = None
                            # title
                            try:
                                title = soup.find(id="productTitle")
                                radio_title_dict['productTitle'] = title.get_text().strip()
                            except:
                                radio_title_dict['productTitle'] = None
                            # by info
                            try:
                                by_info = soup.find(id="bylineInfo")
                                radio_title_dict['byInfo'] = by_info.get_text().strip()
                            except:
                                radio_title_dict['byInfo'] = None
                            # star
                            try:
                                star = soup.find(id="acrPopover").find('span', attrs = {'class':'a-icon-alt'})
                                radio_title_dict['star'] = star.get_text().strip().split(' ')[0]
                            except:
                                radio_title_dict['star'] = None
                            # customer review
                            try:
                                customer_review = soup.find(id="acrCustomerReviewText")
                                radio_title_dict['customerReview'] = customer_review.get_text().strip().split(' ')[0].replace(',', '')
                            except:
                                radio_title_dict['customerReview'] = None
                            # answered question
                            try:
                                answered_question = soup.find(id="askATFLink")
                                radio_title_dict['answeredQuestion'] = answered_question.get_text().strip().split(' ')[0]
                            except:
                                radio_title_dict['answeredQuestion'] = None
                            # price saving
                            try:
                                price_saving = soup.find(id="regularprice_savings").find('td', attrs = {'class':'a-span12 a-color-price a-size-base priceBlockSavingsString'})
                                radio_title_dict['priceSaving'] = price_saving.get_text().strip()
                            except:
                                radio_title_dict['priceSaving'] = None
                            # discard
                            try:
                                discard = soup.find('div', attrs = {'class':'a-section maple-banner__text'})
                                radio_title_dict['discard'] = discard.get_text().strip()
                            except:
                                radio_title_dict['discard'] = None
                            # shipping message
                            try:
                                shipping_messages = soup.find(id="price-shipping-message")
                                radio_title_dict['shippingMessage'] = shipping_messages.get_text().strip().replace('\n', '')
                            except:
                                radio_title_dict['shippingMessage'] = None
                            # size
                            try:
                                size = soup.find(id="variation_size_name").find('span', attrs = {'class':'selection'})
                                radio_title_dict['size'] = size.get_text().strip()
                            except:
                                pass
                            # color
                            try:
                                color = soup.find(id="variation_color_name").find('span', attrs = {'class':'selection'})
                                radio_title_dict['color'] = color.get_text().strip()
                            except:
                                pass
                            # product description
                            try:
                                product_description = soup.find(id="productDescription").find('p')
                                radio_title_dict['productDescription'] = product_description.get_text().strip()
                            except:
                                radio_title_dict['productDescription'] = None
                            
                            if not radio_title_dict['productDescription']:
                                try:
                                    product_description = soup.find('div', attrs = {'class':'celwidget aplus-module 3p-module-b'})
                                    radio_title_dict['productDescription'] = product_description.get_text().strip()
                                except:
                                    radio_title_dict['productDescription'] = None
                                
                            # product detail
                            product_detail_dict = {}
                            try:
                                product_details = soup.find(id="detail-bullets").find('ul').findAll('li')
                                for product_sub_detail in product_details:
                                    sub_detail = product_sub_detail.get_text().strip()
                                    try:
                                        p_key = sub_detail.split(':')[0].strip()
                                        if p_key != 'Customer Reviews':
                                            p_value = sub_detail.split(':')[1].strip().replace('\n', '').replace(".zg_hrsr { margin", '')
                                            product_detail_dict[p_key] = p_value
                                    except Exception as e:
                                        continue     
                                radio_title_dict['productDetail'] = product_detail_dict
                            except:
                                radio_title_dict['productDetail'] = {}
                                
                            if not bool(radio_title_dict['productDetail']):
                                try:
                                    product_details = soup.find(id="productDetails_detailBullets_sections1").findAll('tr')
                                    for product_sub_detail in product_details:
                                        try:
                                            p_key = product_sub_detail.find('th').get_text().strip()
                                            if p_key != 'Customer Reviews':
                                                p_value = product_sub_detail.find('th').find_next_sibling("td").get_text().strip()
                                                product_detail_dict[p_key] = p_value
                                        except Exception as e:
                                            continue
                                    radio_title_dict['productDetail'] = product_detail_dict
                                except:
                                    radio_title_dict['productDetail'] = {}
                            # small image urls
                            try:
                                small_img_urls = soup.find(id="altImages").findAll('img')
                            except:
                                small_img_urls = []
                            try:
                                feature_bullets = soup.find('ul', attrs = {'class':'a-unordered-list a-vertical a-spacing-mini'}).findAll('span', attrs = {'class':'a-list-item'})
                            except:
                                feature_bullets = []
                            if radio_title_dict['price'] is None:
                                radio_title_dict['price'] = soup.find(id='color_name_0_price').get_text().strip()
                                # details["deal"] = False    
                            if radio_title_dict['price'] is None:
                                price = soup.find(id="priceblock_ourprice").get_text().strip()
                                # details["deal"] = False 
                            if radio_title_dict['price'] is not None or radio_title_dict['productTitle'] is not None:
                                break
                        except Exception as e:
                            pass
    
            if len(small_img_urls) > 0:
                radio_title_dict["smallImages"] = []
                radio_title_dict["largeImages"] = []
                for img in small_img_urls:
                    img_url = img.get('src')
                    if img_url[-3:] != 'gif' and 'play' not in img_url:
                        radio_title_dict["smallImages"].append(img_url)
                        try:
                            split_text = '"thumb":"' + img_url + '","large":"'
                            large_url = plain_text.split(split_text)[1].split('"')[0]
                        except:
                            large_url = img_url
                        radio_title_dict["largeImages"].append(large_url)
                    
            if len(feature_bullets) > 0:       
                radio_title_dict["bullets"] = []         
                for feature_bullet in feature_bullets:
                    bullet = re.sub(u"(\u2018|\u2019)", "'", feature_bullet.get_text().strip())
                    radio_title_dict["bullets"].append(bullet.replace('\\', ''))
                if "Make sure this fits" in radio_title_dict["bullets"][0]:
                    radio_title_dict["bullets"].pop(0)

            details[radio_title] = json.dumps(radio_title_dict)
    return details

def save_to_mongo(document):
    '''
    Saves or Updates Mongo db
    document : type: Dictionary

    '''
    collection = db['scrapped_data']
    data = collection.find_one({'url':document.get('url')})
    if data:
        data['shipping_message'] = document.get('shipping_message')
        data['small_img_urls'] = document.get('small_img_urls')
        data['large_img_urls'] = document.get('large_img_urls')
        data['feature_bullets'] = document.get('feature_bullets')
        data.update()
    else:
        data = collection.insert_one(document)
    return data

def main_scrapper(product_url):
# if __name__ == '__main__':
    #product_url = "https://www.amazon.com/Vivii-velas-llama-velas-falsas-bater%C3%ADa/dp/B01MQ1Q3R1?pf_rd_r=CTEWXXM0ZRPGERP822HK&pf_rd_p=277a7e11-1bef-478c-bd76-67176c3b2794&pd_rd_r=6da7826a-b855-499d-b424-230e25bc6416&pd_rd_w=PZTfw&pd_rd_wg=Vi9dp&ref_=pd_gw_unk"
    # parser = argparse.ArgumentParser(
    #     description='Simple scraper to extract all products from Amazon')
    # parser.add_argument('--url', '-u' , default='',help='URL of the Amazon site')
    # args = parser.parse_args()
    # product_url = args.url
    data = get_product_details(product_url)
    flagged_data = save_to_mongo(data)
    # print(data)
    return data