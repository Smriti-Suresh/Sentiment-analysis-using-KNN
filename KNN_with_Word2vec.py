
import pandas as pd
import re
import numpy as np
import scipy
import itertools
import matplotlib
import matplotlib.pyplot as plt
import gensim
from gensim.models import KeyedVectors
from smart_open import open
from scipy.spatial.distance import cdist
from collections import Counter
from random import choice

"""# **Preprocessing**"""

#Storing the training and test datasets into their respective dataframes
trained = pd.read_csv('./train.csv')
test = pd.read_csv('./test.csv')

#Creating a function that takes care of all the preprocessing stuff.
def preprocess():

  trained['Tweet'] = trained['Tweet'].str.lower() # Ensuring all words in the Tweet column of training data are lowercased
  test['Tweet'] = test['Tweet'].str.lower() # Ensuring all words in the Tweet column of test data are lowercased

  # Parsing the stop_words.txt file and storing all the words in a list.
  stopwords = []
  with open('stop_words.txt','r') as file:    
      for line in file:         
          for word in line.split():            
              stopwords.append(word)

  # Removing all stopwords from all the tweets in training data.
  trained["Tweet"] = trained["Tweet"].apply(lambda func: ' '.join(sw 
                                            for sw in func.split() 
                                            if sw not in stopwords))

  # Removing all stopwords from all the tweets in test data.
  test["Tweet"] = test["Tweet"].apply(lambda func: ' '.join(sw 
                                            for sw in func.split() 
                                            if sw not in stopwords))

  special_chars = ["!",'"',"%","&","amp","'","(",")", "*","+",",","-",".",
                  "/",":",";","<","=",">","?","[","\\","]","^","_",
                  "`","{","|","}","~","–","@","#","$"]

  #Training Data
  trained['Tweet'] = trained['Tweet'].str.replace(r'http?://[^\s<>"]+|www\.[^\s<>"]+', '') # Removing hyperlinks from all the tweets
  trained['Tweet'] = trained['Tweet'].str.replace('@[A-Za-z0-9]+', '') # Removing usernames from all the tweets.
  trained['Tweet'] = trained['Tweet'].str.replace(r'\B#\w*[a-zA-Z]+\w*', '') # Removing hashtags, including the text, from all the tweets
  trained['Tweet'] = trained['Tweet'].str.replace('\d+', '') # Removing numbers from all the tweets

  for c in special_chars:
      trained['Tweet'] = trained['Tweet'].str.replace(c,'') # Removing all special characters from all the tweets

  #Test Data
  test['Tweet'] = test['Tweet'].str.replace(r'http?://[^\s<>"]+|www\.[^\s<>"]+', '') # Removing hyperlinks from all the tweets
  test['Tweet'] = test['Tweet'].str.replace('@[A-Za-z0-9]+', '') # Removing usernames from all the tweets.
  test['Tweet'] = test['Tweet'].str.replace(r'\B#\w*[a-zA-Z]+\w*', '') # Removing hashtags, including the text, from all the tweets
  test['Tweet'] = test['Tweet'].str.replace('\d+', '') # Removing numbers from all the tweets

  for c in special_chars:
      test['Tweet'] = test['Tweet'].str.replace(c,'') # Removing all special characters from all the tweets

  #Training Data
  train_unique = (list(set(trained['Tweet'].str.findall("\w+").sum()))) # Finding all the unique words in training data's Tweet column
  train_unique_words = len(train_unique)

  #Test Data
  test_unique = (list(set(test['Tweet'].str.findall("\w+").sum()))) # Finding all the unique words in test data's Tweet column
  test_unique_words = len(test_unique)

  # Making an empty column in our test data for predicted labels.
  test['Predicted Label'] = ''

  print("Unique words in Training Data: {}".format(train_unique_words))
  print("Unique words in Test Data: {}".format(test_unique_words))

preprocess()

trained.head()

test.head()



word2vec = KeyedVectors.load_word2vec_format("./GoogleNews-vectors-negative300.bin.gz", binary=True)

"""# **Repeating Part 1 with Word2Vec**"""

def extract_features(sentence):
  words = [word for word in sentence.split() if word in word2vec.key_to_index]
  if words == []:
    return []
  else:
    return np.mean(word2vec[words],axis=0)

train_embeddings = []

for sentence in trained['Tweet']:
  words = extract_features(sentence)
  if words == []:
    trained = trained.drop(trained[trained.Tweet == sentence].index)
  else:  
    train_embeddings.append(words)

trained = trained.reset_index()

test_embeddings = []

for sentence in test['Tweet']:
  words = extract_features(sentence)
  if len(words) == 0:

    test = test.drop(test[test.Tweet == sentence].index)
  else:  
    test_embeddings.append(words)

test = test.reset_index()

print("Shape of Training Matrix: ({0} , {1})".format(len(train_embeddings),len(train_embeddings[0])))
print("Shape of Test Matrix: ({0} , {1})".format(len(test_embeddings),len(test_embeddings[0])))

#Calculating distances between every test instance with all the train instances. This returns a 2D distances vector.
dists = cdist(test_embeddings,train_embeddings,'euclidean')

# Making a general structure of our confusion matrix
cmatrix = pd.DataFrame({'Gold Positive': '', 'Gold Neutral': '', 'Gold Negative': ''},
                       index = ['Predicted Positive','Predicted Neutral','Predicted Negative'])

# Lists that will later store respective values for plotting
accuracy_list = []
recall_list = []
precision_list = []
F1_list = []

#Function that takes a list and returns the mode of the list. If there are more than one modes, it randomly selects any of them.
def get_mode(l):
    counting = Counter(l)
    max_count = max(counting.values())
    return choice([ks for ks in counting if counting[ks] == max_count])

def cmatrix_measures(k,dists,test,cmatrix):

  row_count = 0
  first_max = 0
  second_max = 0
  check_tie = False

  for ls in dists:
    sorted_distances_indices = np.argsort(ls) #Getting a sorted list of indices of all distances in ls with the smallest distance's index at 0th position
    knn_indices = []
    knn_indices = list(itertools.islice(sorted_distances_indices,k)) #Extracting the indices of the k-smallest distances

    knn_labels = []
    for i in knn_indices:
      label = trained['Sentiment'][i] #Extracting the label of the instance by indexing it through the DataFrame.
      knn_labels.append(label) #Appending the label to our labels list.

    max_class = get_mode(knn_labels)
    first_max = max_class
    second_max = max(knn_labels)
    if first_max == second_max:
      check_tie = True
    predicted_label = max_class
    test.at[row_count, 'Predicted Label'] = predicted_label


    row_count += 1

  #Creating a frequency DataFrame that will store value counts for each tuple of instances. E.g (positive,positive = 309) and so on for all other seven instances.
  testfreqdf = test.groupby(["Sentiment", "Predicted Label"]).size().reset_index(name="Frequency")
  testfreqdf

  #Extracting values from the Frequency DataFrame and assigning to specific cells in the confusion matrix.
  cmatrix['Gold Positive']['Predicted Positive'] = testfreqdf['Frequency'][8]
  cmatrix['Gold Neutral']['Predicted Positive'] = testfreqdf['Frequency'][5]
  cmatrix['Gold Negative']['Predicted Positive'] = testfreqdf['Frequency'][2]
  cmatrix['Gold Positive']['Predicted Neutral'] = testfreqdf['Frequency'][7]
  cmatrix['Gold Neutral']['Predicted Neutral'] = testfreqdf['Frequency'][4]
  cmatrix['Gold Negative']['Predicted Neutral'] = testfreqdf['Frequency'][1]
  cmatrix['Gold Positive']['Predicted Negative'] = testfreqdf['Frequency'][6]
  cmatrix['Gold Neutral']['Predicted Negative'] = testfreqdf['Frequency'][3]
  cmatrix['Gold Negative']['Predicted Negative'] = testfreqdf['Frequency'][0]

  #Extracting all three True Positives from the matrix to measure accuracy.
  TP = cmatrix['Gold Positive']['Predicted Positive']
  TNT = cmatrix['Gold Neutral']['Predicted Neutral']
  TN = cmatrix['Gold Negative']['Predicted Negative']
  total = testfreqdf['Frequency'].sum()
  accuracy = ((TP+TNT+TN)/total)*100
  accuracy = round(accuracy,2)
  accuracy_list.append(accuracy)

  recall_pos = cmatrix['Gold Positive']['Predicted Positive']/cmatrix['Gold Positive'].sum()
  recall_neut = cmatrix['Gold Neutral']['Predicted Neutral']/cmatrix['Gold Neutral'].sum()
  recall_neg = cmatrix['Gold Negative']['Predicted Negative']/cmatrix['Gold Negative'].sum()
  macroaveraged_recall = ((recall_pos+recall_neut+recall_neg)/3)*100
  macroaveraged_recall = round(macroaveraged_recall,2)
  recall_list.append(macroaveraged_recall)

  precision_pos = cmatrix['Gold Positive']['Predicted Positive']/(cmatrix.iloc[0,0:3].sum())
  precision_neut = cmatrix['Gold Neutral']['Predicted Neutral']/(cmatrix.iloc[1,0:3].sum())
  precision_neg = cmatrix['Gold Negative']['Predicted Negative']/(cmatrix.iloc[2,0:3].sum())
  macroaveraged_precision = ((precision_pos+precision_neut+precision_neg)/3)*100
  macroaveraged_precision = round(macroaveraged_precision,2)
  precision_list.append(macroaveraged_precision)

  F1_pos = (2*precision_pos*recall_pos)/(precision_pos+recall_pos)
  F1_neut = (2*precision_neut*recall_neut)/(precision_neut+recall_neut)
  F1_neg = (2*precision_neg*recall_neg)/(precision_neg+recall_neg)
  F1_score = ((F1_pos + F1_neut + F1_neg)/3)*100  
  F1_score = round(F1_score,2)
  F1_list.append(F1_score)
  

  print("\n\nConfusion Matrix with k = {}:\n".format(k))
  print(cmatrix)
  print("\nAccuracy with k = {0}: {1}%".format(k,accuracy))
  print("Macroaveraged Precision with k = {0}: {1}%".format(k,macroaveraged_precision))
  print("Macroaveraged Recall with k = {0}: {1}%".format(k,macroaveraged_recall))
  print("Macroaveraged F1-score with k = {0}: {1}%\n".format(k,F1_score))

cmatrix_measures(1,dists,test,cmatrix)
cmatrix_measures(3,dists,test,cmatrix)
cmatrix_measures(5,dists,test,cmatrix)
cmatrix_measures(7,dists,test,cmatrix)
cmatrix_measures(10,dists,test,cmatrix)

"""# **Plotting Part 1 Results with Word2Vec**"""

k_list = [1,3,5,7,10] 

fig = plt.figure(figsize=(12,8))

plt.subplot(2,2,1)
plt.plot(k_list,accuracy_list)
plt.title("Accuracy as KNN increase",fontsize='x-large')
plt.xlabel("k Nearest Neighbors",fontsize='large')
plt.ylabel("Accuracy",fontsize='large')

plt.subplot(2,2,2)
plt.plot(k_list,recall_list)
plt.title("Recall as KNN increase",fontsize='x-large')
plt.xlabel("k Nearest Neighbors",fontsize='large')
plt.ylabel("Recall",fontsize='large')

plt.subplot(2,2,3)
plt.plot(k_list,precision_list)
plt.title("Precision as KNN increase",fontsize='x-large')
plt.xlabel("k Nearest Neighbors",fontsize='large')
plt.ylabel("Precision",fontsize='large')

plt.subplot(2,2,4)
plt.plot(k_list,F1_list)
plt.title("F1 as KNN increase",fontsize='x-large')
plt.xlabel("k Nearest Neighbors",fontsize='large')
plt.ylabel("F1",fontsize='large')

fig.subplots_adjust(hspace=.5)

plt.show

"""#**Repeating Part 2 with Word2Vec**"""

# Storing the training and test datasets into their respective dataframes

trained = pd.read_csv('train.csv')
test = pd.read_csv('test.csv')

"""# **Preprocessing**"""

#Storing the training and test datasets into their respective dataframes
trained = pd.read_csv('train.csv')
test = pd.read_csv('test.csv')
preprocess()

def extract_features(sentence):
  words = [word for word in sentence.split() if word in word2vec.index_to_key]
  if words == []:
    return []
  else:
    return np.mean(word2vec[words],axis=0)

train_embeddings = []

for sentence in trained['Tweet']:
  words = extract_features(sentence)
  if len(words) == 0:

    trained = trained.drop(trained[trained.Tweet == sentence].index)
  else:  
    train_embeddings.append(words)

test_embeddings = []

for sentence in test['Tweet']:
  words = extract_features(sentence)
  if words == []:
    test = test.drop(test[test.Tweet == sentence].index)
  else:  
    test_embeddings.append(words)

from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn import metrics
from sklearn.metrics import classification_report, confusion_matrix

acc_list = []
rec_list = []
prec_list = []
f1_list = []

def classifying(trainfeatures,testfeatures):

  X_train = trainfeatures 
  X_test = testfeatures
  y_train = trained.iloc[:,0].values
  y_test = test.iloc[:,0].values

  for k in [1,3,5,7,10]:

    classifier = KNeighborsClassifier(n_neighbors=k,algorithm='brute')
    classifier.fit(X_train, y_train)
    predicted_label = classifier.predict(X_test)

    accuracy_score = (metrics.accuracy_score(y_test,predicted_label))
    accuracy_score = (round(accuracy_score,2))*100
    acc_list.append(accuracy_score)

    cmatrix = confusion_matrix(y_test, predicted_label)
    creport = classification_report(y_test, predicted_label)

    macro_precision = (metrics.precision_score(y_test, predicted_label, average='macro'))
    macro_precision = (round(macro_precision,2))*100
    prec_list.append(macro_precision)

    macro_recall = (metrics.recall_score(y_test, predicted_label, average='macro'))
    macro_recall = (round(macro_recall,2))*100
    rec_list.append(macro_recall)
    
    macro_f1 = (metrics.f1_score(y_test, predicted_label, average='macro'))
    macro_f1 = (round(macro_f1,2))*100
    f1_list.append(macro_f1)

    print("\n\nConfusion Matrix for k = {} is:\n".format(k))
    print(cmatrix)
    print("\nClassification Report for k = {} is:\n".format(k))
    print(creport)
    print("Accuracy Score for k = {0} is: {1}%".format(k,accuracy_score))
    print("Macroaveraged Recall for k = {0} is: {1}%".format(k,macro_recall))
    print("Macroaveraged Precision for k = {0} is: {1}%".format(k,macro_precision))
    print("Macroaveraged F1-score for k = {0} is: {1}%".format(k,macro_f1))

classifying(train_embeddings,test_embeddings)

"""# **Plotting Part 2 Results with Word2Vec**"""

k_ls = [1,3,5,7,10] 

fig = plt.figure(figsize=(12,8))

plt.subplot(2,2,1)
plt.plot(k_ls,acc_list)
plt.title("Accuracy as KNN increase",fontsize='x-large')
plt.xlabel("k Nearest Neighbors",fontsize='large')
plt.ylabel("Accuracy",fontsize='large')

plt.subplot(2,2,2)
plt.plot(k_ls,rec_list)
plt.title("Recall as KNN increase",fontsize='x-large')
plt.xlabel("k Nearest Neighbors",fontsize='large')
plt.ylabel("Recall",fontsize='large')

plt.subplot(2,2,3)
plt.plot(k_ls,prec_list)
plt.title("Precision as KNN increase",fontsize='x-large')
plt.xlabel("k Nearest Neighbors",fontsize='large')
plt.ylabel("Precision",fontsize='large')

plt.subplot(2,2,4)
plt.plot(k_ls,f1_list)
plt.title("F1 as KNN increase",fontsize='x-large')
plt.xlabel("k Nearest Neighbors",fontsize='large')
plt.ylabel("F1",fontsize='large')

fig.subplots_adjust(hspace=.5)

plt.show

