import json
import requests
import datetime
import time
import boto3
from botocore.exceptions import ClientError
from lib.sign_sdk import sign

Regions={ "meitu":"strategy.app.meitudata.com","starii":"strategy.stariidata.com","pre-starii":"prestrategy.stariidata.com","pre-meitu":"prestrategy.meitubase.com"}
RegionInner={"meitu":"openapi.m.com","starii":"openapi.s.com","pre-starii":"pre-openapi.s.com","pre-meitu":"pre-openapi.m.com"}
EnvPolicy={
    "inner": {
    "url":"http://openapi.m.com",
    "endpoint":RegionInner
    },
    "outer":{
    "url":"https://openapi.meitu.com",
    "endpoint":Regions
    }
}
class AiApi:
    """ ai api actions."""
    def __init__(self, app, biz,region="pre-meitu",env="inner"):
        """
        :param app: your appId.
        :param biz: your biz.
        :param region: api access region . default "pre-meitu"
        """
        self.App = app
        self.Biz = biz
        self.EndPoint=EnvPolicy[env]["endpoint"][region]
        self.aiStrategy=None
        self.envPolicy=EnvPolicy[env]
        if (region=="starii" or  region=="pre-starii") :
            if env=="outer":
                self.envPolicy["url"]="https://openapi.starii.com"
            else:
                self.envPolicy["url"]="http://openapi.s.com"


        
    def getAiStrategy(self):
        return self.getStrategy()

    def getStrategy(self):
        #now = datetime.datetime.now()
        #unix_epoch = datetime.datetime(1970, 1, 1，tzinfo=datetime.timezone.utc)
        #unix_time = (now - unix_epoch).total_seconds()
        now = datetime.datetime.now(datetime.timezone.utc)
        unix_time = now.timestamp()
        #ai可以使用有效期内的cache
        if  self.aiStrategy and self.aiStrategy["ttl"]+self.strategyLoadTime> unix_time :
            return self.aiStrategy
        
        signer = sign.Signer(self.App, self.Biz)
        sig=signer.signStrategy(str(int(datetime.datetime.now().timestamp())),{"app":self.App,"type":self.Biz})

        uri="http://"+ self.EndPoint + "/ai/policy?app="+self.App+"&type="+self.Biz+"&sig="+sig+"&sigTime="+str(int(unix_time))
        #sign_request = signer.sign(uri, "GET", headers, "")
        #print(uri)
        session = requests.Session()
        resp = session.get(uri,timeout=10)
        #print(resp.content)
        if resp.status_code==200:
            policydata=json.loads(resp.content)
            if policydata==None :
                return
            policy=policydata["data"][0]
            cloud=policy["order"][0]
            cloudConf=policy[cloud]
            self.aiStrategy=cloudConf
        
            now = datetime.datetime.now(datetime.timezone.utc)
            unix_time = now.timestamp()
            self.strategyLoadTime=unix_time
            
            return self.aiStrategy


        
    def run(self,imageUrl,params,task,taskType):
        """
        apply effect to the object.
        :params imageUrl  the image url array [{"url":"url"}]
        :params parmas api params object
        :params task  task name to be apply ,
        :params taskType task supporide, ["mtlab","inference","workflow"]
        :return: The handled result data in json.
        """
        
        policy=self.getAiStrategy()
        if policy==None :
            return {"error":"get ai strategy failure"}
        signer = sign.Signer(policy["credentials"]["access_key"], policy["credentials"]["secret_key"])
        host = self.envPolicy["url"]
        if host.find("https")>-1 :
            host =host[8:]
        elif host.find("http")>-1 :
            host =host[7:]

        headers = {
            sign.HeaderHost: host,
        }
        
        data = {
            "params": json.dumps(params),
            "task": task,
            "task_type": taskType,
            "init_images":imageUrl,
            "sync_timeout":10,
        }
        uri= self.envPolicy["url"] +"/"+ policy["push_path"]
        sign_request = signer.sign(uri, "POST", headers, json.dumps(data))
        session = requests.Session()
        resp = session.send(sign_request,timeout=policy["sync_timeout"]+10)
        if resp.status_code==200 :
            taskResult= json.loads(resp.content)
            if taskResult["data"]["status"]==9:
                return self.status(taskResult["data"]["result"]["id"],policy)
            else:
                return taskResult          
        return json.loads(resp.content)
    def runAsync(self,imageUrl,params,task,taskType):
        """
        apply effect to the object.
        :params imageUrl  the image url array [{"url":"url"}]
        :params parmas api params object
        :params task  task name to be apply ,
        :params taskType task supporide, ["mtlab","inference","workflow"]
        :return: The handled result data in json.
        """
        
        policy=self.getAiStrategy()
        if policy==None :
            return {"error":"get ai strategy failure"}
        signer = sign.Signer(policy["credentials"]["access_key"], policy["credentials"]["secret_key"])
        host = self.envPolicy["url"]
        if host.find("https")>-1 :
            host =host[8:]
        elif host.find("http")>-1 :
            host =host[7:]

        headers = {
            sign.HeaderHost: host,
        }
        
        data = {
            "params": json.dumps(params),
            "task": task,
            "task_type": taskType,
            "init_images":imageUrl,
            "sync_timeout":-1,
        }
        uri= self.envPolicy["url"] +"/"+ policy["push_path"]
        sign_request = signer.sign(uri, "POST", headers, json.dumps(data))
        session = requests.Session()
        resp = session.send(sign_request,timeout=10)
        if resp.status_code==200 :
            taskResult= json.loads(resp.content)
            return taskResult          
        return json.loads(resp.content)

    def status(self,taskId,policy):
        """
        query task execute status
        :params taskId  the task id 
        :params policy query policy with retry and gaps with every retry
        :return: The handled result data in json.
        """
        host = self.envPolicy["url"]
        if host.find("https")>-1 :
            host =host[8:]
        elif host.find("http")>-1 :
            host =host[7:]
        uri= self.envPolicy["url"] +"/"+ policy["status_query"]["path"]+"?task_id="+taskId
        loops = policy["status_query"]["durations"]
        durations=str.split(loops,",")
        for d in durations :
            result = self.queryStatus(uri,policy)
            if result["is_finished"] :
                return result["result"]
            time.sleep(int(d)/1000)
        return None
    def credential(self):
        policy=self.getAiStrategy()
        return {"ak":policy["credentials"]["access_key"],"sk":policy["credentials"]["secret_key"]}
    def queryStatus(self,uri,policy):
        cred=self.credential()
        signer =sign.Signer(cred["ak"],cred["sk"])
        host = self.envPolicy["url"]
        if host.find("https")>-1 :
            host =host[8:]
        elif host.find("http")>-1 :
            host =host[7:]
        headers = {
            sign.HeaderHost: host,
        }
        sign_request = signer.sign(uri, "GET", headers, "")
        session = requests.Session()
        resp = session.send(sign_request,timeout=3)
        if resp.status_code==200 :
            taskResult= json.loads(resp.content)
            if taskResult["data"]["status"]==10 or taskResult["data"]["status"]==2 or taskResult["data"]["status"]==20 :
                return {"is_finished":True,"result":taskResult}
            else:
                return {"is_finished":False,"result":taskResult}         
        return {"is_finished":False,"result":" task query failure: "+uri}
    
    def queryResult(self,uri):
        cred=self.credential()
        signer =sign.Signer(cred["ak"],cred["sk"])
        host = self.envPolicy["url"]
        if host.find("https")>-1 :
            host =host[8:]
        elif host.find("http")>-1 :
            host =host[7:]
        headers = {
            sign.HeaderHost: host,
        }
        requst_uri= self.envPolicy["url"] +"/api/v1/sdk/status?task_id="+ uri
        sign_request = signer.sign(requst_uri, "GET", headers, "")
        session = requests.Session()
        resp = session.send(sign_request,timeout=3)
        if resp.status_code==200 :
            taskResult= json.loads(resp.content)
            if taskResult["data"]["status"]==10 or taskResult["data"]["status"]==2 or taskResult["data"]["status"]==20 :
                return {"is_finished":True,"result":taskResult}
            else:
                return {"is_finished":False,"result":taskResult}         
        return {"is_finished":False,"result":" task query failure: "+uri}
    
    def sod(self,url,params,version="v1"):
        return self.invoke(url,params,version+"/sod","mtlab")

    def znxcAsync(self,url,params,version="v1"):
        return self.invoke(url,params,version+"/znxc_async","mtlab")
    
    def imageRestorationAsync(self,url,params,version="v1"):
        return self.invoke(url,params,version+"/image_restoration_async","mtlab")

    def txt2img(self,params):
        return self.run(None,params,"txt2img","inference")
    

    def img2img(self,url,params):
        return self.run([{"url":url}],params,"img2img","inference")
    
    def inferenceConf(self):
        pass

    def invoke(self,url,params,task):
        """
        invoke ai task
        :params url  the task id 
        :params params task params 
        :params task ai task name ,such as v1/sod ,v1/znxc_async
        :return: The handled result data in json.
        """
        if url == None :
            return self.run(None,params,task,"mtlab")
        return self.run([{"url":url}],params,task,"mtlab")


