
from datetime import datetime
from math import log, exp, sqrt,factorial
import pickle

# TL; DR
# the main learning process start at line 122


# parameters #################################################################

#train = '../data/train.csv'  # path to training file
#label = '../data/trainLabels.csv'  # path to label file of training data
#test = '../data/test.csv'  # path to testing file

#D = 2 ** 24  # number of weights use for each model, we have 32 of them
#alpha = .1   # learning rate for sgd optimization

class best_online_model:

    def __init__(self,train='../data/train.csv',label = '../data/trainLabels.csv',test= '../data/trainLabels.csv',D= 2 ** 24,alpha= .1,predict_y14=True,output_file='./submissiontk36x.csv'):
        self.train=train
        self.label=label
        self.test=test
        self.D=D
        self.alpha=alpha
        self.hash_cols = [131,132,133,136,35,65,61,62,91,92,142,3,4,61,34,91,94,95]
        self.hh=len(self.hash_cols)
        self.hh=self.hh*(self.hh-1)/2+1
        self.predict_y14=predict_y14
        self.output_file=output_file

# function, generator definitions ############################################

# A. x, y generator
# INPUT:
#     path: path to train.csv or test.csv
#     label_path: (optional) path to trainLabels.csv
# YIELDS:
#     ID: id of the instance (can also acts as instance count)
#     x: a list of indices that its value is 1
#     y: (if label_path is present) label value of y1 to y33

    def data(self,path, label_path=None):
        
        badfeatures=[15,76,82,17,131,132,133,136,134,78,48,79,109,21,18,108,35,65,61,62,91,92,142,3,4,61,34,91,94,95,142,43,2,23,22,113,114,53,54,138,139, 96, 97, 98, 99,  100,  19,  29,  36, 37, 38, 39, 122, 110, 120, 121, 123, 124, 125, 59, 52, 50, 7, 6, 8, 9,  145, 122, 39, 38, 37, 36]
        for t, line in enumerate(open(path)):
            # initialize our generator
        
            if t == 0:
                # create a static x,
                # so we don't have to construct a new x for every instance
              
                x = [0] * (146+self.hh+32)
                if label_path:
                    label = open(label_path)
                    label.readline()  # we don't need the headers
                continue
        # parse x
            for m, feat in enumerate(line.rstrip().split(',')):
                if m == 0:
                    ID = int(feat)
                elif m in badfeatures:              
                    x[m] =-10
                else:
                # one-hot encode everything with hash trick
                # categorical: one-hotted
                # boolean: ONE-HOTTED
                # numerical: ONE-HOTTED!
                # note, the build in hash(), although fast is not stable,
                #       i.e., same value won't always have the same hash
                #       on different machines
                    x[m] = abs(hash(str(m) + '_' + feat)) % self.D
        # parse y, if provided
            row=line.rstrip().split(',')
        
            t = 146
            for i in xrange(len(self.hash_cols)):
                for j in xrange(i+1,len(self.hash_cols)):
                    t += 1
                    x[t] = abs(hash(str(i)+'_'+str(j)+'_'+row[self.hash_cols[i]]+"_x_"+row[self.hash_cols[j]])) % self.D
        
        
                
            if label_path:
                # use float() to prevent future type casting, [1:] to ignore id
                y = [float(y) for y in label.readline().split(',')[1:]]
            yield (ID, x, y) if label_path else (ID, x)


# B. Bounded logloss
# INPUT:
#     p: our prediction
#     y: real answer
# OUTPUT
#     bounded logarithmic loss of p given y
    def logloss(self,p, y):
        p = max(min(p, 1. - 10e-15), 10e-15)
        return -log(p) if y == 1. else -log(1. - p)


# C. Get probability estimation on x
# INPUT:
#     x: features
#     w: weights
# OUTPUT:
#     probability of p(y = 1 | x; w)
    def predict2(self,x, w):
        wTx = 0.
        for i in x[:146+self.hh]:  # do wTx
            if i <0:
                continue
            wTx += w[i] * 1.
        for c,i in enumerate(x[146+self.hh:]):  # do wTx
        
            wTx += w[self.D+c] * i  # w[i] * x[i], but if i in x we got x[i] = 1.
        return 1. / (1. + exp(-max(min(wTx, 20.), -20.)))  # bounded sigmoid
    def predict(self,x, w):
        wTx = 0.
        for i in x[:146+self.hh]:  # do wTx
            if i <0:
                continue
            wTx += w[i] * 1.  # w[i] * x[i], but if i in x we got x[i] = 1.
    
        return 1. / (1. + exp(-max(min(wTx, 20.), -20.)))  # bounded sigmoid


# D. Update given model
# INPUT:
# alpha: learning rate
#     w: weights
#     n: sum of previous absolute gradients for a given feature
#        this is used for adaptive learning rate
#     x: feature, a list of indices
#     p: prediction of our model
#     y: answer
# MODIFIES:
#     w: weights
#     n: sum of past absolute gradients
    def update(self,alpha, w, n, x, p, y):
        for i in x[:146+self.hh]:
            if i <0:
                continue
        # alpha / sqrt(n) is the adaptive learning rate
        # (p - y) * x[i] is the current gradient
        # note that in our case, if i in x then x[i] = 1.
            n[i] += abs(p - y)
            w[i] -= (p - y) * 1. * alpha / sqrt(n[i])
   
    def update2(self,alpha, w, n, x, p, y):
    
        for c,i in enumerate(x[146+self.hh:]):
        # alpha / sqrt(n) is the adaptive learning rate
        # (p - y) * x[i] is the current gradient
        # note that in our case, if i in x then x[i] = 1.
            n[self.D+c] += abs((p - y) * i) 
            w[self.D+c] -= (p - y) * i * alpha/7  # /2 is good!


# training and testing #######################################################
    def train_predict(self):
        start = datetime.now()

# a list for range(0, 33) - 13, no need to learn y14 since it is always 0
        K = [k for k in range(33) if k != 13]

# initialize our model, all 32 of them, again ignoring y14
        w = [[0.] * (self.D+32) if k != 13 else None for k in range(33)]
        n = [[0.] * (self.D+32) if k != 13 else None for k in range(33)]

        loss = 0.
        loss2 = 0.
        loss_y14 = log(1. - 10**-15)

        for ID, x, y in self.data(self.train, self.label):

    # get predictions and train on all labels
            P=[]
            for k in K:
                p = self.predict(x, w[k])
                P.append(p)
       # update(alpha, w[k], n[k], x, p, y[k])
                if k<13:
                    x[146+self.hh+k]=p
                else:
                    x[145+self.hh+k]=p
                loss += self.logloss(p, y[k]) 
            for k,p in zip(K,P):
                p2 = self.predict2(x, w[k])
                self.update(self.alpha, w[k], n[k], x, p2, y[k])
                self.update2(self.alpha, w[k], n[k], x, p2, y[k])
                loss2 += self.logloss(p2, y[k])  
            loss += loss_y14  # the loss of y14, logloss is never zero
            loss2 += loss_y14
    # print out progress, so that we know everything is working
            if ID % 10000 == 0:
        
                print('%s encountered: %d current logloss: %f  logloss2: %f' % (
                    datetime.now(), ID, (loss/33.)/ID,(loss2/33.)/ID))
   
           
        with open(self.output_file, 'w') as outfile:
            outfile.write('id_label,pred\n')
    
            for ID, x in self.data(self.test):
                for k in K:
                    p = self.predict(x, w[k])
                    if k<13:
                        x[146+self.hh+k]=p
                    else:
                        x[145+self.hh+k]=p
                for k in K:
                    p = self.predict2(x, w[k])
                    outfile.write('%s_y%d,%s\n' % (ID, k+1, str(p)))
                    if k == 12 and self.predict_y14:
                        outfile.write('%s_y14,0.0\n' % ID)

        print('Done, elapsed time: %s' % str(datetime.now() - start))
        
        
            
if __name__ == "__main__":
    best_online=best_online_model(train='../../data-sample/train.csv',label = '../../data-sample/trainLabels.csv',test= '../../data-sample/test.csv',D= 2 ** 24,alpha= .1,output_file='sample.csv')
    best_online.train_predict()
