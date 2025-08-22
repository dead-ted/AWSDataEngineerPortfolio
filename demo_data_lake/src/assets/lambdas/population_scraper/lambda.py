import json
import os
import boto3
from typing import Tuple, List
from datetime import datetime, timezone
from tempfile import mkdtemp
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_PATH = os.environ.get("S3_PATH", "")
DATA_URL = os.environ.get("DATA_URL", "")
CHROME_DRIVER = os.environ.get("CHROME_DRIVER", "")
CHROME_BINARY = os.environ.get("CHROME_BINARY", "")
LOCAL = os.environ.get("LOCAL", "")

s3 = boto3.client("s3")

def validate_row_length(validation_header:List, validation_rows:List[List]) -> bool:
    """
    Check if the data collected from each row matches the length of the header
    """
    for x in validation_rows:
        if len(x) != len(validation_header):
            return False
    return True

def create_s3_key(path_prefix: str, scrape_time: datetime, suffix: str, file_type: str = "json") -> str:
    """
    Generate an S3 key with year/month partitioning and timestamped filename.
    """
    # Example: "year=2025/month=08/2025-08-20_14-35-22_suffix.json"
    date_str = scrape_time.strftime("%Y-%m-%d_%H-%M-%S")
    key = f"{path_prefix.rstrip('/')}/year={scrape_time.year}/month={scrape_time.month:02d}/{date_str}_{suffix}.{file_type}"
    return key

def extract_most_populated_cities(driver, data_url:str, max_iter:int = 10) -> Tuple[List[str], List[List[str]]]:
    """
    Navigate to URL and extract cities ranked by population
    """
    driver.get(data_url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "wpr-table"))
        )

        # locate the table
        table = driver.find_element(By.CLASS_NAME, "wpr-table")

        # get table header
        headers = [th.text.strip() for th in table.find_elements(By.CSS_SELECTOR, "thead th")]
        if headers:
            print("Found table header for processing.")
        else:
            print("Can not find table header for processing.")
            raise Exception("Can not find table header for processing.")

        # get rows
        rows = []
        n = 0
        for tr in table.find_elements(By.CSS_SELECTOR, "tbody tr"):
            if n >= max_iter:
                break
            cells = [td.text.strip() for td in tr.find_elements(By.CSS_SELECTOR, "td")]
            rows.append(cells)
            n += 1

        if rows:
            print("Found cities from table scrape.")
        else:
            print("Can not find rows for cities")
            raise Exception("Can not find rows for cities.")



    except NoSuchElementException as e:
        print("Table or element not found:", e)
        return [], []
    except TimeoutException as e:
        print("Timed out waiting for table:", e)
        return [], []
    except StaleElementReferenceException as e:
        print("Element went stale during scrape:", e)
        return [], []
    except Exception as e:
        print("Unexpected error:", e)
        return [], []

    return headers, rows

def configure_chrome_driver() -> webdriver.Chrome:
    chrome_options = Options()
    chrome_options.binary_location = CHROME_BINARY#"/opt/chrome/chrome"
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1280x1696")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-dev-tools")
    chrome_options.add_argument("--no-zygote")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument(f"--user-data-dir={mkdtemp()}")
    chrome_options.add_argument(f"--data-path={mkdtemp()}")
    chrome_options.add_argument(f"--disk-cache-dir={mkdtemp()}")

    return webdriver.Chrome(
        options=chrome_options,
        service=ChromeService(CHROME_DRIVER) #"/opt/chromedriver"
    )

def configure_chrome_driver_local() -> webdriver.Chrome:
    tmp = mkdtemp()
    
    chrome_options = Options()
    chrome_options.binary_location = CHROME_BINARY
    chrome_options.add_argument("--headless")  # classic headless
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"--user-data-dir={tmp}")
    chrome_options.add_argument(f"--disk-cache-dir={tmp}")
    chrome_options.add_argument("--window-size=1280x1696")

    service = ChromeService(CHROME_DRIVER)
    return webdriver.Chrome(service=service, options=chrome_options)

def lambda_handler(event=None, context=None):
    now_utc = datetime.now(timezone.utc)

    s3_key = create_s3_key(S3_PATH, now_utc, "population_ranks")

    driver = None
    try:
        print("Starting WebDriver")

        if LOCAL:
            driver = configure_chrome_driver_local()
        else:
            driver = configure_chrome_driver()

        print("Extracting data from table")
        raw_header, raw_rows = extract_most_populated_cities(driver, DATA_URL, 100)
        
        if not raw_header or not raw_rows:
            raise Exception("Problem grabbing data.")
        
        if not validate_row_length(raw_header, raw_rows):
            raise Exception("Heder length not matching rows.")
        
        raw_json = [dict(zip(raw_header, row)) for row in raw_rows]
            

        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(raw_json),
            ContentType="application/json"
        )
        print("Upload to S3 successful")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Scraping and upload completed",
            })
        }

    except Exception as e:
        print("ERROR:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

    finally:
        if driver:
            driver.quit()
            print("WebDriver closed")

if __name__ == "__main__":
    lambda_handler({}, {})

    ######################################
    # add  power tools
    # custom metrics
    # alarm on custom metric
    ######################################