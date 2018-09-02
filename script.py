import urllib.request
import re
import sys
import csv
import threading
import time
import unicodedata


# Parametre
search = "levothyrox"
rubrique = "29*sante"
debug = False


def clean_message(messages):
    print("clean message")
    clean_msg_all = []
    for msg in messages:
        msg = re.sub(',', '', msg)  # Pour un decoupage correct sur excel
        msg = re.sub('<div.*?</div>', '', msg)  # suppr les citations
        msg = re.sub('<img.*?/>', '', msg)  #suppr les images
        msg = unicodedata.normalize('NFD', msg).encode('ascii', 'ignore')  # suppr les accents
        clean_msg_all.append(msg)
    return(clean_msg_all)

class ClientThread(threading.Thread):

    def __init__(self, url, page, nb_page, sujet):
        threading.Thread.__init__(self)
        self.url = url
        self.page = page
        self.nb_page = nb_page
        self.sujet = sujet

    def run(self):
        print("[Ouverture URL de \"" + self.sujet + "\" page " + str(page) + "]")
        try:
            with urllib.request.urlopen(self.url) as rep:
                html = rep.read().decode('utf-8')
        except (http.client.IncompleteRead) as e:
            html = e.partial.decode('utf-8')
        messages_page = clean_message(re.findall(r"</td.*?itemprop=\"text\"(.*?)class=\"clear\"", html))
        pseudo_all_message = re.findall(r"itemprop=\"name\">(.*?)/span", html, re.MULTILINE | re.DOTALL)
        date_all_message = re.findall(r"topic_posted.*?le (.*?)&nbsp;", html, re.MULTILINE | re.DOTALL)
        if debug:
            print("["+str(len(messages_page))+" messages à la page "+str(self.page)+"]")
        i = 0
        while i < len(messages_page):
            if re.match(".*DOC_cryptlink.*", pseudo_all_message[i]):
                pseudo_all_message[i] = re.search("\" >(.*?)<", pseudo_all_message[i]).group(1)
            message_infos = [messages_page[i], pseudo_all_message[i], date_all_message[i], self.url]
            all_messages.append(message_infos)
            i += 1
        print("[" + str(len(messages_page)) + " new msg sur \"" + self.sujet + "\" de la page " + str(self.page) + " sur " + self.nb_page + "]")


def get_nbr_page(html):
    list_pages = re.search('pagination_main_visible(.+?)/div', html).group(1)
    if re.match(r".*href.*", list_pages):
        return(re.findall("\">([0-9]+)<", html)[-1])
    else:
        return("1")


print("Recherche de <"+search+"> dans la rubrique <"+rubrique+">")
if debug:
    print('http://forum.doctissimo.fr/search_result.php?post_cat_list='+rubrique+'&search='+search+'&resSearch=100')
with urllib.request.urlopen('http://forum.doctissimo.fr/search_result.php?post_cat_list='+rubrique+'&search='+search+'&resSearch=100') as response:
   html = response.read().decode('utf-8')
if re.match(r".*aucune réponse n'a été trouvée.*", html, re.MULTILINE|re.DOTALL):
    print("La recherche donne aucune reponse")
    sys.exit()
nb_page_topic = get_nbr_page(html)

print(nb_page_topic+" page(s) sur le sujet <"+search+"> dans la rubrique <"+rubrique+"> (limité à 100 topics par page)")

all_topics_url = []
i = 1
while i <= int(nb_page_topic):
    print("telechargement de page " + str(i) + " sur " + nb_page_topic)
    if debug:
        print('http://forum.doctissimo.fr/search_result.php?post_cat_list='+rubrique+'&search='+search+'&resSearch=100&page='+str(i))
    with urllib.request.urlopen('http://forum.doctissimo.fr/search_result.php?post_cat_list='+rubrique+'&search='+search+'&resSearch=100&page='+str(i)) as response:
        html = response.read().decode('utf-8')
    topics = re.findall(r"</?t.*?sujet ligne_booleen(.+?)</tr>", html, re.MULTILINE | re.DOTALL)
    for topic in topics:
        all_topics_url.append(re.search(r"href=\"(.+?)\"", topic).group(1))
    i += 1
print("nb de topic = " + str(len(all_topics_url)))

all_messages = [['Message', 'Pseudo', 'Date', 'URL']]
threadList = []
for url in all_topics_url:
    print(str(len(all_messages)) + " messages total récoltés")
    with urllib.request.urlopen(url) as response:
        html = response.read().decode('utf-8')
    nb_page_topic = get_nbr_page(html)
    sujet_topic = re.search("itemprop=\"headline\"(.*?)<", html).group(1)
    print("topic \""+sujet_topic+"\" avec "+str(nb_page_topic)+" page(s)")
    page = 1
    while page <= int(nb_page_topic):
        clean_url = re.search(r"(.*)_", url).group(1)
        if debug:
            print(clean_url+"_"+str(page)+".htm")
        newthread = ClientThread(clean_url+"_"+str(page)+".htm", page, nb_page_topic, sujet_topic)
        newthread.start()
        threadList.append(newthread)
        page += 1
    time.sleep(1)

print("Attente des threats")
for curThread in threadList :
    curThread.join()

print(str(len(all_messages)) + " messages total récoltés en fin de script")
print(all_messages)

with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerows(all_messages)

