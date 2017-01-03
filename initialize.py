import pickle
creds  = {'CIBInvestor':'CIB2016'}
with open('credentials.txt','wb') as f:
    pickle.dump(creds, f)