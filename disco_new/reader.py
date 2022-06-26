import os,json,csv,re
import pandas as pd
import xml.etree.ElementTree as et
from pathlib import Path

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class DISCO_Reader:

    def __init__(self,data_path):
        self.__data_path =data_path
        self.__paths_dict = None
        self.__xml_dict = None
        self.__current_file = None
        self.__tree = None
        self.__meta = { "start_date":None, 
                        "end_time":None, 
                        "channel_name":None, 
                        "team_domain":None,
                    }
        self.__data = {"data":[], "meta":{}}
        self.__output_path=None
        self.__so_posts = {"data":[], "meta":{}}
        self.__current_convo = None
        self.__categories = [
                "Debugging Solution",
                "Alternative Solution", 
                "Question Repost", 
            "Direct Solution Provided by Asker", 
            "Related Information (Not Solution)",
            "Direct Solution Provided by Non-Asker", 
            "Validating Solution", 
            "Outsourcing SO Post",
            "Other"
        ]

    def set_data_path(self, path):
        self.__data_path = os.path.abspath(path)
        self.set_xml_paths()
        return

    def set_output_path(self,path):
        self.__output_path = os.path.abspath(path)
        return

    def get_file_paths(self):
        if self.__data_path is None:
            return "Error: data path not set"
        paths = []
        data_path = self.__data_path
        try:
            project_dirs = os.listdir(self.__data_path)
            for d in project_dirs:
                timerange_dirs = os.listdir(f"{data_path}/{d}/")
                for t in timerange_dirs:
                    files = os.listdir(f"{data_path}/{d}/{t}/")
                    for f in files:
                        if ".out" in f:
                            paths.append(os.path.abspath(f"{data_path}/{d}/{t}/{f}"))
        except Exception as e: 
            print(e)
        self.__paths_dict = paths
        return paths


    def load_xml(self,path):
        try:
            abs_path = os.path.abspath(path)
            tree = et.parse(abs_path)
            self.__current_file = abs_path
            self.__tree = tree
            self.read_meta()
            self.read_messages()
            return tree
        except Exception as e:
            print(e)
        return None
    
    def read_meta(self):
        root = self.get_root()
        for k in self.__meta.keys():
            if root.find(k) is not None:
                self.__meta[k] = root.find(k).text
        return

    def get_root(self):
        return self.__tree.getroot()

    def read_message(self,e):
        msg = { "ts":"", # timestamp
                "user":"",
                "text":"",
                }
        for k in msg.keys():
            msg[k] = e.find(k).text
        msg['conversation_id'] = e.attrib['conversation_id'] #thread id
        return msg

    def read_messages(self):
        root = self.get_root()
        count = 0
        convos = {}
        for child in iter(root.findall("message")):
            count+=1
            msg = self.read_message(child)
            convo_id = msg['conversation_id']

            if convo_id not in convos.keys():
                msg['index']=0
                convos[convo_id] = [msg]
            else:
                msg['index'] = len(convos[convo_id])
                convos[convo_id].append(msg)

        for k in convos.keys(): # for each convo_id
            thread = {"conversation_id" : k, "messages":convos[k]}
            self.__data['data'].append(thread)
            
        self.__meta['count'] = count
        return

    def get_data_dict(self):
        return self.__data['data']
    
    def get_so_data_dict(self):
        return self.__so_posts['data']
    def get_meta_data_dict(self):
        return self.__meta
    def get_categories(self):
        return self.__categories

    def export_to_json(self,path=""):
        try:
            if self.__output_path is None:
                self.set_output_path(path)
            data = self.__data
            data['meta'] = self.__meta
            data['so_posts'] = self.__so_posts['data']
            with open(self.__output_path, "w+") as f:
                json.dump(data, f)
        except Exception as e:
            print(e)
        return

    def get_convo_ids(self):
        data = self.get_data_dict()
        return [x['conversation_id'] for x in data]

    def get_convo(self,convo_id):
        if str(convo_id) in self.get_convo_ids():
            data =self.get_data_dict()
            return data[int(convo_id)-1]
        else:
            return None

    def get_so_convo_ids(self):
        data = self.get_so_data_dict()
        return [x['conversation_id'] for x in data]

    def get_so_convo(self,convo_id):
        if str(convo_id) in self.get_so_convo_ids():
            data =self.get_so_data_dict()
            for convo in data:
                if str(convo_id) == convo['conversation_id']:
                    return convo
        else:
            return None


    def find_so_posts(self,regex):
        so_convos = []
        pattern = re.compile(regex)
        data = self.get_data_dict()
        for convo in data:
            convo_id = convo['conversation_id']
            convo_thread = {"conversation_id":convo_id, 
                            "messages":[],
                            "so_post_count":0
                            }
            msgs = convo['messages']
            for msg in msgs:
                if re.search(pattern,msg['text']):
                    convo_thread['so_post_count']+=1
                    convo_thread['messages'].append(msg)
            if convo_thread['so_post_count'] > 0:
                so_convos.append(convo_thread)
        self.__so_posts['data'] = so_convos
        return

    def get_so_posts(self):
        return self.__so_posts['data']

    def get_convos(self,convo_id): 
        so_convo = self.get_so_convo(convo_id)
        total_convo = self.get_convo(convo_id)
        return so_convo, total_convo
    
    """
    def get_convo_df(self,so_msg, total_convo):
        keys = so_msg.keys()
        all_msgs = total_convo['messages']
        df = pd.DataFrame()
        for msg in all_msgs:
            msg = {'user':msg['user'] ,'text':msg['text']}
            df = df.append(msg,ignore_index=True)
        return df
    """

    def label_matches(self,output_dir_path,start_conversation_id=None):
        matches = self.get_so_data_dict()

        if start_conversation_id is None:
            start_conversation_id = matches[0]['conversation_id']

        # jump to starting conversation id and msg idx
        i = 0
        while i < len(matches) and matches[i]['conversation_id'] != start_conversation_id:
            i+=1
        if i >= len(matches):
            raise Exception(f"start_conversation_id {start_conversation_id} is invalid")
            return
        
        categories_str = ""
        for x in range(len(self.__categories)):
            categories_str = categories_str + f"{x}:{self.__categories[x]}\n"

        while i < len(matches):
            match_conversation = matches[i]
            match_conversation_id = match_conversation["conversation_id"]
            match_msgs = [x for x in match_conversation['messages']]
            full_conversation = self.get_convo(match_conversation_id)
            full_msgs = full_conversation['messages']
            for match_msg in match_msgs:
                match_msg_text = match_msg['text']
                match_msg_user = match_msg['user']
                match_msg_index = match_msg['index']
                target_str = f"{match_msg_index}:{match_msg_user}|{match_msg_text}"

                os.system('clear')
                k = 0
                for k in range(len(full_msgs)): # for each message in conversation
                    msg = full_msgs[k]
                    msg_text = msg['text']
                    msg_user = msg['user']
                    msg_index = msg['index']
                    output_str = f"{msg_index}:{msg_user}|{msg_text}"

                    if msg_index ==match_msg_index:
                        print(bcolors.WARNING + output_str + bcolors.ENDC)
                    elif msg_user == match_msg_user:
                        print(bcolors.OKCYAN + output_str + bcolors.ENDC)
                    elif '?' in msg_text:
                        print(bcolors.HEADER + output_str + bcolors.ENDC)
                    else:
                        print(bcolors.OKGREEN + output_str + bcolors.ENDC)

                progress = round((i/len(matches))*100, 2)

                print(bcolors.FAIL + f"{progress}%|CONVERSATION_ID: {match_conversation_id} MSG_IDX: {match_msg_index}\n{target_str}" + bcolors.ENDC)
                q_idx= input("Enter question msg index, t for target as Q&A, ENTER to skip, or x to quit: ")
                if q_idx =="x" or q_idx== "X":
                    print(f"QUITTING AT CONVERSATION_ID {match_conversation_id} and MSG IDX: {match_msg_index}")
                    return
                elif q_idx == "t" or q_idx=="T":
                    q_msg = match_msg
                elif len(q_idx) == 0:
                   continue #skip if 
                else:
                    q_msg = full_msgs[int(q_idx)]
                category  = self.__categories[int(input(f"Pick from the following categories:\n{categories_str}"))]
                comments = input("Enter comments:")
                dump = {'related_post': q_msg ,
                        'so_post': match_msg, 
                        'category' : category, 
                        'comments': comments,
                        'meta': self.get_meta_data_dict()
                        }
                filename = f"{match_conversation_id}-{match_msg_index}.json"
                with open(f"{output_dir_path}/{filename}", "w+") as f:
                    json.dump(dump, f, indent=4)
            i=i+1
        return
    def abs_file_paths(self,directory):
        for dirpath,_,filenames in os.walk(directory):
            for f in filenames:
                yield os.path.abspath(os.path.join(dirpath, f))

    def get_category_counts(self,input_data_dir="./data", output_data_dir="./output"):
        # get all input data paths (.xml.out)
        input_paths = [ x for x in reader.abs_file_paths(input_data_dir) if '.xml.out' in x ]

        #setup count dict
        overall_categories = {'sum':0}
        for c in reader.get_categories():
            overall_categories[c] = 0
        counts = {'total_so_posts':0, 'overall':overall_categories, 'per_dir':{}}
        #get output data paths (.json)
        output_paths = [x for x in reader.abs_file_paths(output_data_dir) if '.json' in x]
        for abs_path in output_paths:
            dir_path = str(Path(abs_path).parent.absolute()) # get filepath

            with open(abs_path, "r") as jf:
                category = json.load(jf)['category'] # get category from json

            if dir_path not in counts['per_dir']: #for each project dir
                category_dict = {'sum':0}
                for c in reader.get_categories():
                    category_dict[c] = 0
                counts['per_dir'][dir_path] = category_dict

            counts['per_dir'][dir_path][category]+=1
            counts['per_dir'][dir_path]['sum']+=1
            counts['overall'][category]+=1
            counts['overall']['sum']+=1
            print(abs_path, category)

        for path in input_paths:
            reader.load_xml(path)
            reader.find_so_posts("stackoverflow.com") # can use to search w/ regexes
            so_post_count = len(reader.get_so_data_dict())
            print(path, so_post_count)
            counts['total_so_posts']+=so_post_count
        with open("./counts.json", "w+") as f:
            json.dump(counts,f)
        return

if __name__ == "__main__":
    reader = DISCO_Reader("./data")
    reader.load_xml("/home/colinm/Documents/serene/serene-so-bert/disco_new/data/pythongeneral/Aug2020/pythongeneralAug2020.xml.out")
    reader.find_so_posts("stackoverflow.com")
    reader.label_matches(output_dir_path="./output/python/Aug2020", start_conversation_id="1540")

