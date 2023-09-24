import pickle

sellerids = set()

for sellerid in range(2000, 5001):
    sellerid_str = str(sellerid)
    sellerids.add(sellerid_str)

with open('sellerids_range', 'wb') as file_obj:
    pickle.dump(sellerids, file_obj)
