import pickle

with open('sellerinfos', 'rb') as file_obj:
    sellers = pickle.load(file_obj)

seller_keys = sellers.keys()

err_count = 0

with open('sellers.txt', 'w') as file_obj:
    for seller_key in seller_keys:
        try:
            seller = sellers[seller_key]
            file_obj.write('{}\n\tEmail: {}\n\tPhone: {}\n\n'.format(seller['name'], seller['email'], seller['phone']))
        except:
            err_count += 1

print(err_count)
