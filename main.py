import argparse
import os
import pickle
from concurrent.futures import ThreadPoolExecutor, wait
from requests import get
import urllib3

results_product_pages = set()
results_product_pages_file = 'products'
results_seller_ids = set()
results_seller_ids_file = 'sellerids'
results_seller_infos = dict()
results_seller_infos_file = 'sellerinfos'

max_sim_connection = 100
targets_head_url = [
    (156126, 46861)
]
http_pool = urllib3.PoolManager(max_sim_connection)


def reset_for_iteration():
    results_product_pages.clear()
    results_seller_ids.clear()
    results_seller_infos.clear()


def fetch_products(url: str):
    resp = http_pool.request('GET', url, retries=urllib3.Retry(10, 10, 10))

    try:
        respJson = resp.json()
        articles = respJson['data']['categories'][0]['categoryArticles']['articles']

        for article in articles:
            results_product_pages.add('https://www.home24.de/' + article['url'])
    finally:
        resp.release_conn()


def dispatch_head(_id_: int, _max_: int):
    url_temp = ('https://www.home24.de/graphql?extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C'
                '%22sha256Hash%22%3A%224c0db1839cdad663e84602f7172cfc894d8201a350ea42308caad436f056238e%22%7D%7D'
                '&variables=%7B%22urlParams%22%3A%22%22%2C%22locale%22%3A%22de_DE%22%2C%22first%22%3A{___FIRST___}%2C'
                '%22offset%22%3A{___OFFSET___}%2C%22id%22%3A%22{___ID___}%22%2C%22format%22%3A%22WEBP%22%2C'
                '%22sortingScore%22%3A%22A%22%2C%22userIP%22%3A%22{___USERIP___}%22%2C%22userAgent%22%3A%22Mozilla%2F5'
                '.0+%28Windows+NT+10.0%3B+Win64%3B+x64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Chrome%2F116'
                '.0.0.0+Safari%2F537.36%22%2C%22backend%22%3A%22ThirdParty%22%7D')

    executor = ThreadPoolExecutor(max_sim_connection)
    targets = set()
    futures = list()

    userip = get('https://api.ipify.org').content.decode('utf8')

    steps = 60

    for i in range(0, _max_, steps):
        endUrl = url_temp.format(
            ___FIRST___=steps,
            ___OFFSET___=i,
            ___ID___=_id_,
            ___USERIP___=userip
        )

        targets.add(endUrl)

    for target in targets:
        futures.append(executor.submit(fetch_products, target))

    wait(futures)

    executor.shutdown()


def extract_product_seller_id(htmldata: str):
    idStarterStr = '{&#x22;id&#x22;:&#x22;'
    idEnderStr = '&#x22'

    i = htmldata.index(idStarterStr) + len(idStarterStr)
    j = htmldata.index(idEnderStr, i)

    possibleID = htmldata[i:j]

    return possibleID


def extract_seller(url: str):
    resp = http_pool.request('GET', url)
    respStr = resp.data.decode('utf-8')

    sellerID = extract_product_seller_id(respStr)

    results_seller_ids.add(sellerID)

    resp.release_conn()


def extract_sellers_ids():
    executor = ThreadPoolExecutor(max_sim_connection)
    targets = set()
    futures = list()

    for product_page_url in results_product_pages:
        targets.add(product_page_url)

    for target in targets:
        futures.append(executor.submit(extract_seller, target))

    wait(futures)

    executor.shutdown()


def extract_seller_info(seller_id: str):
    url_template = ('https://www.home24.de/graphql?extensions={"persistedQuery":{"version":1,'
                    '"sha256Hash":"3dcfe845f42d3874ad8d180011f2db9baffb7e09b3596d25ea65d3f7a883a5dd"}}&variables={'
                    '"id":"_____seller__id______","locale":"de_DE"}')

    url = url_template.replace('_____seller__id______', seller_id)

    resp = urllib3.request('GET', url)

    needed_info = resp.json()['data']['shop']
    needed_info.pop('legalInfo', None)

    results_seller_infos[seller_id] = needed_info

    resp.release_conn()


def extract_sellers_info():
    executor = ThreadPoolExecutor(max_sim_connection)
    futures = list()

    for seller_id in results_seller_ids:
        futures.append(executor.submit(extract_seller_info, seller_id))

    wait(futures)

    executor.shutdown()


def append_results_file(new_results: set, file_name: str):
    if not os.path.isfile(file_name) or os.path.getsize(file_name) == 0:
        with open(file_name, 'wb') as file_obj:
            pickle.dump(set(), file_obj)

    with open(file_name, 'rb') as file_obj:
        current_results = pickle.load(file_obj)

    current_results_len = len(current_results)

    current_results.update(new_results)

    new_results_len = len(current_results)

    with open(file_name, 'wb') as file_obj:
        pickle.dump(current_results, file_obj)

    return (current_results_len, new_results_len)


# STARTS HERE

parser = argparse.ArgumentParser()
parser.add_argument('mode', type=str, help='operation mode',
                    choices=('get-products', 'extract-seller-ids', 'extract-seller-infos'))
parser.add_argument('-it', '--iterations', type=int)

args = parser.parse_args()

if args.mode == 'get-products':
    for it in range(0, args.iterations):
        print('Fetching product pages... [iteration {}]'.format(it + 1))
        for x in targets_head_url:
            dispatch_head(x[0], x[1])
        appendResult = append_results_file(results_product_pages, results_product_pages_file)
        print('Found {} new products\t ({} total)'.format(appendResult[1] - appendResult[0], appendResult[1]))
        reset_for_iteration()
elif args.mode == 'extract-seller-ids':
    for it in range(0, args.iterations):
        with open(results_product_pages_file, 'rb') as file_obj:
            results_product_pages = pickle.load(file_obj)
        print(
            'Extracting seller ids from {} product pages... [iteration {}]'.format(len(results_product_pages), it + 1))
        extract_sellers_ids()
        appendResult = append_results_file(results_seller_ids, results_seller_ids_file)
        print('Found {} new seller ids\t ({} total)'.format(appendResult[1] - appendResult[0], appendResult[1]))
        reset_for_iteration()

elif args.mode == 'extract-seller-infos':
    with open(results_seller_ids_file, 'rb') as file_obj:
        results_seller_ids = pickle.load(file_obj)
    print('Extracting seller infos from {} seller ids...'.format(len(results_seller_ids)))
    extract_sellers_info()
    print('Found {} seller info'.format(len(results_seller_infos)))
    with open(results_seller_infos_file, "wb") as f:
        pickle.dump(results_seller_infos, f)
    print('{} seller info'.format(len(results_seller_infos)) + ' saved.')
else:
    pass
