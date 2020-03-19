import pandas as pd
import nltk as nlp
from nltk.corpus import stopwords
from string import punctuation
from multiprocessing import Pool, cpu_count
from sklearn.feature_extraction.text import TfidfVectorizer

# results are different
# faster
def norm(text):
    text = text.translate(str.maketrans('', '', punctuation))
    text = text.lower()
    text = nlp.word_tokenize(text)
    stop_words = set(stopwords.words('russian'))
    text = [word for word in text if word not in stop_words]
    lemmatizer = nlp.WordNetLemmatizer()
    roots = [lemmatizer.lemmatize(each) for each in text]

    return ' '.join(roots)


data = pd.read_csv('texts.csv').values.tolist()
data = [x[0] for x in data]

p = Pool(cpu_count()-1)
processed = p.map(norm, data)
vectorizer = TfidfVectorizer(max_features=3000) # over 12k without limit
X = vectorizer.fit_transform(processed)
df = pd.DataFrame(X.todense().tolist(), columns=vectorizer.get_feature_names())
df.to_csv('processed.csv', index=False)

#import re
#import pymorphy2
#def norm(s):
#    morph = pymorphy2.MorphAnalyzer()
#    s = re.sub(r'[\d\$\%\#\@\№\^&\*]', '', s)
#
#    return ' '.join([morph.parse(i)[0].normal_form for i in s.split(' ')])
