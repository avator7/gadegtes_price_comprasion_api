from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from difflib import SequenceMatcher
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

app = FastAPI()


def get_similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()



def get_chrome_driver():
    options = uc.ChromeOptions()
    options.headless = True
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    driver = uc.Chrome(options=options)
    return driver

def scrape_product_data(search_term: str):
    driver = get_chrome_driver()
    driver.get("https://www.gadgets360.com/")

    try:
        driver.find_element(By.CLASS_NAME, '_sricn').click()
        search_input = driver.find_element(By.ID, 'searchtext')
        search_input.send_keys(search_term)
        search_input.send_keys(Keys.RETURN)
        time.sleep(2)

        products = driver.find_elements(By.CSS_SELECTOR, "#productSearch ul li")

        best_match = None
        best_score = 0.0
        for product in products:
            try:
                title_el = product.find_element(By.CSS_SELECTOR, "a.rvw-title")
                title = title_el.text.strip()
                score = get_similarity(search_term, title)
                if score > best_score:
                    best_score = score
                    best_match = title_el
            except Exception:
                continue

        if best_match:
            best_match.click()
            time.sleep(2)
        else:
            print("No matching product found.")
            driver.quit()
            return {}

        # Extracting Specs
        specs = {}
        try:
            specs_block = driver.find_element(By.ID, "overview")
            specs_items = specs_block.find_elements(By.CSS_SELECTOR, "li._flx")
            for item in specs_items:
                key = item.find_element(By.CSS_SELECTOR, "span._ttl").text.strip()
                value = item.find_element(By.CSS_SELECTOR, "span._vltxt").text.strip()
                specs[key] = value
        except Exception as e:
            print("Specs not found:", e)

        # Extracting Store Prices
        price_dict = []
        try:
            store_products = driver.find_elements(By.CSS_SELECTOR, "ul._prcbx > li")
            for product in store_products:
                store_span = product.find_element(By.CSS_SELECTOR, "._storwrp span._stor")
                store_class = store_span.get_attribute("class")
                store_name = [cls.replace("_", "").capitalize() for cls in store_class.split() if cls.startswith("_") and cls != "_stor"][0]
                buy_link = product.find_element(By.CSS_SELECTOR, "._buybtn a").get_attribute("href")
                price = product.find_element(By.CSS_SELECTOR, "._prc").text.strip()
                price_dict.append({"Store_name": store_name, "Price": price, "Buy_link": buy_link})
        except Exception as e:
            print("Price data not found:", e)

        # Extracting News
        news_list = []
        news_items = driver.find_elements(By.CSS_SELECTOR, "#newslist ul > li")
        for item in news_items:
            try:
                headline = item.find_element(By.CSS_SELECTOR, "div.txtp").text.strip()
                news_list.append(headline)
            except:
                news_list.append("No news")

        # Extracting Ratings
        review_ratings = {}
        try:
            ratings = driver.find_elements(By.CSS_SELECTOR, "ul._rwrtng li")
            for rating in ratings:
                category = rating.find_element(By.TAG_NAME, "span").text.strip()
                class_attr = rating.find_element(By.TAG_NAME, "i").get_attribute("class")
                score = int([cls[1:] for cls in class_attr.split() if cls.startswith("r")][0])
                review_ratings[category] = score
        except Exception as e:
            print("Error extracting rating:", e)

        # Extracting Pros and Cons
        pros, cons = [], []
        try:
            lists = driver.find_elements(By.CSS_SELECTOR, "div._pdqty ul")
            pros = [li.text.strip() for li in lists[0].find_elements(By.TAG_NAME, "li")[1:]]
            cons = [li.text.strip() for li in lists[1].find_elements(By.TAG_NAME, "li")[1:]]
        except Exception as e:
            print("Error extracting pros and cons:", e)

        driver.quit()

        product_info = {
            "Stores": price_dict,
            "News": news_list,
            "Specs": specs,
            "ReviewRatings": review_ratings,
            "Pros": pros,
            "Cons": cons
        }

        return product_info

    except Exception as main_e:
        print("Critical error occurred:", main_e)
        driver.quit()
        return {}



@app.get("/")
def root():
    return {"message": "API is live!"}

@app.get("/scrape")
def scrape(query: str = Query(..., description="Product name to search")):
    data = scrape_product_data(query)
    return JSONResponse(content=data)
