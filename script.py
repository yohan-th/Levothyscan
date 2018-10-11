import urllib.request
import re
import sys
import csv
import threading
import timeit
import unicodedata
import time


# Parametre
search = "levothyrox"
rubrique = "18*sante"
debug = False

def clean_message(messages):
    if debug:
        print("clean message")
    clean_msg_all = []
    for msg in messages:
        if debug:
            print("--- CLEAN MSG :")
            print(msg)
        msg = re.sub(',', ' ', msg)  # Pour un decoupage correct sur excel
        msg = re.sub('>', ' ', msg, 1)
        msg = re.sub('<div.*?</div>', ' ', msg)  # suppr les citations
        msg = re.sub('<img.*?/>', ' ', msg)  #suppr les images
        msg = re.sub('<br.*?>', ' ', msg) #suppr les balise br
        msg = re.sub('<a (.*?)</a>', ' ', msg) #suppr les liens externe
        msg = re.sub('</?span.*?>', ' ', msg)
        msg = re.sub('</?table.*?>', ' ', msg)
        msg = re.sub('</?[a-z][a-z]?>', ' ', msg) #</i> <lu> et bien d'autre
        msg = re.sub('&[a-z#0-9]{1,4};', ' ', msg) #&#034; &nbsp; &euro; &gt; &lt;
        msg = re.sub('\[#[0-9]+ size=[0-9]+\]', ' ', msg)
        msg = re.sub('</?strong>', ' ', msg)
        msg = re.sub('</?div>?', ' ', msg)
        #msg = re.sub('\.+', ' ', msg)
        while re.search(" ['\w^.><?!)(/@*_&%:+\-]{0,4} ", msg):
            msg = re.sub(" ['\w^.><?!)(/@*_&%:;+\-]{0,4} ", ' ', msg)
        msg = unicodedata.normalize('NFD', msg).encode('ascii', 'ignore')  # suppr les accents
        if debug:
            print("--- CLEAN FINAL")
            print("--->   \033[91m"+str(msg)+ '\033[0m')
        clean_msg_all.append(msg)
    return(clean_msg_all)



class GetAllPages_topic_Thread(threading.Thread):

    def __init__(self, url, page, nb_page, sujet):
        threading.Thread.__init__(self)
        self.url = url
        self.page = page
        self.nb_page = nb_page
        self.sujet = sujet

    def run(self):
        if debug:
            print("[Ouverture URL de \"" + self.sujet + "\" page " + str(page) + "]")
        try:
            with urllib.request.urlopen(self.url) as rep:
                html = rep.read().decode('utf-8')
        except (http.client.IncompleteRead) as e:
            html = e.partial.decode('utf-8')
        messages_page = clean_message(re.findall(r"</td.*?itemprop=\"text\"(.*?)class=\"clear\"", html))
        pseudo_all_message = re.findall(r"itemprop=\"name\".*?>(.*?)</span", html, re.MULTILINE | re.DOTALL)
        date_all_message = re.findall(r"topic_posted.*?le (.*?)&nbsp;", html, re.MULTILINE | re.DOTALL)
        if debug:
            print("["+str(len(messages_page))+" messages à la page "+str(self.page)+"]")
        i = 0
        while i < len(messages_page):
            if re.match(".*DOC_cryptlink.*", pseudo_all_message[i]):
                pseudo_all_message[i] = re.sub("<span.*?>", "", pseudo_all_message[i])
            if debug:
                print("<\033[92m" + pseudo_all_message[i] + "\033[0m>")
            message_infos = [messages_page[i], pseudo_all_message[i], date_all_message[i], self.url]
            all_messages.append(message_infos)
            i += 1
        if debug:
            print("[" + str(len(messages_page)) + " new msg sur \"" + self.sujet + "\" de la page " + str(self.page) + " sur " + self.nb_page + "]")




def get_nbr_page(html):
    list_pages = re.search('pagination_main_visible(.+?)/div', html).group(1)
    if re.match(r".*href.*", list_pages):
        return(re.findall("\">([0-9]+)<", html)[-1])
    else:
        return("1")



start = timeit.default_timer()
print("Recherche de <"+search+"> dans la rubrique <"+rubrique+">")
if debug:
    print('http://forum.doctissimo.fr/search_result.php?post_cat_list='+rubrique+'&search='+search+'&resSearch=250')
with urllib.request.urlopen('http://forum.doctissimo.fr/search_result.php?post_cat_list='+rubrique+'&search='+search+'&resSearch=250') as response:
   html = response.read().decode('utf-8')
if re.match(r".*aucune réponse n'a été trouvée.*", html, re.MULTILINE|re.DOTALL):
    print("La recherche de <"+search+"> dans la rubrique <"+rubrique+"> donne aucun résultat")
    sys.exit()
nb_page_topic = get_nbr_page(html)

print(nb_page_topic+" page(s) sur le sujet <"+search+"> dans la rubrique <"+rubrique+"> (limité à 100 topics par page)")

all_topics_url = []
page = 1
if debug:
    nb_page_topic = "1"
while page <= int(nb_page_topic):
    print("telechargement de page " + str(page) + " sur " + nb_page_topic)
    if debug:
        print('http://forum.doctissimo.fr/search_result.php?post_cat_list='+rubrique+'&search='+search+'&resSearch=250&page='+str(page))
    with urllib.request.urlopen('http://forum.doctissimo.fr/search_result.php?post_cat_list='+rubrique+'&search='+search+'&resSearch=250&page='+str(page)) as response:
        html = response.read().decode('utf-8')
    topics = re.findall(r"</?t.*?sujet ligne_booleen(.+?)</tr>", html, re.MULTILINE | re.DOTALL)
    for topic in topics:
        if debug:
            print(re.search(r"href=\"(.+?)\"", topic).group(1))
        all_topics_url.append(re.search(r"href=\"(.+?)\"", topic).group(1))
    page += 1
print("nb de topic = " + str(len(all_topics_url)))


all_messages = [['Message', 'Pseudo', 'Date', 'URL']]


threadList = []
i = 0
valou = True
for url in all_topics_url:
    if debug:
        time.sleep(2)
    with urllib.request.urlopen(url) as response:
        html = response.read().decode('utf-8')
    nb_page_topic = get_nbr_page(html)
    sujet_topic = re.search("itemprop=\"headline\"(.*?)<", html).group(1)
    if debug:
        print("topic \""+sujet_topic+"\" avec "+str(nb_page_topic)+" page(s)")
    if int(nb_page_topic) > 10:
        print("WARNING : topic \""+sujet_topic+"\" contient "+str(nb_page_topic)+" pages. Risque probable de perte de 50 messages sur",int(nb_page_topic)*50, "pour chaque erreur ci-dessous :")
        print("          Code erreur \"ConnectionResetError: [WinError 10054] An existing connection was forcibly closed by the remote host\"")
    page = 1
    while page <= int(nb_page_topic):
        clean_url = re.search(r"(.*)_", url).group(1)
        if debug:
            print(clean_url+"_"+str(page)+".htm")
        newthread = GetAllPages_topic_Thread(clean_url + "_" + str(page) + ".htm", page, nb_page_topic, sujet_topic)
        newthread.start()
        time.sleep(0.1)
        threadList.append(newthread)
        page += 1
    i += 1
    print(str(i) + " topics extrait sur " + str(len(all_topics_url)) + ". Messages récoltés : " + str(len(all_messages)))
    if len(all_messages) > 1000 and valou == True:
        with open('output_tmp.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(all_messages)
        valou = False


print("Attente des threats")
for curThread in threadList :
    curThread.join()

stop = timeit.default_timer()
m, s = divmod(stop - start, 60)
h, m = divmod(m, 60)
print(str(len(all_messages)) + " messages total récoltés en %dh %02dmin et %02ds" % (h, m, s))

with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerows(all_messages)
