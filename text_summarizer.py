import sys
import json
import nltk
nltk.download('punkt')
nltk.download('stopwords')
import numpy
import requests
from boilerpy3 import extractors
import pickle
import newspaper
from newspaper import Article



def summarize(url=None, html=None, n=100, cluster_threshold=5, top_sentences=10):

    # Adapted from "The Automatic Creation of Literature Abstracts" by H.P. Luhn
    #
    # Parameters:
    # * n  - Number of words to consider
    # * cluster_threshold - Distance between words to consider
    # * top_sentences - Number of sentences to return for a "top n" summary
            
    # Begin - nested helper function
    def score_sentences(sentences, important_words):
        scores = []
        sentence_idx = -1

    
        for s in [nltk.tokenize.word_tokenize(s) for s in sentences]:
    
            sentence_idx += 1
            word_idx = []
    
            # For each word in the word list...
            for w in important_words:
                try:
                    # Compute an index for important words in each sentence
    
                    word_idx.append(s.index(w))
                except ValueError: # w not in this particular sentence
                        pass
    
            word_idx.sort()
    
            # It is possible that some sentences may not contain any important words
            if len(word_idx)== 0: continue
    
            # Using the word index, compute clusters with a max distance threshold
            # for any two consecutive words
    
            clusters = []
            cluster = [word_idx[0]]
            i = 1
            while i < len(word_idx):
                if (word_idx[i]) - (word_idx[i - 1]) < cluster_threshold:
                    cluster.append(word_idx[i])
                else:
                    clusters.append(cluster[:])
                    cluster = [word_idx[i]]
                i += 1
            clusters.append(cluster)

            # Score each cluster. The max score for any given cluster is the score 
            # for the sentence.
    
            max_cluster_score = 0
            for c in clusters:
                significant_words_in_cluster = len(c)
                total_words_in_cluster = (c[-1]) - (c[0]) + 1
                score = 1.0 * significant_words_in_cluster \
                    * significant_words_in_cluster / total_words_in_cluster
    
                if score > max_cluster_score:
                    max_cluster_score = score
    
            scores.append((sentence_idx, score))
    
        return scores    
    
    # End - nested helper function
    
    extractor = extractors.ArticleExtractor()

    # It's entirely possible that this "clean page" will be a big mess. YMMV.
    # The good news is that the summarize algorithm inherently accounts for handling
    # a lot of this noise.

    txt = extractor.get_content_from_url(url)
    
    sentences = [s for s in nltk.tokenize.sent_tokenize(str(txt))]
    normalized_sentences = [s.lower() for s in sentences]

    words = [
        w.lower() 
        for sentence in normalized_sentences
            for w in
                nltk.tokenize.word_tokenize(sentence)
    ]

    fdist = nltk.FreqDist(words)

    top_n_words = [w[0] for w in fdist.items() 
            if w[0] not in nltk.corpus.stopwords.words('english')][:n]

    scored_sentences = score_sentences(normalized_sentences, top_n_words)

    # Summarization Approach 1:
    # Filter out nonsignificant sentences by using the average score plus a
    # fraction of the std dev as a filter

    avg = numpy.mean([s[1] for s in scored_sentences])
    std = numpy.std([s[1] for s in scored_sentences])
    mean_scored = [
    (sent_idx, score) 
        for (sent_idx, score) in scored_sentences 
            if score > avg + 0.5 * std
    ]

    # Summarization Approach 2:
    # Another approach would be to return only the top N ranked sentences

    top_n_scored = sorted(scored_sentences, key=lambda s: s[1])[-top_sentences:]
    top_n_scored = sorted(top_n_scored, key=lambda s: s[0])

    # Decorate the post object with summaries

    return dict(top_n_summary=[sentences[idx] for (idx, score) in top_n_scored],
                mean_scored_summary=[sentences[idx] for (idx, score) in mean_scored])
    

def summarize_nltk_text(raw_url):
    summary = summarize(raw_url)
    result_summary = " ".join(summary['mean_scored_summary'])
    return result_summary

def fake_news_or_not(url):
    with open('model.pkl', "rb") as file:
        model = pickle.load(file)

    article = Article(url)
    article.download()
    article.parse()
    article.nlp()
    news = article.summary

    pred = model.predict([news])

    fake_news_or_not = ""
    if pred[0] == 'FAKE':
        fake_news_or_not = 'This news article is likely not reliable'
    
    elif pred[0] == 'REAL':
        fake_news_or_not = 'This news article is likely reliable'

    return fake_news_or_not    
    

# ============================================================================================================