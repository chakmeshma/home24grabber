import pickle

sellers = dict()

with open('sellerinfos', 'rb') as file_obj:
    sellers = pickle.load(file_obj)

seller_keys = sellers.keys()

for seller_key in seller_keys:
    seller = sellers[seller_key]
    print('{}\n\tEmail: {}\n\tPhone: {}'.format(seller['name'], seller['email'], seller['phone']))
